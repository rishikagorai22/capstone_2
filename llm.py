import time
from google import genai
from google.genai import types, errors
import config

_client = None


def _get_client():
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def chat(prompt, system="You are a helpful assistant.", max_tokens=1024, temperature=0.2, retries=4):
    """Returns {"text", "input_tokens", "output_tokens"}.
    Every agent calls this one function, so the Gemini details live in ONE place."""
    client = _get_client()
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    for attempt in range(retries + 1):
        try:
            resp = client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt, config=cfg)
            break
        except errors.APIError as e:
            # 429 = rate limited (common on the free tier), 500/503 = Google is busy. Wait and retry.
            if e.code in (429, 500, 503) and attempt < retries:
                wait = 5 * (2 ** attempt)
                print(f"  [Gemini busy or rate limited ({e.code}), retrying in {wait}s...]")
                time.sleep(wait)
            else:
                raise

    usage = resp.usage_metadata
    input_tokens = (getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
    # Thinking tokens are billed as output, so count them too.
    output_tokens = ((getattr(usage, "candidates_token_count", 0) or 0)
                     + (getattr(usage, "thoughts_token_count", 0) or 0)) if usage else 0
    try:
        text = (resp.text or "").strip()
    except Exception:
        text = ""
    return {"text": text, "input_tokens": input_tokens, "output_tokens": output_tokens}
