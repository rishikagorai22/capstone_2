import re
import sqlite3
import config
import llm

ROWS_TO_LLM = 20   # only send this many rows to the LLM (saves tokens)
_schema_cache = None


def get_schema_context():
    """Reads the real tables/columns plus 2 example rows, so the model sees the true date format."""
    global _schema_cache
    if _schema_cache is None:
        conn = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
        lines = ["Available tables (SQLite):"]
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for t in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})")]
            lines.append(f"- {t}({', '.join(cols)})")
            for row in conn.execute(f"SELECT * FROM {t} LIMIT 2"):
                lines.append(f"    example row: {row}")
        conn.close()
        _schema_cache = "\n".join(lines)
    return _schema_cache


BLOCKED = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "ATTACH", "DETACH", "PRAGMA", "VACUUM"]


def validate_sql(query):
    """Guardrail: runs BEFORE any SQL touches the database."""
    q = query.strip().rstrip(";").strip()
    if not q:
        return {"valid": False, "reason": "Empty query"}
    for word in BLOCKED:
        if re.search(rf"\b{word}\b", q, flags=re.IGNORECASE):
            return {"valid": False, "reason": f"Blocked keyword: {word}"}
    if not q.upper().startswith("SELECT"):
        return {"valid": False, "reason": "Only SELECT queries are permitted"}
    if ";" in q:
        return {"valid": False, "reason": "Multiple statements are not permitted"}
    if "--" in q or "/*" in q:
        return {"valid": False, "reason": "SQL comments are not permitted"}
    return {"valid": True, "reason": "OK"}


def clean_sql(text):
    """Models often wrap SQL in ```sql fences; strip them."""
    text = re.sub(r"^```(?:sql)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


SQL_SYSTEM = """You are a SQLite expert. Convert the user's question into ONE read-only SQLite SELECT statement.
Rules:
- Output ONLY the SQL. No markdown, no explanation.
- Use only the tables and columns in the schema.
- Do not use WITH/CTEs; use subqueries instead.
- Dates are TEXT in ISO format (YYYY-MM-DD); use strftime() for month/quarter grouping.
- A NULL churn_date means the customer is still active.
- If the question cannot be answered from this schema, output: SELECT 'UNANSWERABLE' AS error"""

INTERPRET_SYSTEM = """You explain SQL query results to a business reader.
Use ONLY the numbers in the results provided; never invent or estimate values.
If the data is truncated or empty, say so. Be concise."""


def generate_sql(query):
    r = llm.chat(f"{get_schema_context()}\n\nQuestion: {query}", system=SQL_SYSTEM, max_tokens=800, temperature=0.0)
    return {"sql": clean_sql(r["text"]), "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"]}


def run(query):
    s = generate_sql(query)
    sql = s["sql"]
    validation = validate_sql(sql)

    if not validation["valid"]:
        return {"answer": f"Query blocked: {validation['reason']}", "sql": sql, "columns": [], "rows": [],
                "validation": "FAILED", "input_tokens": s["input_tokens"], "output_tokens": s["output_tokens"]}
    try:
        conn = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)  # read-only = can't write even by accident
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchmany(200)
        cols = [d[0] for d in cursor.description]
        conn.close()

        prompt = (f"The user asked: {query}\n\nSQL used: {sql}\n\nColumns: {cols}\n"
                  f"Rows (first {ROWS_TO_LLM} of {len(rows)}): {rows[:ROWS_TO_LLM]}\n\nInterpret these results.")
        r = llm.chat(prompt, system=INTERPRET_SYSTEM, max_tokens=800, temperature=0.2)
        return {"answer": r["text"], "sql": sql, "columns": cols, "rows": rows, "validation": "PASSED",
                "input_tokens": s["input_tokens"] + r["input_tokens"],
                "output_tokens": s["output_tokens"] + r["output_tokens"]}
    except Exception as e:
        return {"answer": f"Query execution failed: {e}", "sql": sql, "columns": [], "rows": [],
                "validation": "ERROR", "input_tokens": s["input_tokens"], "output_tokens": s["output_tokens"]}

    