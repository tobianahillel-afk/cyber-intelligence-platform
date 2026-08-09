# Lot 22 — Conditional, premium, LinkedIn, Discord, and BrixHub integrations

## Status

Implementation in progress on `agent/conditional-premium-integrations` from exact Lot 21 squash `f797128dd71eb1cbe5716e73478565e6942cb458`.

Target release: `0.23.0`, not bumped until a complete functional candidate is green.

## Outcome

Lot 22 adds a provider-specific approval layer for sources whose use depends on licences, scopes, administrator consent, customer-provided access, or written authorization.

It does not weaken or replace Source Governance, Provider Onboarding, or Source Portfolio controls. A conditional provider must satisfy all of them plus its provider-specific approval dossier before execution can be eligible.

## Authorization boundary

```text
catalog candidate
!= approved provider

account availability
!= approved account or scope

licensed product
!= authorization for every field or purpose

public professional profile
!= platform automation authorization

configured secret reference
!= executable provider

positive provider approval dossier
+ valid onboarding state
+ allowed source-policy decision
+ registered adapter capability
+ live quota/cost/kill-switch state
= conditional execution eligibility
```

Eligibility is still not a network request by itself. The ordinary analyst UI remains database-first.

## Existing controls reused

Lot 22 composes the existing control planes rather than duplicating them:

- **Source Governance:** source status, authorization document, purposes, data categories, host/path scope, automation permission, raw-storage permission, rate limits and human review;
- **Provider Onboarding:** official provider profile, onboarding state, service identity, secret references, verification, expiry, revocation and rotation;
- **Source Portfolio:** adapter capability, execution status, freshness, quota, monthly cost, quality, health and runtime pause state;
- **Data Governance:** retention, suppression and deletion obligations;
- **Lot 21 privacy boundary:** professional context remains separate from private-life data and outreach authorization.

## Provider-specific approval dossier

A dossier records only references and approved capabilities, never raw secrets. It includes:

- source/provider identity;
- provider family;
- exact approved access method;
- draft, pending-review, approved, expired, revoked or paused state;
- authorization-document reference;
- licence/contract reference when applicable;
- reviewed terms reference and terms-review state;
- exact approved scopes;
- exact approved fields;
- approved purposes;
- approved data categories;
- explicit retention maximum;
- automation permission;
- optional account/service-identity reference;
- review, review-due, expiry, revocation and pause metadata.

Approved dossiers fail construction unless required review artifacts and retention limits are explicit.

## Provider method boundaries

The initial executable-method policy is deliberately conservative:

- **LinkedIn:** official API or separately licensed API only;
- **Discord:** administrator-installed connector or explicitly authorized export only;
- **BrixHub:** no executable method by default until an exact access-path, field, licence and security review is approved;
- **premium CTI:** licensed API or authorized export;
- **commercial datasets:** licensed API, authorized export, or contract-bound customer-provided access;
- **other conditional providers:** method still requires a positive provider dossier plus every shared runtime gate.

This lot contains no fake-account, copied-cookie, CAPTCHA/MFA bypass, ban-evasion, or proxy-rotation path.

## Fail-closed execution gate

A request is blocked if any relevant condition fails, including:

- dossier not approved, expired, revoked or paused;
- terms changed or review overdue;
- provider/method mismatch;
- source or account mismatch;
- requested scope, field, purpose or data category outside approval;
- retention longer than approved;
- automation not approved;
- onboarding not ready;
- Source Governance denial;
- missing adapter capability;
- active kill switch;
- exhausted quota;
- exhausted monthly cost budget.

The decision preserves explicit blocking reasons for audit and analyst review.

## Current first slice

Implemented first:

- `conditional_integrations` bounded context;
- provider/access/approval/terms/blocking enums;
- immutable approval-dossier contract;
- exact conditional-execution request and runtime-dependency contracts;
- deterministic fail-closed evaluation;
- explicit provider-method policy;
- unit tests for provider restrictions, approval artifacts, scopes, fields, purpose, categories, retention, account isolation, expiry, revocation, terms changes, onboarding, kill switch, quota and cost.

## Planned persistence and control plane

The next slice will persist:

- current provider approval dossier;
- immutable dossier revision/audit history;
- provider terms/licence review evidence references;
- kill-switch and pause decisions;
- execution-decision audit without secrets;
- unique-value measurements linked to the Source Portfolio value model.

Protected APIs/UI will manage dossier review and show why a provider is blocked. They will not perform provider login or collection from the page view.

## Exit gate

A conditional source cannot execute until its exact provider dossier is positive and every existing shared runtime gate is also positive. Revocation, pause, expiry, terms change, kill switch, quota exhaustion, or cost exhaustion must prevent new execution immediately without corrupting previously stored provenance or privacy obligations.
