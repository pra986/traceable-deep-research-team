"""Data contracts for the traceable deep research pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchPlanItem(BaseModel):
    """A single planned web search query with its rationale."""

    query: str = Field(..., min_length=1, description="Search query string.")
    reason: str = Field(..., min_length=1, description="Why this search is needed.")


class SearchEvidence(BaseModel):
    """Verbatim evidence captured from a search result."""

    query: str = Field(..., description="Originating search query.")
    source_url: str = Field(..., description="Verbatim retrieved source URL.")
    title: str = Field(default="", description="Source title.")
    excerpt: str = Field(..., description="Verbatim retrieved text excerpt.")


class ResearchReportData(BaseModel):
    """Final research report with verified citations and delivery status."""

    short_summary: str = Field(..., description="Executive summary of findings.")
    markdown_report: str = Field(..., description="Full markdown research report.")
    cited_urls: list[str] = Field(
        default_factory=list,
        description="Verified URLs cited in the report.",
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Suggested follow-up research questions.",
    )
    evidence: list[SearchEvidence] = Field(
        default_factory=list,
        description="Verbatim retrieved search evidence.",
    )
    failed_queries: list[str] = Field(
        default_factory=list,
        description="Queries that failed during bounded search execution.",
    )
    rejected_urls: list[str] = Field(
        default_factory=list,
        description="Unretrieved URLs rejected by citation verification.",
    )
    email_sent: bool = Field(
        default=False,
        description="Whether decoupled email delivery succeeded.",
    )
    email_error: str | None = Field(
        default=None,
        description="Error message if decoupled email delivery failed.",
    )
