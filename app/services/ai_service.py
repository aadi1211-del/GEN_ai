"""
ai_service.py
--------------
Thin abstraction layer over the two supported LLM providers (Gemini / OpenAI).
Keeping this in one place means the rest of the app (chat routes, RAG
service) never needs to know which provider is active - it just calls
`generate_response()`.

Design notes for the report / viva:
- Provider is chosen via AI_PROVIDER in .env, so switching from Gemini to
  OpenAI needs zero code changes.
- If no API key is configured, the app degrades gracefully instead of
  crashing - useful for offline demos of the UI/DB/auth layers.
"""
import html

from flask import current_app


def render_markdown(text: str) -> str:
    """Render model Markdown after escaping raw HTML from model output."""
    import markdown

    return markdown.markdown(
        html.escape(text or ""),
        extensions=["extra", "nl2br"],
        output_format="html5",
    )


SYSTEM_PROMPT = (
    "You are NeuraForge Assistant, a helpful, concise, and accurate AI assistant "
    "embedded in a final-year Generative AI web application. "
    "If context documents are supplied, ground your answer in them and say so "
    "when the answer isn't contained in the provided context."
)


class AIServiceError(Exception):
    pass


def _build_prompt(user_message: str, history: list, context: str | None) -> str:
    """Compose a single prompt string for providers/models called without
    native multi-turn chat objects (kept simple & provider-agnostic)."""
    parts = [SYSTEM_PROMPT]

    if context:
        parts.append(
            "\n--- CONTEXT FROM UPLOADED DOCUMENT (use this to answer) ---\n"
            f"{context}\n--- END CONTEXT ---"
        )

    if history:
        parts.append("\nConversation so far:")
        for turn in history[-8:]:  # keep the prompt bounded
            role = "User" if turn["role"] == "user" else "Assistant"
            parts.append(f"{role}: {turn['content']}")

    parts.append(f"\nUser: {user_message}\nAssistant:")
    return "\n".join(parts)


def _call_gemini(prompt: str) -> str:
    try:
        from google import genai
    except ImportError as e:
        raise AIServiceError("google-genai package is not installed.") from e

    api_key = current_app.config["GEMINI_API_KEY"]
    if not api_key:
        raise AIServiceError("GEMINI_API_KEY is not set in .env")

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=current_app.config["GEMINI_MODEL"],
        input=prompt,
    )
    return (interaction.output_text or "").strip()


def _call_openai(prompt: str) -> str:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise AIServiceError("openai package is not installed.") from e

    api_key = current_app.config["OPENAI_API_KEY"]
    if not api_key:
        raise AIServiceError("OPENAI_API_KEY is not set in .env")

    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=current_app.config["OPENAI_MODEL"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content.strip()


def generate_response(user_message: str, history: list | None = None, context: str | None = None) -> dict:
    """
    Returns: {"success": bool, "reply": str, "provider": str, "error": str|None}
    Never raises - callers can render `reply` straight into the chat UI.
    """
    provider = current_app.config["AI_PROVIDER"]
    history = history or []
    prompt = _build_prompt(user_message, history, context)

    try:
        if provider == "gemini":
            reply = _call_gemini(prompt)
        elif provider == "openai":
            reply = _call_openai(prompt)
        else:
            raise AIServiceError(f"Unknown AI_PROVIDER '{provider}'. Use 'gemini' or 'openai'.")

        if not reply:
            reply = "I couldn't generate a response for that. Could you rephrase?"

        return {"success": True, "reply": reply, "provider": provider, "error": None}

    except AIServiceError as e:
        return {
            "success": False,
            "provider": provider,
            "reply": (
                f"⚠️ AI provider '{provider}' is not configured correctly ({e}). "
                "Add a valid API key to your .env file to enable live responses."
            ),
            "error": str(e),
        }
    except Exception as e:  # noqa: BLE001 - surface any provider/network error to the UI
        return {
            "success": False,
            "provider": provider,
            "reply": f"⚠️ The AI provider returned an error: {e}",
            "error": str(e),
        }