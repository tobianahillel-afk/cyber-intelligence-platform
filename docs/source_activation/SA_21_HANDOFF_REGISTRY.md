# SA-21 — Handoff Registry

## Canonical ownership amendment

This registry makes the post-SA16 ownership correction explicit without changing the historical truth of SA-00 through SA-20 documents.

The Source Activation Master Plan and SA-15→SA-20 roadmap remain historical/normative context for their original waves. Where they leave a useful unresolved capability without a later named owner, this registry and `SA_21_ORPHANED_SOURCE_ACTIVATION_RECOVERY.md` assign that capability to SA-21.

## Handoffs into SA-21

| Historical owner/state | Capability | SA-21 ownership |
| --- | --- | --- |
| SA-02 / SA-15 incomplete | Brave Search | final entitlement/onboarding/live promotion |
| SA-14 / SA-15 incomplete | Mojeek | final entitlement/storage-rights/live promotion |
| SA-15 incomplete | Marginalia | commercial activation/live proof |
| SA-14 / SA-15 incomplete | PatentsView / current USPTO ODP | current contract/provider implementation/live proof |
| SA-15 incomplete | Google automated search route | legitimate automated route or fully integrated equivalent replacement |
| SA-15 omitted residual | Bing or independent web search provider | provider selection/implementation/live proof |
| SA-06 manual | official corporate disclosures | concrete provider/first-party acquisition activation |
| SA-06 manual | official regulatory change notices | concrete provider/regulator acquisition activation |
| SA-06 manual | official relationship disclosures | concrete provider/first-party acquisition activation |
| SA-06 manual | public partner directories | concrete provider activation |
| SA-06 manual | public case studies | concrete provider/first-party acquisition activation |
| SA-06 manual | public certificate relationship metadata | relationship-specific activation where semantics are explicit |
| SA-06 / SA-07 blocked | licensed corporate news metadata | concrete licensed provider activation |
| SA-07 blocked | commercial licensed dataset | concrete provider decomposition/activation or product-owner exclusion |
| SA-15 ambiguous with SA-18 | current-generation GDELT | provider activation in SA-21; downstream CTI semantics remain SA-18 |

## GDELT single-owner rule

There is no longer a shared provider-activation responsibility.

**SA-21 is the only Source Activation owner for current-generation GDELT provider integration.** It owns provider contract review, endpoint/product generation, schemas, quotas, storage/use terms, Source Governance, adapter/runtime/checkpoints and controlled real-provider live proof.

**SA-18 is a downstream consumer.** It owns only CTI/news evidence semantics after the SA-21 provider path is available: evidence classification, claim state, source independence, chronology and CTI/ransomware/phishing use.

If a future roadmap sentence says that SA-18 uses current GDELT/news evidence, it must be read as a consumption dependency on SA-21 rather than an authorization for a second GDELT adapter.

## Historical issue disposition

Historical SA-15 issue #115 allowed closure when unresolved dependencies were either genuinely resolved or explicitly handed to a later named SA with their concrete dependency preserved. The handoff to SA-21 / issue #158 satisfies that rule. Issue #115 is therefore closed as a completed handoff, while implementation remains open under #158.

## No silent ownership changes

Future decomposition may split SA-21 into micro-lots, but each capability above must retain a named owner until it reaches a truthful terminal outcome under the current Source Activation completeness definition.
