# Four route probes before implementation

Four authorized English requests, exactly one attempt each, over all eleven authored stone fixtures in disposable PostgreSQL/Typesense/Qdrant stores. Luna handled parsing and evidence; free Nemotron was configured for planning, selection and answers. The probes completed before route code changed. No semantic judge or automatic model retry ran. [Full stage outcomes and token telemetry](summary.json).

| Case | Question | Observed result |
| --- | --- | --- |
| [Tell Svetlana](runs/20261111T194459Z-tell-svetlana.json) | Tell me about Svetlana. | Name recognized; unresolved_question; no sources read. |
| [Madame's likes](runs/20261111T194523Z-madame-likes.json) | What does Madame Obsidian like? | Name recognized; unresolved_question; no sources read. |
| [Onyx care](runs/20261111T194546Z-onyx-care.json) | How should I care for onyx? | Luna incorrectly treated onyx as an individual name. No supported goal; unresolved_question. There is no ONYX type/chapter in the current authored corpus. |
| [Eight household types](runs/20261111T194746Z-eight-household-types.json) | Find one granite stone for a home where obsidian, basalt, marble, limestone, slate, sandstone, pumice, and gneiss already live. Check compatibility with each of the eight existing types separately, explain any conditions or conflicts, and say whether I can adopt the ninth stone now. | Parsed eight existing types; loaded all eight exact pair rules. Sir Pebble AVAILABLE but conditional_option; no unconditional recommendation. Answer mentioned only the three conditional pairs, failing the requested full eight-pair explanation. |

Langfuse traces: [Svetlana](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/531f44159edfbe289f82baa723d65018), [Madame](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/e4e9f293380a1e016a0e096708c209ea), [onyx](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/11fd1af3775dc7df7c6224a556f41efa), [eight types](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/4def51c5096e6211738af85616743ab0).

## Context observation

In the eight-type request the selection model reported 2,497 input tokens, planning 1,439, and Luna evidence 572. The parsing input included 131 ordinary and 1,761 cache-creation tokens. No generation reported a length finish. This is not a context-limit stress result: the eight pair documents are consumed by Python policy, rather than all being sent to the evidence model. The evidence model receives candidate sources and target identifiers. It returned empty individual evidence lists, leaving general pair verdicts and condition handling to Python.

The three conditional pairs were GRANITE+MARBLE, GRANITE+SANDSTONE and GRANITE+PUMICE. Their authored rules lack machine-checkable condition annotations, so the policy retained unmarked/unconfirmed conditions rather than inventing agreements. The other five pairs were harmonious. This checks the new candidate against each existing type; it does not recheck the existing eight against one another or prove whole-household compatibility.

Reported Luna cost across four requests: approximately $0.001079045. Free generations exposed token telemetry without explicit cost fields. HTTP 200 and the launcher asserting HTTP success are not semantic passes for the first three requests or the incomplete fourth answer.

Subsequent route changes were verified locally with fixture models; these archived requests were not repeated after the change.
