import re

REFUSAL_PHRASE = "cannot find this information"


def _cited_numbers(answer):
    """Finds citations like 'Source 2', '[Source 1]', 'Sources 1, 3 and 4'."""
    nums = set()
    for m in re.finditer(r"Sources?\s*#?(\d+(?:\s*(?:,|and|&)\s*\d+)*)", answer, flags=re.IGNORECASE):
        nums.update(int(n) for n in re.findall(r"\d+", m.group(1)))
    return nums


def _overlap_ratio(answer, chunks):
    """What fraction of the answer's longer words appear in the retrieved context? Low = suspicious."""
    context = " ".join(c["content"] for c in chunks).lower()
    words = {w for w in re.findall(r"[a-z]{5,}", answer.lower()) if w != "source"}
    if not words:
        return 1.0
    return sum(1 for w in words if w in context) / len(words)


def validate_qualitative(answer, chunks, min_overlap=0.35):
    if not answer.strip():
        return {"is_grounded": False, "refused_to_answer": False, "sources_cited": [], "invalid_citations": [],
                "overlap_ratio": 0.0, "flag": True, "warning": "Empty response from model"}
    warnings = []
    cited = _cited_numbers(answer)
    valid = sorted(n for n in cited if 1 <= n <= len(chunks))
    invalid = sorted(n for n in cited if not 1 <= n <= len(chunks))
    sources = [chunks[n - 1]["source"] for n in valid]
    refused = REFUSAL_PHRASE in answer.lower()
    overlap = _overlap_ratio(answer, chunks)
    grounded = len(valid) > 0

    if not grounded and not refused:
        warnings.append("Response may not be grounded in source documents (no valid citations)")
    if invalid:
        warnings.append(f"Cites sources that were never provided: {invalid}")
    if not refused and overlap < min_overlap:
        warnings.append(f"Low word overlap with retrieved context ({overlap:.0%}); may contain outside knowledge")

    return {"is_grounded": grounded, "refused_to_answer": refused, "sources_cited": sources,
            "invalid_citations": invalid, "overlap_ratio": round(overlap, 2),
            "flag": bool(warnings), "warning": "; ".join(warnings) if warnings else None}


def validate_quantitative(answer, sql, validation_status, rows=None):
    warnings = []
    if validation_status != "PASSED":
        warnings.append(f"SQL validation status: {validation_status}")
    elif rows is not None and len(rows) == 0:
        warnings.append("Query returned no rows; the interpretation may be unreliable")
    if not answer.strip():
        warnings.append("Empty response from model")
    return {"sql_validated": validation_status == "PASSED", "sql_blocked": validation_status == "FAILED",
            "execution_error": validation_status == "ERROR", "flag": bool(warnings),
            "warning": "; ".join(warnings) if warnings else None}


def validate_synthesis(answer, qual_validation, quant_validation):
    """A combined answer is only as trustworthy as its parts."""
    warnings = []
    if not answer.strip():
        warnings.append("Empty synthesized response")
    if qual_validation and qual_validation["flag"]:
        warnings.append(f"Qualitative part flagged: {qual_validation['warning']}")
    if quant_validation and quant_validation["flag"]:
        warnings.append(f"Quantitative part flagged: {quant_validation['warning']}")
    return {"flag": bool(warnings), "warning": "; ".join(warnings) if warnings else None}

