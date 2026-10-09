import re
import llm
from agents import qualitative, quantitative
from validation.validator import validate_qualitative, validate_quantitative, validate_synthesis
from tokenomics.logger import log

CLASSIFY_SYSTEM = """You are a query router for an enterprise assistant.
Classify the query as exactly one of: qualitative, quantitative, both.
qualitative = policies, processes, procedures, explanations, documentation
quantitative = numbers, metrics, trends, comparisons, SQL-queryable data
both = needs document search AND data analysis
Reply with ONE word only."""


def classify(query):
    # max_tokens is deliberately not tiny: Gemini can use part of it for internal reasoning.
    r = llm.chat(query, system=CLASSIFY_SYSTEM, max_tokens=100, temperature=0.0)
    log(query, "manager-classifier", r["input_tokens"], r["output_tokens"])
    m = re.search(r"\b(qualitative|quantitative|both)\b", r["text"].lower())
    return m.group(1) if m else "qualitative"


def synthesize(query, qual, quant):
    system = ("You combine two reports into one answer. Use ONLY the information given. "
              "Keep document-based claims and data-based claims clearly separate, keep citations like [Source N], "
              "and add no outside facts. If the reports don't answer part of the question, say so.")
    prompt = f"QUESTION: {query}\n\nDOCUMENT REPORT:\n{qual['answer']}\n\nDATA REPORT (SQL: {quant['sql']}):\n{quant['answer']}"
    r = llm.chat(prompt, system=system, max_tokens=1200, temperature=0.2)
    log(query, "manager-synthesis", r["input_tokens"], r["output_tokens"])
    return r["text"]


def _warn(v):
    if v and v["flag"]:
        print(f"\n⚠️  VALIDATION WARNING: {v['warning']}")


def run(query):
    print(f"\nQuery: {query}")
    route = classify(query)
    print(f"Route: {route}")
    qual = quant = qual_v = quant_v = synth_v = None

    if route in ("qualitative", "both"):
        qual = qualitative.run(query)
        qual_v = validate_qualitative(qual["answer"], qual["chunks"])
        log(query, "qualitative", qual["input_tokens"], qual["output_tokens"])
        _warn(qual_v)
        print(f"\n[Qualitative]\n{qual['answer']}")

    if route in ("quantitative", "both"):
        quant = quantitative.run(query)
        quant_v = validate_quantitative(quant["answer"], quant["sql"], quant["validation"], quant["rows"])
        log(query, "quantitative", quant["input_tokens"], quant["output_tokens"])
        _warn(quant_v)
        print(f"\n[Quantitative]\n{quant['answer']}")
        print(f"SQL used: {quant['sql']}")

    if route == "both":
        final = synthesize(query, qual, quant)
        synth_v = validate_synthesis(final, qual_v, quant_v)
        _warn(synth_v)
        print(f"\n[Final answer]\n{final}")
    else:
        final = (qual or quant)["answer"]

    warnings = [v["warning"] for v in (qual_v, quant_v, synth_v) if v and v["flag"]]
    return {"query": query, "route": route, "answer": final, "qualitative": qual, "quantitative": quant,
            "qualitative_validation": qual_v, "quantitative_validation": quant_v,
            "flagged": bool(warnings), "warnings": warnings}

