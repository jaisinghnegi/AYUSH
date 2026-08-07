import httpx

from app import config
from app.assistant.groq_client import GROQ_CHAT_URL, GroqNotConfiguredError


async def translate_text(text: str, language_name: str) -> str:
    """Translate `text` into `language_name` (e.g. "Hindi") via Groq.

    This is a literal translation task, not a chat -- low temperature, no
    persona, and the prompt explicitly forbids adding commentary so the
    result is safe to store and display as-is.
    """
    if not config.GROQ_API_KEY:
        raise GroqNotConfiguredError("GROQ_API_KEY is not configured")

    if not text.strip():
        return text

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a medical terminology translator. Translate the user's text into "
                f"{language_name}. Preserve medical/technical meaning as precisely as possible. "
                f"Reply with ONLY the translated text -- no explanation, no quotes, no notes, "
                f"nothing else."
            ),
        },
        {"role": "user", "content": text},
    ]

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            GROQ_CHAT_URL,
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={
                "model": config.GROQ_MODEL,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 500,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"].strip()
