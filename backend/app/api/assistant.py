from typing import Literal, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.assistant.groq_client import GroqNotConfiguredError, chat_completion
from app.assistant.grounding import build_context

router = APIRouter(prefix="/assistant")


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatTurn]] = None


@router.post("/chat")
async def chat(body: ChatRequest) -> JSONResponse:
    if not body.message.strip():
        return JSONResponse(status_code=400, content={"error": "message is required"})

    history = [t.model_dump() for t in (body.history or [])]

    try:
        context = await build_context(body.message)
    except Exception as e:
        print(f"Grounding lookup failed (continuing without it): {e}")
        context = ""

    try:
        reply = await chat_completion(body.message, history, context)
    except GroqNotConfiguredError:
        return JSONResponse(
            status_code=503,
            content={"error": "The Ayurveda Assistant isn't configured yet (missing GROQ_API_KEY)."},
        )
    except Exception as e:
        print(f"Groq chat call failed: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": "The Ayurveda Assistant is temporarily unavailable. Please try again."},
        )

    return JSONResponse({"reply": reply})
