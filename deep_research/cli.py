"""Runnable CLI demo entrypoint for the traceable deep research pipeline."""

from __future__ import annotations

import argparse
import asyncio

from deep_research.engine import TraceableResearchManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the traceable multi-agent deep research pipeline."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="Impact of agentic AI on financial research workflows",
        help="Research topic or question to investigate.",
    )
    parser.add_argument(
        "--recipient",
        default=None,
        help="Optional email address for decoupled report delivery.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=3,
        help="Maximum concurrent search tasks (semaphore bound).",
    )
    return parser


async def _run_cli(query: str, recipient: str | None, max_concurrency: int) -> None:
    manager = TraceableResearchManager(max_concurrency=max_concurrency)
    report = await manager.run(query=query, recipient=recipient)

    print("=== Summary ===")
    print(report.short_summary)
    print("\n=== Report ===")
    print(report.markdown_report)
    print("\n=== Cited URLs ===")
    for url in report.cited_urls:
        print(f"- {url}")
    if report.failed_queries:
        print("\n=== Failed Queries ===")
        for failed in report.failed_queries:
            print(f"- {failed}")
    if report.rejected_urls:
        print("\n=== Rejected Citations ===")
        for rejected in report.rejected_urls:
            print(f"- {rejected}")
    if recipient:
        print(f"\nEmail sent: {report.email_sent}")
        if report.email_error:
            print(f"Email error: {report.email_error}")


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(_run_cli(args.query, args.recipient, args.max_concurrency))


if __name__ == "__main__":
    main()
