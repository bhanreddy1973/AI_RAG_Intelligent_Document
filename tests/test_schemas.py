from app.schemas import (
    SCHEMA_BY_TYPE,
    AskResponse,
    DocumentType,
    EmploymentAgreement,
    ExtractedField,
    OtherDocument,
    SearchRequest,
)


def test_all_document_types_have_a_schema():
    assert set(SCHEMA_BY_TYPE.keys()) == set(DocumentType)


def test_other_type_exists():
    assert DocumentType.OTHER.value == "Other"
    schema = SCHEMA_BY_TYPE[DocumentType.OTHER]
    assert schema is OtherDocument


def test_employment_missing_values_are_null_or_empty():
    data = EmploymentAgreement()
    assert data.notice_period.value is None
    assert data.notice_period.page is None
    assert data.key_clauses.value == []
    assert data.other_fields == {}
    assert data.missing_fields == []


def test_extracted_field_keeps_page_reference():
    field = ExtractedField(value="60 days", page=4)
    assert field.model_dump() == {"value": "60 days", "page": 4}


def test_other_document_accepts_extra_fields():
    doc = OtherDocument(
        title=ExtractedField(value="Invoice", page=1),
        other_fields={
            "invoice_number": ExtractedField(value="INV-21", page=1),
        },
        missing_fields=["effective_date"],
    )
    assert doc.document_type == "Other"
    assert doc.other_fields["invoice_number"].value == "INV-21"
    assert "effective_date" in doc.missing_fields


def test_ask_response_allows_not_found():
    response = AskResponse(
        answer="This information is not present in the uploaded documents."
    )
    assert response.source is None
    assert response.page is None
    assert response.chunk_id is None


def test_search_request_filters_are_optional():
    request = SearchRequest(query="notice period")
    assert request.document_id is None
    assert request.document_type is None
