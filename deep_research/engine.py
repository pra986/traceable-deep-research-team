"""Core orchestration engine for traceable deep research."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from deep_research.models import ResearchReportData, SearchEvidence, SearchPlanItem

PlannerFn = Callable[[str], Awaitable[list[SearchPlanItem]]]
SearchFn = Callable[[SearchPlanItem], Awaitable[list[SearchEvidence] | SearchEvidence]]
WriterFn = Callable[[str, list[SearchEvidence]], Awaitable[ResearchReportData]]
EmailFn = Callable[[ResearchReportData], Awaitable[None]]


class TraceableResearchManager:
    """Coordinates planning, bounded search, citation verification, and delivery."""

    def __init__(
        self,
        planner: PlannerFn | None = None,
        searcher: SearchFn | None = None,
        writer: WriterFn | None = None,
        emailer: EmailFn | None = None,
        max_concurrency: int = 3,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self.planner = planner or self._default_planner
        self.searcher = searcher or self._default_searcher
        self.writer = writer or self._default_writer
        self.emailer = emailer
        self.max_concurrency = max_concurrency

    async def run(self, query: str, send_email: bool = True) -> ResearchReportData:
        """Execute the 6-stage traceable research pipeline."""
        plan = await self.planner(query)
        evidence, failed_queries = await self.run_searches(plan)
        draft = await self.writer(query, evidence)
        report = self.verify_citations(draft, evidence, failed_queries)
        if send_email and self.emailer is not None:
            report = await self.deliver_email(report)
        return report

    async def run_searches(
        self, plan: list[SearchPlanItem]
    ) -> tuple[list[SearchEvidence], list[str]]:
        """Execute searches under semaphore bound, surviving partial failures."""
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _bounded_search(item: SearchPlanItem) -> list[SearchEvidence]:
            async with semaphore:
                result = await self.searcher(item)
                if isinstance(result, SearchEvidence):
                    return [result]
                return list(result)

        raw_results: list[Any] = await asyncio.gather(
            *(_bounded_search(item) for item in plan),
            return_exceptions=True,
        )

        evidence: list[SearchEvidence] = []
        failed_queries: list[str] = []
        for item, outcome in zip(plan, raw_results):
            if isinstance(outcome, BaseException):
                failed_queries.append(item.query)
            else:
                evidence.extend(outcome)
        return evidence, failed_queries

    @staticmethod
    def verify_citations(
        draft: ResearchReportData,
        evidence: list[SearchEvidence],
        failed_queries: list[str],
    ) -> ResearchReportData:
        """Reject unretrieved URLs and attach verbatim retrieved evidence."""
        retrieved_urls = {ev.source_url for ev in evidence}
        verified_urls: list[str] = []
        rejected_urls: list[str] = []
        for url in draft.cited_urls:
            if url in retrieved_urls:
                if url not in verified_urls:
                    verified_urls.append(url)
            else:
                rejected_urls.append(url)

        return draft.model_copy(
            update={
                "cited_urls": verified_urls,
                "rejected_urls": rejected_urls,
                "evidence": list(evidence),
                "failed_queries": list(failed_queries),
            }
        )

    async def deliver_email(self, report: ResearchReportData) -> ResearchReportData:
        """Deliver report via decoupled mailer without failing the pipeline."""
        if self.emailer is None:
            return report
        try:
            await self.emailer(report)
            return report.model_copy(update={"email_sent": True, "email_error": None})
        except Exception as exc:  # noqa: BLE001
            return report.model_copy(
                update={"email_sent": False, "email_error": str(exc)}
            )

    @staticmethod
    async def _default_planner(query: str) -> list[SearchPlanItem]:
        return [
            SearchPlanItem(query=f"{query} overview", reason="Core background"),
            SearchPlanItem(query=f"{query} benchmarks", reason="Empirical evidence"),
        ]

    @staticmethod
    async def _default_searcher(item: SearchPlanItem) -> list[SearchEvidence]:
        slug = item.query.lower().replace(" ", "-")
        return [
            SearchEvidence(
                query=item.query,
                source_url=f"https://example.org/research/{slug}",
                title=f"Reference for {item.query}",
                excerpt=f"Verbatim findings for query: {item.query}.",
            )
        ]

    @staticmethod
    async def _default_writer(
        query: str, evidence: list[SearchEvidence]
    ) -> ResearchReportData:
        urls = [ev.source_url for ev in evidence]
        bullets = "\n".join(
            f"- [{ev.title or ev.source_url}]({ev.source_url}): {ev.excerpt}"
            for ev in evidence
        )
        return ResearchReportData(
            short_summary=f"Research summary for: {query} ({len(evidence)} sources).",
            markdown_report=f"# Research Report: {query}\n\n## Evidence\n{bullets}",
            cited_urls=urls,
            follow_up_questions=[f"What are the next steps for {query}?"],
        )
