import time

from openai import OpenAI

from app.config import settings


class LLMError(Exception):
    pass


def chat(
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.0,
    retries: int = 2,
) -> str:
    if not settings.nvidia_api_key:
        raise LLMError("NVIDIA_API_KEY is missing. Add it to the .env file.")

    client = OpenAI(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
        timeout=60.0,
    )

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model=settings.nvidia_llm_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))

    raise LLMError(f"LLM request failed: {last_error}") from last_error
