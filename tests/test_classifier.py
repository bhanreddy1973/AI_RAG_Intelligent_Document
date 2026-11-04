from app.classifier import classify_document
from app.schemas import DocumentType


def test_classify_employment_agreement(monkeypatch):
    monkeypatch.setattr(
        "app.classifier.chat_json",
        lambda messages, max_tokens=80: {"document_type": "Employment Agreement"},
    )
    result = classify_document("Agreement between ABC and John Doe")
    assert result is DocumentType.EMPLOYMENT_AGREEMENT


def test_classify_unknown_becomes_other(monkeypatch):
    monkeypatch.setattr(
        "app.classifier.chat_json",
        lambda messages, max_tokens=80: {"document_type": "Invoice"},
    )
    result = classify_document("Tax invoice for March")
    assert result is DocumentType.OTHER


def test_classify_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(
        "app.classifier.chat_json",
        lambda messages, max_tokens=80: {"document_type": "company policy"},
    )
    result = classify_document("WFH policy")
    assert result is DocumentType.COMPANY_POLICY
