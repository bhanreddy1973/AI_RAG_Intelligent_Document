from pydantic import BaseModel, ValidationError

from app.nvidia_client import LLMError, chat_json
from app.parser import Page
from app.schemas import SCHEMA_BY_TYPE, DocumentType, ExtractedField


SKIP_FIELDS = {"document_type", "other_fields", "missing_fields"}


def _field_names(schema_cls: type[BaseModel]) -> list[str]:
    return [name for name in schema_cls.model_fields if name not in SKIP_FIELDS]


def _is_list_field(schema_cls: type[BaseModel], name: str) -> bool:
    sample = schema_cls()
    return isinstance(getattr(sample, name).value, list)


def _to_field(raw, is_list: bool) -> ExtractedField:
    if raw is None:
        return ExtractedField(value=[] if is_list else None, page=None)

    if isinstance(raw, dict):
        value = raw.get("value")
        page = raw.get("page")
        if page is not None:
            try:
                page = int(page)
            except (TypeError, ValueError):
                page = None
        if is_list:
            if value is None:
                value = []
            elif not isinstance(value, list):
                value = [value]
        elif value == "":
            value = None
        return ExtractedField(value=value, page=page)

    if is_list:
        value = raw if isinstance(raw, list) else [raw]
        return ExtractedField(value=value, page=None)
    return ExtractedField(value=raw, page=None)


def _is_missing(field: ExtractedField, is_list: bool) -> bool:
    if is_list:
        return not field.value
    return field.value is None or field.value == ""


def extract_fields(pages: list[Page], document_type: DocumentType) -> BaseModel:
    schema_cls = SCHEMA_BY_TYPE[document_type]
    names = _field_names(schema_cls)
    body = "\n\n".join(f"[Page {page.page_number}]\n{page.text}" for page in pages)

    data = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "Extract fields that are explicitly present in the document. "
                    "Do not invent values. Missing text fields must be null. "
                    "Missing list fields must be []. "
                    "Each field is {\"value\": ..., \"page\": number or null}. "
                    "Put extra useful facts in other_fields. "
                    'Return JSON: {"fields": {...}, "other_fields": {...}}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Document type: {document_type.value}\n"
                    f"Fields: {names}\n\n"
                    f"{body[:80000]}"
                ),
            },
        ],
        max_tokens=1500,
    )

    raw_fields = data.get("fields") or {}
    raw_other = data.get("other_fields") or {}
    if not isinstance(raw_fields, dict):
        raw_fields = {}
    if not isinstance(raw_other, dict):
        raw_other = {}

    payload = {"document_type": document_type.value}
    missing = []
    for name in names:
        is_list = _is_list_field(schema_cls, name)
        field = _to_field(raw_fields.get(name), is_list)
        payload[name] = field
        if _is_missing(field, is_list):
            missing.append(name)

    other_fields = {}
    for key, raw in raw_other.items():
        if not key or key in SKIP_FIELDS:
            continue
        other_fields[str(key)] = _to_field(raw, is_list=False)

    payload["other_fields"] = other_fields
    payload["missing_fields"] = missing

    try:
        return schema_cls.model_validate(payload)
    except ValidationError as exc:
        raise LLMError(f"Extracted JSON failed schema validation: {exc}") from exc
