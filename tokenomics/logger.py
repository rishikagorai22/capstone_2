import json
from datetime import datetime
import config


def log(query, agent, input_tokens, output_tokens):
    input_cost = (input_tokens / 1_000_000) * config.PRICE_IN_PER_1M
    output_cost = (output_tokens / 1_000_000) * config.PRICE_OUT_PER_1M
    total_cost = input_cost + output_cost
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "query": query,
        "agent": agent,
        "model": config.GEMINI_MODEL,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(total_cost, 6),
        "cost_per_1000_queries": round(total_cost * 1000, 2),
    }
    print(f"[TOKENOMICS] {agent:<20} in={input_tokens:<6} out={output_tokens:<5} est. cost=${total_cost:.6f}")
    with open(config.LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

