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
    answer --> combine[Combine completed parts and their sources]
    combine --> result([HTTP result + trace_id])
    reference -->|Reference only| result
    reference -->|Also recommendation| saved[Preserve reference component]
    saved -->|General candidate goal| prepared
    saved -->|Named candidate target| named
    clarify --> result
    prepared -->|Retrieval allowance exceeded| stop[Stop]
    stop --> combine
    parse -.-> budget[Budget admission for model stages]
    grounding -.-> budget
    plan -.-> budget
    select -.-> budget
    evaluate -.-> budget
    referenceEvidence -.-> budget
    answer -.-> budget
```

General recommendations make one hybrid call, not a model-controlled search loop. Hybrid retrieval consumes two of the four allowed backend calls; named candidate search consumes one. Named status, exact pairs and encyclopedia care keep their reference routes. Search rank never overrides current status or source validation.

For mixed questions the graph fixes reference-first execution; the planner covers the union of goals and orders dependent reference reads. Independent information identity and recommendation target are separate. The final combination preserves both source sets and authoritative statuses, and completed reference work survives an empty or stopped candidate branch. The diagram's combine step represents the shared result helper, not another model generation.

Langfuse retains one trace_id: engine inputs and durations, RRF ranks/contributions and dropped hits, per-candidate provenance, selected/unselected IDs, verified statuses and final evaluations. Engine/fusion observations reference source texts already recorded in the trace. Budget admission remains the pilot stub.
