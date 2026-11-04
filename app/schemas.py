from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    EMPLOYMENT_AGREEMENT = "Employment Agreement"
    COMPANY_POLICY = "Company Policy"
    PRODUCT_DOCUMENTATION = "Product Documentation"
    PROJECT_PROPOSAL = "Project Proposal"
    OTHER = "Other"


class ExtractedField(BaseModel):
    value: Any = None
    page: int | None = None


def _text_field() -> ExtractedField:
    return ExtractedField(value=None, page=None)


def _list_field() -> ExtractedField:
    return ExtractedField(value=[], page=None)


class EmploymentAgreement(BaseModel):
    document_type: str = DocumentType.EMPLOYMENT_AGREEMENT.value
    company_name: ExtractedField = Field(default_factory=_text_field)
    employee_name: ExtractedField = Field(default_factory=_text_field)
    job_title: ExtractedField = Field(default_factory=_text_field)
    effective_date: ExtractedField = Field(default_factory=_text_field)
    salary: ExtractedField = Field(default_factory=_text_field)
    notice_period: ExtractedField = Field(default_factory=_text_field)
    key_clauses: ExtractedField = Field(default_factory=_list_field)
    other_fields: dict[str, ExtractedField] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class CompanyPolicy(BaseModel):
    document_type: str = DocumentType.COMPANY_POLICY.value
    company_name: ExtractedField = Field(default_factory=_text_field)
    policy_name: ExtractedField = Field(default_factory=_text_field)
    policy_category: ExtractedField = Field(default_factory=_text_field)
    effective_date: ExtractedField = Field(default_factory=_text_field)
    eligibility: ExtractedField = Field(default_factory=_text_field)
    policy_rules: ExtractedField = Field(default_factory=_list_field)
    approval_process: ExtractedField = Field(default_factory=_text_field)
    other_fields: dict[str, ExtractedField] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ProductDocumentation(BaseModel):
    document_type: str = DocumentType.PRODUCT_DOCUMENTATION.value
    product_name: ExtractedField = Field(default_factory=_text_field)
    product_version: ExtractedField = Field(default_factory=_text_field)
    description: ExtractedField = Field(default_factory=_text_field)
    features: ExtractedField = Field(default_factory=_list_field)
    technical_requirements: ExtractedField = Field(default_factory=_list_field)
    installation_steps: ExtractedField = Field(default_factory=_list_field)
    api_endpoints: ExtractedField = Field(default_factory=_list_field)
    other_fields: dict[str, ExtractedField] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ProjectProposal(BaseModel):
    document_type: str = DocumentType.PROJECT_PROPOSAL.value
    project_name: ExtractedField = Field(default_factory=_text_field)
    organization: ExtractedField = Field(default_factory=_text_field)
    project_objective: ExtractedField = Field(default_factory=_text_field)
    problem_statement: ExtractedField = Field(default_factory=_text_field)
    proposed_solution: ExtractedField = Field(default_factory=_text_field)
    technologies: ExtractedField = Field(default_factory=_list_field)
    timeline: ExtractedField = Field(default_factory=_text_field)
    budget: ExtractedField = Field(default_factory=_text_field)
    deliverables: ExtractedField = Field(default_factory=_list_field)
    other_fields: dict[str, ExtractedField] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class OtherDocument(BaseModel):
    document_type: str = DocumentType.OTHER.value
    title: ExtractedField = Field(default_factory=_text_field)
    company_name: ExtractedField = Field(default_factory=_text_field)
    effective_date: ExtractedField = Field(default_factory=_text_field)
    key_clauses: ExtractedField = Field(default_factory=_list_field)
    other_fields: dict[str, ExtractedField] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


SCHEMA_BY_TYPE = {
    DocumentType.EMPLOYMENT_AGREEMENT: EmploymentAgreement,
    DocumentType.COMPANY_POLICY: CompanyPolicy,
    DocumentType.PRODUCT_DOCUMENTATION: ProductDocumentation,
    DocumentType.PROJECT_PROPOSAL: ProjectProposal,
    DocumentType.OTHER: OtherDocument,
}

ExtractedData = (
    EmploymentAgreement
    | CompanyPolicy
    | ProductDocumentation
    | ProjectProposal
    | OtherDocument
)


class FileMetadata(BaseModel):
    file_name: str
    file_type: str
    file_hash: str
    total_pages: int
    uploaded_at: datetime


class DocumentMetadata(BaseModel):
    document_type: str
    title: str | None = None
    short_summary: str | None = None
    key_topics: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)


class ProcessingMetadata(BaseModel):
    status: str
    schema_version: str = "1.0"


class DocumentRecord(BaseModel):
    document_id: str
    file_metadata: FileMetadata
    document_metadata: DocumentMetadata
    extracted_data: dict[str, Any]
    processing_metadata: ProcessingMetadata


class DocumentListItem(BaseModel):
    document_id: str
    file_name: str
    document_type: str | None = None
    uploaded_at: datetime
    status: str


class SearchRequest(BaseModel):
    query: str
    document_id: str | None = Field(
        default=None,
        description="Optional document id filter.",
    )
    document_type: str | None = Field(
        default=None,
        description="Optional document type filter.",
    )
    top_k: int | None = Field(
        default=None,
        description="Optional result count.",
    )


class SearchHit(BaseModel):
    document_id: str
    file_name: str
    page: int | None = None
    chunk_id: str
    score: float
    text: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]


class AskRequest(BaseModel):
    query: str
    document_id: str | None = Field(
        default=None,
        description="Optional document id filter.",
    )
    document_type: str | None = Field(
        default=None,
        description="Optional document type filter.",
    )


class AskResponse(BaseModel):
    answer: str
    source: str | None = None
    page: int | None = None
    chunk_id: str | None = None
    supporting_text: str | None = None
