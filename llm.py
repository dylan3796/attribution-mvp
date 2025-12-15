import os
from typing import Tuple, Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai optional
    OpenAI = None


def call_llm(prompt: str, system: Optional[str] = None, model: str = "gpt-4o-mini", temperature: float = 0.2) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Returns (ok, content, error). Falls back gracefully if key/package missing.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return False, None, "Set OPENAI_API_KEY and install openai to enable LLM calls."

    try:
        client = OpenAI(api_key=api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        content = resp.choices[0].message.content.strip()
        return True, content, None
    except Exception as exc:  # pragma: no cover - remote call
        return False, None, str(exc)
