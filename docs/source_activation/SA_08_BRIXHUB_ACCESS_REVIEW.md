# SA-08 — BrixHub access, provenance and licence review

## Decision

`brixhub` remains terminal `blocked`.

SA-08 found no repository evidence and no sufficiently trustworthy public official documentation establishing the exact BrixHub operator, legal entity, official API/export contract, data provenance, collection basis, permitted fields, retention/deletion rules, or customer-facing incorporation/redistribution rights required by this standalone commercial product.

Search results with similar names are not accepted as provider identity evidence. Third-party reputation or allegation material is risk context only and cannot prove operator identity, ownership, legality, data provenance or exact service terms.

## Actions explicitly not performed

This review does not:

- create or register a BrixHub account;
- authenticate or sign in;
- use Discord OAuth or any social-login flow;
- make a payment or cryptocurrency transfer;
- use Tor, a proxy or a copied browser session;
- bypass a challenge, CAPTCHA, MFA, paywall or access control;
- download a sample, archive, dataset, credential corpus or other provider content;
- import BrixHub data into the platform;
- inspect authenticated/private content;
- add a browser runtime or provider adapter;
- add credentials, secrets or schedules;
- perform controlled live validation.

## Why the source remains blocked

A useful provider activation dossier would need all of the following before the source can be reconsidered:

1. verified operator/legal-entity identity and accountable contact;
2. official current terms of service and privacy/data-processing terms attributable to that operator;
3. documented provenance and lawful collection basis for every offered data class;
4. explicit customer-facing commercial incorporation/redistribution rights for the product's intended use;
5. exact permitted and prohibited fields, countries/regions, subject categories and use cases;
6. retention, deletion, correction, suppression and data-subject-rights handling;
7. documented official API or export method, authentication model, quotas and cost model;
8. a safe schema/sample supplied through an approved channel that does not expose prohibited victim/private/credential material;
9. Source Governance review and approved hosts/paths/methods;
10. Provider Onboarding, secret references and deployment-specific authorization;
11. Source Portfolio registration, runtime capability and pause/kill-switch controls;
12. canonical mapping and evidence semantics that do not silently upgrade weak data into identity, exposure, compromise, need or opportunity claims;
13. a separately authorized controlled live validation.

## Safety and evidence boundary

The platform must not use leaked, stolen, victim, credential or private-communication data merely because a third party offers access to it. Likewise, third-party reputation claims are not canonical evidence about a provider.

```text
provider listing / allegation / reputation result
!= verified operator
!= lawful provenance
!= commercial licence
!= authorized data
!= canonical company evidence
```

## Completion gate

SA-08 may close only when:

- `brixhub` remains `blocked` with `activation_wave: SA-08` and a non-empty reason;
- the record has none of `adapter_present`, `authorized`, `executable`, `scheduled` or `live_tested`;
- the Source Coverage Matrix continues to identify `brixhub` as blocked;
- this decision document records the missing prerequisites and prohibited review actions;
- no account/login/payment/download/browser/Tor/Discord-OAuth path was introduced;
- deterministic reconciliation tests pass;
- one exact final SHA passes the complete backend and frontend CI;
- reviews and review threads are clear before squash merge.
