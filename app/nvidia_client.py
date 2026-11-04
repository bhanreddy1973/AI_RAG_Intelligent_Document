import json
import re
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


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMError("LLM did not return JSON.")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError("LLM returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise LLMError("LLM JSON must be an object.")
    return data


def chat_json(
    messages: list[dict],
    max_tokens: int = 1024,
    retries: int = 1,
) -> dict:
    last_error = None
    current = list(messages)
    for _ in range(retries + 1):
        try:
            return parse_json(chat(current, max_tokens=max_tokens, temperature=0.0))
        except LLMError as exc:
            last_error = exc
            current = messages + [
                {
                    "role": "user",
                    "content": "Return valid JSON only. No markdown, no extra text.",
                }
            ]
    raise LLMError(f"Could not parse LLM JSON: {last_error}") from last_error
