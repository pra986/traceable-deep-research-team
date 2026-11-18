# Architecture Overview

`TraceableResearchManager` implements a 6-stage asynchronous deep research pipeline designed for traceability, bounded concurrency, and fault tolerance.

## Components

1. **Planner (`plan_searches`)**: Converts a user research prompt into a structured list of `SearchPlanItem` objects (`query`, `reason`).
2. **Bounded Search Executor (`run_searches`)**: Uses `asyncio.Semaphore(max_concurrency)` to bound concurrent search requests and `asyncio.gather(..., return_exceptions=True)` so individual search errors are isolated into `failed_queries` rather than aborting the run.
3. **Verbatim Evidence Store (`SearchEvidence`)**: Retains exact `source_url`, `title`, and `excerpt` strings returned by the search backend.
4. **Report Synthesizer (`write_report`)**: Produces a `ResearchReportData` object containing `short_summary`, `markdown_report`, `cited_urls`, and `follow_up_questions`.
5. **Citation Verifier (`verify_citations`)**: Filters `cited_urls` against the set of retrieved `SearchEvidence.source_url` values. Any unretrieved URL is removed from `cited_urls` and recorded in `rejected_urls`.
6. **Decoupled Mailer (`deliver_email`)**: Sends the report asynchronously in a `try/except` block so email transport failures populate `email_error` while still returning the verified `ResearchReportData`.

## Data Flow

```
Query -> [Planner] -> SearchPlanItem[]
      -> [Semaphore-Bounded Search] -> SearchEvidence[] + failed_queries[]
      -> [Writer] -> Draft ResearchReportData
      -> [Citation Verifier] -> Verified cited_urls[] + rejected_urls[]
      -> [Decoupled Emailer] -> Final ResearchReportData (email_sent / email_error)
```
