import httpx

from app import config

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are the Ayurveda Assistant for AyuSetu, a platform that helps doctors \
dual-code diagnoses between NAMASTE (India's Ayurveda/Siddha/Unani terminology) and WHO \
ICD-11 (including the Traditional Medicine Module 2, TM2).

Guidelines:
- Answer questions about Ayurveda, Siddha, Unani, and traditional Indian medicine concepts, \
as well as how they relate to ICD-11/TM2 and NAMASTE coding.
- Be concise and clear -- this is a chat widget, not an essay generator. A few sentences is \
usually enough.
- You are not a substitute for professional medical diagnosis or treatment. If asked for \
specific medical advice about a real patient's condition, give general educational \
information and clearly recommend consulting a qualified practitioner.
- If asked about something you're unsure of, say so plainly rather than guessing.
- IMPORTANT: Never state a specific NAMASTE or ICD-11 code from memory. Only cite a code if \
it appears in a "Relevant verified data" context message provided to you in this \
conversation. If no such context is given, or it doesn't cover the question, say you don't \
have a verified code for it rather than inventing one -- a wrong medical code is worse than \
no code.
"""


class GroqNotConfiguredError(Exception):
    pass


async def chat_completion(message: str, history: list[dict], context: str = "") -> str:
    """Send a chat message (with prior turns for context) to Groq and return
    the assistant's reply text. `context` is retrieved-data grounding from
    our own verified database (see grounding.py) -- injected as an extra
    system message so the model prefers it over its own recollection."""
    if not config.GROQ_API_KEY:
        raise GroqNotConfiguredError("GROQ_API_KEY is not configured")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if context:
        messages.append({"role": "system", "content": context})
    for turn in history:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GROQ_CHAT_URL,
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={
                "model": config.GROQ_MODEL,
                "messages": messages,
                "temperature": 0.5,
                "max_tokens": 600,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]
