from app.parser import Page
from app.summarizer import summarize_pages


def test_summarize_pages_batches_and_combines(monkeypatch):
    monkeypatch.setattr("app.summarizer.settings.pages_per_batch", 2)
    monkeypatch.setattr("app.summarizer.settings.max_parallel", 2)

    calls = []

    def fake_chat_json(messages, max_tokens=1024, retries=1):
        calls.append(messages)
        user = messages[-1]["content"]
        if user.startswith("Pages "):
            return {
                "title": "Employment Agreement",
                "short_summary": "Covers notice and pay.",
                "key_topics": ["notice period"],
                "entities": ["ABC Technologies"],
            }
        return {"summary": f"batch {len(calls)}"}

    monkeypatch.setattr("app.summarizer.chat_json", fake_chat_json)

    pages = [
        Page(1, "Company ABC"),
        Page(2, "Employee John"),
        Page(3, "Notice 60 days"),
    ]
    overview = summarize_pages(pages)

    assert len(overview.batch_summaries) == 2
    assert overview.batch_summaries[0].page_start == 1
    assert overview.batch_summaries[0].page_end == 2
    assert overview.batch_summaries[1].page_start == 3
    assert overview.title == "Employment Agreement"
    assert "notice" in overview.short_summary.lower()
    assert overview.key_topics == ["notice period"]
    assert overview.entities == ["ABC Technologies"]
    assert len(calls) == 3
