from unittest.mock import MagicMock, patch

import pytest

from app.nvidia_client import LLMError, chat, parse_json


def test_missing_api_key(monkeypatch):
    monkeypatch.setattr("app.nvidia_client.settings.llm_provider", "openai")
    monkeypatch.setattr("app.nvidia_client.settings.openai_api_key", "")
    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        chat([{"role": "user", "content": "hello"}])


@patch("app.nvidia_client.OpenAI")
def test_chat_returns_model_text(mock_openai, monkeypatch):
    monkeypatch.setattr("app.nvidia_client.settings.llm_provider", "openai")
    monkeypatch.setattr("app.nvidia_client.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.nvidia_client.settings.openai_llm_model", "gpt-4o-mini")
    mock_openai.return_value.chat.completions.create.return_value.choices[
        0
    ].message.content = "60 days"

    result = chat([{"role": "user", "content": "What is the notice period?"}])

    assert result == "60 days"
    mock_openai.return_value.chat.completions.create.assert_called_once()
    mock_openai.assert_called_once()
    assert mock_openai.call_args.kwargs["api_key"] == "test-key"


@patch("app.nvidia_client.time.sleep")
@patch("app.nvidia_client.OpenAI")
def test_chat_retries_then_succeeds(mock_openai, mock_sleep, monkeypatch):
    monkeypatch.setattr("app.nvidia_client.settings.llm_provider", "openai")
    monkeypatch.setattr("app.nvidia_client.settings.openai_api_key", "test-key")
    ok = MagicMock()
    ok.choices[0].message.content = "ok"
    mock_openai.return_value.chat.completions.create.side_effect = [
        TimeoutError("timed out"),
        ok,
    ]

    result = chat([{"role": "user", "content": "hi"}], retries=2)

    assert result == "ok"
    assert mock_openai.return_value.chat.completions.create.call_count == 2
    mock_sleep.assert_called_once()


@patch("app.nvidia_client.time.sleep")
@patch("app.nvidia_client.OpenAI")
def test_chat_raises_after_retries(mock_openai, mock_sleep, monkeypatch):
    monkeypatch.setattr("app.nvidia_client.settings.llm_provider", "openai")
    monkeypatch.setattr("app.nvidia_client.settings.openai_api_key", "test-key")
    mock_openai.return_value.chat.completions.create.side_effect = RuntimeError("down")

    with pytest.raises(LLMError, match="LLM request failed"):
        chat([{"role": "user", "content": "hi"}], retries=1)

    assert mock_openai.return_value.chat.completions.create.call_count == 2


def test_parse_json_strips_markdown():
    data = parse_json('```json\n{"summary": "ok"}\n```')
    assert data == {"summary": "ok"}


def test_parse_json_rejects_plain_text():
    with pytest.raises(LLMError, match="did not return JSON"):
        parse_json("the notice period is 60 days")
