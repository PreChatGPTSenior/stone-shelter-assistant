# Current question workflow

```mermaid
flowchart TD
    request([POST /api/v1/questions]) --> parse[Parse criteria and prepare queries/filters]
    parse --> grounding[Verify sensitive proposals against English catalog]
    grounding --> plan[Validate tool plan]
    plan -->|General recommendation| prepared[Prepare one hybrid call]
    plan -->|Named recommendation| named[Prepare exact-name lexical call]
    plan -->|Named info / history / status / care / compatibility| facts[Execute reference plan]
    plan -->|Invalid or unresolved| clarify[Clarify request]
    prepared --> hybrid[Hybrid tool: two retrieval calls]
    hybrid --> ts[Typesense]
    hybrid --> q[Qdrant + query embedding]
    ts --> rrf[RRF: deduplicate, score, retain provenance]
    q --> rrf
    named --> lexical[Lexical tool: one retrieval call]
    rrf --> select[LLM selects up to 3 using parsed criteria]
    lexical --> select
    select --> cards[Read PostgreSQL cards]
    cards --> verify[Verify current PostgreSQL status]
    verify --> evaluate[Load observations; validate quoted evidence and apply policy]
    evaluate --> answer[Render decisions and grounded explanation]
    facts --> referenceEvidence[Extract and validate scoped reference quotes]
    referenceEvidence --> reference[Compose cited sections / render verified facts]
    answer --> result([HTTP result + trace_id])
    reference --> result
    clarify --> result
    prepared -->|Retrieval allowance exceeded| stop[Stop]
    parse -.-> budget[Budget admission for model stages]
    grounding -.-> budget
    plan -.-> budget
    select -.-> budget
    evaluate -.-> budget
    referenceEvidence -.-> budget
    answer -.-> budget
```

General recommendations make one hybrid call, not a model-controlled search loop. Hybrid retrieval consumes two of the four allowed backend calls; named candidate search consumes one. Named status, exact pairs and encyclopedia care keep their reference routes. Search rank never overrides current status or source validation.

Langfuse retains one trace_id: engine inputs and durations, RRF ranks/contributions and dropped hits, per-candidate provenance, selected/unselected IDs, verified statuses and final evaluations. Engine/fusion observations reference source texts already recorded in the trace. Budget admission remains the pilot stub.
