# English semantic grounding: prepared measurement

The active Typesense seed contains three concept definitions and ten contrasting examples: required candidate type, decision rotation agreement and decision deadline agreement. Runtime uses the selected Typesense snapshot, not this seed as a fallback. [Seed/export](../../../../fixtures/knowledge/grounding/grounding_en-v1.json).

[holdout.json](holdout.json) contains ten different question wordings with reviewed expected decisions. These expected labels are not passed to the verifier. Catalog examples are training/context data; hold-out cases measure behavior on different wording, not unseen tasks or a general multilingual benchmark. Scope and adversarial coverage remain limited.

Before replacing the regex recognizer, its binary accepted/rejected outputs were frozen in historical_regex_accepted. Original question_grounding.py SHA-256: 41d0d6edfe535211f3446730599967a42096b6a6c99c94d6fb294272c1e8b1a6. The old source is not retained as executable legacy support. Its binary acceptance accuracy on these ten authored cases was 8/10; two false acceptances concern another household's agreement and the type of an already owned stone.

## Runner and interpretation

tests/integration/test_grounding_model_evaluation.py runs the actual ground_question node with a complete catalog in disposable Typesense, once per case, only with explicit RUN_GROUNDING_EVALUATION=1. Default model is openai/gpt-6-luna, medium reasoning, 8192 tokens, no retries or paid semantic judge. No model experiment has been run for this catalog yet.

The runner records source-bound outcomes, catalog snapshot/hash, model settings, trace IDs, raw observations, usage/cost and elapsed time in versioned runs. Metrics separate three-way classification accuracy, binary acceptance accuracy, false acceptances, supported precision and technical failures. Technical errors cannot count as correct negative answers. The old baseline has binary outcomes only; do not compare it as though it made three-way semantic classifications.

Ordinary local tests supply fixture model decisions to verify orchestration, completeness and source binding; they do not measure model quality. The opt-in runner asserts recording completeness, not semantic success. No improvement over the former recognizer is claimed before the real comparison.
