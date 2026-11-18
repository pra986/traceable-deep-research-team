# Traceable Deep Research Team (Project 19 / A3: Agentic Track)

Async multi-agent deep research pipeline with semaphore-bounded search, verbatim URL/excerpt preservation, citation verification, and decoupled email delivery.

## Architecture

The system coordinates specialized agents and deterministic guardrails through `TraceableResearchManager`:

- **Planner Agent**: Decomposes a research query into structured `SearchPlanItem` entries with explicit rationale.
- **Bounded Search Executor**: Executes asynchronous web searches concurrently under an `asyncio.Semaphore` limit, isolating per-query failures so partial search failures do not crash the pipeline.
- **Evidence Store (`SearchEvidence`)**: Preserves verbatim source URLs and retrieved excerpts without LLM paraphrasing or link rewriting.
- **Writer & Citation Verifier**: Synthesizes a structured `ResearchReportData` report and validates that every cited URL exists in the retrieved evidence set, rejecting hallucinated or unretrieved URLs.
- **Decoupled Email Delivery**: Dispatches the final report via an asynchronous mailer in a non-blocking, fault-isolated stage so email delivery failures never discard or fail the generated research report.

## 6-Stage Workflow

1. **Plan**: Generate a list of `SearchPlanItem` queries from the user prompt.
2. **Bounded Search**: Run search tasks concurrently with `asyncio.Semaphore(max_concurrency)` and `asyncio.gather(..., return_exceptions=True)`.
3. **Verbatim Evidence Capture**: Store `SearchEvidence` records containing exact `source_url` and `excerpt` values; record failed queries without halting.
4. **Synthesize Report**: Produce `ResearchReportData` (`short_summary`, `markdown_report`, `cited_urls`, `follow_up_questions`).
5. **Verify Citations**: Cross-check `cited_urls` against the retrieved `SearchEvidence` URLs and strip/reject any unretrieved URLs.
6. **Decoupled Delivery**: Attempt email delivery independently; capture delivery status (`email_sent`, `email_error`) while always returning the verified report.

## Data Contract

Defined in `deep_research/models.py` using Pydantic:

- `SearchPlanItem`: `query: str`, `reason: str`
- `SearchEvidence`: `query: str`, `source_url: str`, `title: str`, `excerpt: str`
- `ResearchReportData`: `short_summary: str`, `markdown_report: str`, `cited_urls: list[str]`, `follow_up_questions: list[str]`, `evidence: list[SearchEvidence]`, `failed_queries: list[str]`, `rejected_urls: list[str]`, `email_sent: bool`, `email_error: str | None`

## Production Controls

- **Semaphore Concurrency Bounding**: Prevents upstream rate-limit exhaustion during fan-out searches.
- **Partial Search Failure Survival**: Failed individual searches are logged in `failed_queries` while remaining evidence proceeds to synthesis.
- **Verbatim URL & Excerpt Preservation**: Source URLs and text snippets are retained verbatim from tool outputs.
- **Citation Verification Gate**: Any URL cited by the writer that was not retrieved in `SearchEvidence` is rejected and recorded in `rejected_urls`.
- **Non-Blocking Decoupled Email Delivery**: Email transport errors are captured in `email_error` without losing the completed `ResearchReportData`.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pytest -v
python -m deep_research.cli "Impact of agentic workflows on financial research"
```

## Attribution

Inspired by and adapted with pinned attribution from [`ed-donner/agents` (`2_openai/deep_research`)](https://github.com/ed-donner/agents/tree/main/2_openai/deep_research).
