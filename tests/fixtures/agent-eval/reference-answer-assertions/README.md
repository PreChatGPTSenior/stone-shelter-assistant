# Reference-answer assertions: meaning and completeness

[cases.json](cases.json) defines four English cases and twelve reviewed answer samples (31 assertion verdicts). It is a focused semantic-judge calibration set, not application run results or a replacement for the twenty-question search suite.

| Case | Required meaning | Deliberately wrong answers |
| --- | --- | --- |
| Svetlana | Staff observation of daily 05:00 singing and two complaints; preserve who dislikes noise | Omit the observation; assign the neighbors' dislike to Svetlana |
| Madame Obsidian | Vacuum cleaners cause anxiety; human company remains a separate preference | Reverse the meaning to calm tolerance; omit the trigger |
| Professor Quartzless | Individual quiet-home preference remains unknown; general granite knowledge is separate | Promote type information into proof about the individual |
| GRANITE + GRANITE | Both decision rotation and a shared decision deadline; guidance is not fulfilled agreement | Omit the deadline; answer only CONDITIONAL; invent fulfilled agreement/adoption approval |

Evidence is read from current authored fixtures using explicit pointers or existing chapter/pair builders. The missing Professor profile is represented explicitly as an absent field. All twelve samples deliberately pass reference_citations_valid, including the wrong ones: valid source IDs/scopes cannot prove correct meaning. Expected pass/fail labels were reviewed as calibration data and are never sent to the judge.

## Evaluation contract

tests/evaluation/answer_assertions.py supplies typed assertions, original fixture evidence, the final displayed answer and its scoped sections. It accepts faithful paraphrases rather than searching for keywords. Pass, missing, contradicted, unsupported and uncertain are distinct outcomes. Required passes and claim failures require exact answer quotations; support quotes must come from that assertion's allowed source IDs. A complete unique decision set is mandatory. Empty answers, prohibition-only rubrics, omitted assertions and fabricated quotes cannot produce an overall pass. Structural citation validity and semantic outcomes are reported independently; neither replaces the other.

The optional answer field overrides draft section text so a future caller can assess the final rendered response, including deterministic rules/fallbacks. Only listed assertions are evaluated. No universal entailment guarantee is claimed.

## Local checks and a future model run

Ordinary unit tests use fixture verdicts to verify reporting and error handling, not to prove that a model understands the text. Calibration metrics count false passes, false failures, abstentions and technical failures per assertion; uncertain/invalid responses get no correctness credit. A judge that gives every bad answer a pass fails calibration.

The opt-in runner is tests/live/test_reference_answer_assertions.py. It requires RUN_ANSWER_ASSERTION_EVALUATION=1 and an explicitly selected ANSWER_ASSERTIONS_JUDGE_MODEL. It makes one judge call per frozen sample, at 4096 tokens/medium reasoning with no retries. It saves fixture hashes, model settings, messages/observations, token/cost telemetry, per-assertion findings and Langfuse trace IDs under runs, then asserts calibration has no errors. Failed attempts remain recorded. No model call has been made for this suite.

This runner calibrates the judge on frozen answers; it does not run search or generate application answers. A future /questions evaluation must use the actual final answer and actual supplied/retrieved sources, resolve source aliases from run-specific IDs, and report retrieval/coverage separately. Do not substitute oracle fixture knowledge for missing retrieved evidence or infer an end-to-end success from judge calibration.
