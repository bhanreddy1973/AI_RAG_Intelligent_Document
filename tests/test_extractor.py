from app.extractor import extract_fields
from app.parser import Page
from app.schemas import DocumentType, EmploymentAgreement, OtherDocument


def test_extract_fills_fields_and_page_numbers(monkeypatch):
    monkeypatch.setattr(
        "app.extractor.chat_json",
        lambda messages, max_tokens=1500: {
            "fields": {
                "company_name": {"value": "ABC Technologies", "page": 1},
                "employee_name": {"value": "John Doe", "page": 1},
                "notice_period": {"value": "60 days", "page": 4},
                "key_clauses": {
                    "value": ["Confidentiality", "Termination"],
                    "page": 5,
                },
            },
            "other_fields": {
                "probation_period": {"value": "90 days", "page": 2},
            },
        },
    )

    pages = [
        Page(1, "ABC Technologies hires John Doe"),
        Page(4, "Notice period of 60 days"),
    ]
    result = extract_fields(pages, DocumentType.EMPLOYMENT_AGREEMENT)

    assert isinstance(result, EmploymentAgreement)
    assert result.notice_period.value == "60 days"
    assert result.notice_period.page == 4
    assert result.key_clauses.value == ["Confidentiality", "Termination"]
    assert "job_title" in result.missing_fields
    assert result.salary.value is None
    assert result.other_fields["probation_period"].value == "90 days"


def test_extract_other_document(monkeypatch):
    monkeypatch.setattr(
        "app.extractor.chat_json",
        lambda messages, max_tokens=1500: {
            "fields": {"title": {"value": "March Invoice", "page": 1}},
            "other_fields": {"amount": {"value": "50000 INR", "page": 1}},
        },
    )
    result = extract_fields([Page(1, "Invoice 50000 INR")], DocumentType.OTHER)

    assert isinstance(result, OtherDocument)
    assert result.title.value == "March Invoice"
    assert result.other_fields["amount"].value == "50000 INR"
    assert "company_name" in result.missing_fields
