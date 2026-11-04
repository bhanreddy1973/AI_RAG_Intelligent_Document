from app.nvidia_client import chat_json
from app.schemas import DocumentType

TYPE_LABELS = [item.value for item in DocumentType]


def classify_document(short_summary: str, title: str = "") -> DocumentType:
    data = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "Classify the document into exactly one type. "
                    f"Allowed values: {TYPE_LABELS}. "
                    "If it does not match a specific type, use Other. "
                    'Return JSON: {"document_type": "..."}'
                ),
            },
            {
                "role": "user",
                "content": f"Title: {title}\nSummary: {short_summary}",
            },
        ],
        max_tokens=80,
    )

    label = str(data.get("document_type") or "Other").strip()
    for item in DocumentType:
        if item.value.lower() == label.lower():
            return item
    return DocumentType.OTHER
