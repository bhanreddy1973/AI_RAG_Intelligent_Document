import json
import re
import time

import httpx
from openai import OpenAI

from app.config import settings


class LLMError(Exception):
    pass


def _gemini_payload(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> dict:
    system_parts: list[str] = []
    contents: list[dict] = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, list):
            text = "\n".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        else:
            text = str(content)

        if role == "system":
            system_parts.append(text)
            continue

        gemini_role = "model" if role == "assistant" else "user"
        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"][0]["text"] += "\n" + text
        else:
            contents.append({"role": gemini_role, "parts": [{"text": text}]})

    if not contents:
        contents = [{"role": "user", "parts": [{"text": "\n".join(system_parts) or ""}]}]
        system_parts = []

    payload: dict = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_parts:
        payload["systemInstruction"] = {
            "parts": [{"text": "\n\n".join(system_parts)}]
        }
    return payload


def _chat_gemini(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    if not settings.gemini_api_key:
        raise LLMError("GEMINI_API_KEY is missing. Add it to the .env file.")

    model = settings.gemini_model
    url = (
        f"{settings.gemini_base_url.rstrip('/')}/models/"
        f"{model}:generateContent"
    )
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": settings.gemini_api_key,
    }
    payload = _gemini_payload(messages, max_tokens, temperature)

    with httpx.Client(timeout=60.0, trust_env=False) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMError(f"Gemini returned no candidates: {data}")
    parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
    text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    if not text.strip():
        raise LLMError(f"Gemini returned empty content: {data}")
    return text.strip()


def _chat_openai_compatible(
    *,
    api_key: str,
    base_url: str,
    model: str,
    missing_key_message: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float,
    timeout: float = 60.0,
    extra_body: dict | None = None,
) -> str:
    if not api_key:
        raise LLMError(missing_key_message)

    client = OpenAI(
        api_key=api_key.strip(),
        base_url=base_url,
        timeout=timeout,
    )
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if extra_body:
        kwargs["extra_body"] = extra_body
    response = client.chat.completions.create(**kwargs)
    message = response.choices[0].message
    text = (message.content or "").strip()
    if not text:
        # Some NIM thinking models put text in reasoning_content instead.
        text = (getattr(message, "reasoning_content", None) or "").strip()
    if not text:
        raise LLMError("LLM returned empty content.")
    # Drop accidental think blocks if the model ignores enable_thinking=False.
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    return text


def _chat_nvidia(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    # Nemotron Ultra supports thinking; keep it off for structured JSON tasks.
    return _chat_openai_compatible(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
        model=settings.nvidia_llm_model,
        missing_key_message="NVIDIA_API_KEY is missing. Add it to the .env file.",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout=180.0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def _chat_openai(
    messages: list[dict],
    max_tokens: int,
    temperature: float,
) -> str:
    return _chat_openai_compatible(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_llm_model,
        missing_key_message="OPENAI_API_KEY is missing. Add it to the .env file.",
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def chat(
    messages: list[dict],
    max_tokens: int = 1024,
    temperature: float = 0.0,
    retries: int = 2,
) -> str:
    provider = (settings.llm_provider or "openai").strip().lower()
    last_error = None
    for attempt in range(retries + 1):
        try:
            if provider == "nvidia":
                return _chat_nvidia(messages, max_tokens, temperature)
            if provider == "gemini":
                return _chat_gemini(messages, max_tokens, temperature)
            if provider == "openai":
                return _chat_openai(messages, max_tokens, temperature)
            raise LLMError(
                f"Unknown LLM_PROVIDER={provider!r}. Use openai, gemini, or nvidia."
            )
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))

    raise LLMError(f"LLM request failed: {last_error}") from last_error


def parse_json(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        preview = cleaned[:200].replace("\n", " ")
        raise LLMError(f"LLM did not return JSON. Preview: {preview!r}")
    snippet = cleaned[start : end + 1]
    try:
        data = json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM returned invalid JSON. Preview: {snippet[:200]!r}") from exc
    if not isinstance(data, dict):
        raise LLMError("LLM JSON must be an object.")
    return data


def chat_json(
    messages: list[dict],
    max_tokens: int = 1024,
    retries: int = 2,
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
                    "content": (
                        "Return valid JSON only. One JSON object. "
                        "No markdown, no extra text."
                    ),
                }
            ]
    raise LLMError(f"Could not parse LLM JSON: {last_error}") from last_error
