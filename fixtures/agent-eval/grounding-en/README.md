# English semantic grounding: prepared measurement

The active Typesense seed contains three concept definitions and ten contrasting examples: required candidate type, decision rotation agreement and decision deadline agreement. Runtime uses the selected Typesense snapshot, not this seed as a fallback. [Seed/export](../../knowledge/grounding/grounding_en-v1.json).

[holdout.json](holdout.json) contains ten different question wordings with reviewed expected decisions. These expected labels are not passed to the verifier. Catalog examples are training/context data; hold-out cases measure behavior on different wording, not unseen tasks or a general multilingual benchmark. Scope and adversarial coverage remain limited.

## Runner and interpretation

`tests/evaluation/test_grounding_model_evaluation.py` runs the actual `ground_question` node with a complete catalog in disposable Typesense, once per case, only with explicit `RUN_GROUNDING_EVALUATION=1`. The default model is `openai/gpt-6-luna`, with medium reasoning, 8192 tokens, no retries, and no paid semantic judge. No model experiment has been run for this catalog yet.

The runner records source-bound outcomes, catalog snapshot/hash, model settings, trace IDs, raw observations, usage/cost and elapsed time in versioned runs. Metrics separate three-way classification accuracy, binary acceptance accuracy, false acceptances, supported precision and technical failures. It requires every reviewed case exactly once and fails on execution errors or cases without a usable finding. Telemetry export errors remain separate from grounding outcomes.

Ordinary local tests supply fixture model decisions to verify orchestration, completeness and source binding; they do not measure model quality. Diagnostic runs record mismatches without an outcome pass claim. Set `RUN_GROUNDING_ACCEPTANCE=1` together with `RUN_GROUNDING_EVALUATION=1` to require each held-out outcome to match its existing reviewed label. This per-case gate does not measure parser quality or establish general model reliability.
