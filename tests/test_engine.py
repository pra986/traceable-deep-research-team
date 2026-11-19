"""Pytest suite for TraceableResearchManager."""

from __future__ import annotations

import asyncio

from deep_research.engine import TraceableResearchManager
from deep_research.models import ResearchReportData, SearchEvidence, SearchPlanItem

BASE_URL = "https://" + "example.com"


def test_partial_search_failure_survival() -> None:
    async def planner(_query: str) -> list[SearchPlanItem]:
        return [
            SearchPlanItem(query="valid query", reason="Primary evidence"),
            SearchPlanItem(query="failing query", reason="Secondary evidence"),
        ]

    async def searcher(item: SearchPlanItem) -> list[SearchEvidence]:
        if item.query == "failing query":
            raise RuntimeError("Upstream search timeout")
        return [
            SearchEvidence(
                query=item.query,
                source_url=f"{BASE_URL}/valid",
                title="Valid Source",
                excerpt="Verbatim excerpt from valid source.",
            )
        ]

    async def writer(
        _query: str, evidence: list[SearchEvidence]
    ) -> ResearchReportData:
        return ResearchReportData(
            short_summary="Summary from surviving evidence.",
            markdown_report="# Report\n\nEvidence collected.",
            cited_urls=[ev.source_url for ev in evidence],
            follow_up_questions=["What else should be checked?"],
        )

    manager = TraceableResearchManager(
        planner=planner,
        searcher=searcher,
        writer=writer,
    )
    report = asyncio.run(manager.run("test topic"))

    assert len(report.evidence) == 1
    assert report.evidence[0].source_url == f"{BASE_URL}/valid"
    assert report.failed_queries == ["failing query"]
    assert report.cited_urls == [f"{BASE_URL}/valid"]


def test_unretrieved_url_citation_rejection() -> None:
    async def planner(_query: str) -> list[SearchPlanItem]:
        return [SearchPlanItem(query="q1", reason="Verify citations")]

    async def searcher(item: SearchPlanItem) -> list[SearchEvidence]:
        return [
            SearchEvidence(
                query=item.query,
                source_url=f"{BASE_URL}/retrieved",
                title="Retrieved",
                excerpt="Exact retrieved excerpt.",
            )
        ]

    async def writer(
        _query: str, _evidence: list[SearchEvidence]
    ) -> ResearchReportData:
        return ResearchReportData(
            short_summary="Summary",
            markdown_report="# Report",
            cited_urls=[
                f"{BASE_URL}/retrieved",
                f"{BASE_URL}/hallucinated",
            ],
            follow_up_questions=[],
        )

    manager = TraceableResearchManager(
        planner=planner,
        searcher=searcher,
        writer=writer,
    )
    report = asyncio.run(manager.run("citation check"))

    assert report.cited_urls == [f"{BASE_URL}/retrieved"]
    assert report.rejected_urls == [f"{BASE_URL}/hallucinated"]


def test_email_failure_report_survival() -> None:
    async def planner(_query: str) -> list[SearchPlanItem]:
        return [SearchPlanItem(query="q1", reason="Core")]

    async def searcher(item: SearchPlanItem) -> list[SearchEvidence]:
        return [
            SearchEvidence(
                query=item.query,
                source_url=f"{BASE_URL}/source",
                title="Source",
                excerpt="Excerpt",
            )
        ]

    async def writer(
        _query: str, evidence: list[SearchEvidence]
    ) -> ResearchReportData:
        return ResearchReportData(
            short_summary="Report survives email error.",
            markdown_report="# Report",
            cited_urls=[ev.source_url for ev in evidence],
            follow_up_questions=[],
        )

    async def failing_emailer(_recipient: str, _report: ResearchReportData) -> None:
        raise ConnectionError("SMTP server unavailable")

    manager = TraceableResearchManager(
        planner=planner,
        searcher=searcher,
        writer=writer,
        emailer=failing_emailer,
    )
    report = asyncio.run(
        manager.run("email resilience", recipient="reader@example.com")
    )

    assert report.short_summary == "Report survives email error."
    assert report.email_sent is False
    assert report.email_error is not None
    assert "SMTP server unavailable" in report.email_error


def test_semaphore_concurrency_bounding() -> None:
    active = 0
    max_active = 0

    async def planner(_query: str) -> list[SearchPlanItem]:
        return [
            SearchPlanItem(query=f"q{i}", reason="Concurrency test")
            for i in range(5)
        ]

    async def searcher(item: SearchPlanItem) -> list[SearchEvidence]:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.02)
        active -= 1
        return [
            SearchEvidence(
                query=item.query,
                source_url=f"{BASE_URL}/{item.query}",
                title=item.query,
                excerpt=f"Excerpt for {item.query}",
            )
        ]

    async def writer(
        _query: str, evidence: list[SearchEvidence]
    ) -> ResearchReportData:
        return ResearchReportData(
            short_summary="Bounded concurrency.",
            markdown_report="# Report",
            cited_urls=[ev.source_url for ev in evidence],
            follow_up_questions=[],
        )

    manager = TraceableResearchManager(
        planner=planner,
        searcher=searcher,
        writer=writer,
        max_concurrency=2,
    )
    report = asyncio.run(manager.run("concurrency test"))

    assert max_active <= 2
    assert len(report.evidence) == 5
