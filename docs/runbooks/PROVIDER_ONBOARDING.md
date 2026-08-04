# Provider onboarding runbook

## Purpose

The provider onboarding workspace targets zero-touch setup whenever the provider exposes an official, documented, and authorized provisioning path. An ordinary platform user should not have to generate, copy, paste, display, or manually rotate an API key when the provider permits programmatic onboarding.

Zero-touch does not mean bypassing provider controls. When a provider requires a person to accept terms, complete MFA, solve a CAPTCHA, prove identity, approve payment, request privileged scopes, or wait for provider approval, the workflow records a human checkpoint and pauses.

The platform does not create fake accounts, use disposable or temporary mailboxes, impersonate people, solve CAPTCHAs, bypass MFA, evade quotas, scrape credentials, or circumvent provider approval and access controls.

## Automation levels

Each provider must declare one onboarding level:

| Level | Behaviour |
|---|---|
| `anonymous` | No account or secret is required. The provider is connected automatically after source-governance approval. |
| `official_provisioning` | An official API, OAuth flow, dynamic client-registration mechanism, service-account interface, or documented key-management endpoint provisions the account and credentials automatically. |
| `authorized_browser` | A provider-authorized browser workflow performs only the exact reviewed steps and fields. It must not bypass anti-automation controls or provider restrictions. |
| `human_checkpoint` | The provider requires an action that cannot lawfully or reliably be automated. The workflow pauses and records the required action. |
| `blocked` | The source or onboarding method is not authorized and no execution is permitted. |

A provider may move between these levels only after its terms, authorization evidence, and technical implementation have been reviewed.

## Managed service identity

Automatic account creation, where expressly permitted by the provider, uses an organization-controlled service identity rather than a personal or disposable identity.

Required properties:

- a durable mailbox or alias owned by the deploying organization, such as `providers@company.example` or a provider-specific alias;
- no temporary-email, catch-all abuse, rented inbox, fake identity, or mailbox created to evade account restrictions;
- a provider-specific randomly generated password with sufficient entropy;
- no password reuse across providers;
- immediate storage of the password in the deployment secret backend;
- a stable account owner, recovery path, and offboarding procedure;
- an audit record linking the account to the provider, purpose, organization, and authorization decision;
- one account per legitimate organizational need, never account multiplication to evade quotas, trials, bans, or product limits.

The platform may create the service identity or provider account automatically only when the organization controls the identity and the provider explicitly permits the registration method.

## Managed mailbox verification

The deployment may connect to the organization-controlled service mailbox through an approved mailbox API, OAuth application, service account, or equivalent consented integration.

When unattended email verification is permitted by the provider, the onboarding worker may:

1. create the provider account with the approved service address;
2. wait for a message from the exact expected provider sender or domain;
3. restrict processing to the active onboarding transaction and a short time window;
4. extract the one-time verification code or provider-owned verification link;
5. validate the destination host against an allowlist;
6. submit the code or follow the link through the approved onboarding path;
7. store only the verification result, timestamps, message fingerprint, and audit metadata;
8. delete or expire temporary processing data according to the mailbox-retention policy.

The worker must not search unrelated mail, retain mailbox content, use verification messages as a substitute for MFA, or follow links outside the provider allowlist. A provider email that requests identity proof, MFA, payment, contract acceptance, or another privileged action becomes a human checkpoint.

## Automatic credential and API-key provisioning

The preferred order is:

1. OAuth or another delegated authorization protocol;
2. official service-account or machine-identity API;
3. official API-key management endpoint;
4. provider-authorized browser workflow;
5. human checkpoint when no approved automated path exists.

When a credential is generated automatically:

- the value is written directly into the secret backend and is never returned to the browser, application API, logs, audit events, database, or Git;
- the application database stores only a redacted reference, provider identifier, scopes, creation time, expiry time, rotation state, revocation state, and a non-secret fingerprint where useful;
- requested scopes are the minimum required for the approved collector;
- a provider-specific connectivity test validates the credential without exposing it;
- failed provisioning triggers immediate revocation or cleanup where supported;
- expiration and rotation are scheduled before the credential becomes unusable;
- revocation is automatic when the source is disabled, authorization expires, the deployment is offboarded, or compromise is suspected.

A normal HTML console is not automatically an approved key-generation API. Browser automation requires exact written authorization or provider documentation that permits the workflow.

## Human checkpoints that remain mandatory

The following steps are not silently automated unless the provider offers an explicit machine workflow covering them:

- acceptance of contractual terms or material licence changes;
- payment, subscription choice, purchase, or billing approval;
- CAPTCHA or anti-bot challenge;
- MFA, passkey, hardware token, biometric, or personal identity verification;
- KYC, company verification, regulated-sector approval, or proof documents;
- privileged product, partner, advertising, profile, or data-access approval;
- consent on behalf of another person or organization;
- access to private groups, private messages, non-public datasets, or restricted workspaces;
- any step whose automation would breach provider terms, law, privacy obligations, or technical controls.

The product should minimize these checkpoints, explain the exact action, and resume automatically after the authorized operator completes it.

## Safe secret model

Secret values must remain outside Git, application responses, logs, fixtures, and the application database. The database stores only validated references:

- `env://CIP_PROVIDER_SECRET`
- `file-secret:///run/secrets/provider-secret`
- `vault://secret/data/cip/provider`

The local runtime can verify environment and mounted-file references without returning their values. Vault references are accepted as deployment metadata but require a vault resolver before they can be verified as available.

The target production architecture must support direct secret writes from the provisioning worker to the configured secret backend so that the ordinary user never handles the raw credential.

## Public providers

The following providers require no secret and are synchronized as connected:

- CISA KEV
- TED Search API
- BOAMP
- Greenhouse Job Board API
- Lever Postings API
- SmartRecruiters Posting API
- API Recherche d'entreprises
- GLEIF
- BODACC company events

Sirene is represented using the documented open-data mode. Its collection policy remains independently governed and must still be enabled before jobs can run.

## INPI/RNE workflow

The current INPI/RNE integration remains a human-checkpoint workflow because no approved programmatic account-provisioning path has yet been implemented.

1. Open the official Data INPI registration or account portal from the Sources page.
2. Sign in through the provider-controlled page.
3. Complete any email verification or MFA requested by the provider.
4. Review and accept the applicable provider terms.
5. Request the documented API or SFTP access in the account.
6. Record `awaiting_provider_approval` in the Sources page while the provider processes the request.
7. Retrieve the technical username and password issued by the provider.
8. Store those values in the deployment secret backend, never in the platform.
9. Register references such as:
   - `env://CIP_INPI_RNE_USERNAME`
   - `env://CIP_INPI_RNE_PASSWORD`
10. Select **Verify configuration**. The deployment checks only whether both references can be resolved.

A future implementation may remove manual steps only if INPI exposes or authorizes an official machine provisioning route. A successful local reference check proves that the deployment can access the configured secret references. Provider-specific authenticated connectivity must be implemented by the future INPI/RNE collection adapter before that source can collect data.

## LinkedIn official API workflow

LinkedIn remains a human-checkpoint provider onboarding workflow:

1. Open the official developer application portal.
2. Sign in and complete provider-managed MFA.
3. Create or select the official developer application.
4. Request the required product access and scopes.
5. Record the workflow as awaiting provider approval.
6. Review the granted scopes and authorization evidence before changing source governance.

The onboarding module does not automate LinkedIn registration, authentication, MFA, product approval, or browser collection unless LinkedIn later exposes or grants an explicit machine provisioning path for the exact workflow. The authorized browser source remains blocked until the isolated runtime in issue #3 exists and exact written authorization has been reviewed.

## Blocked providers

A blocked provider cannot be started, verified, or given a secret reference. BrixHub remains quarantined. Account creation, authentication, scraping, downloads, imports, and credential provisioning are prohibited until source governance explicitly approves the provider and exact onboarding method.

## User experience target

For a fully approved provider with machine provisioning, the ordinary user should see only:

1. **Enable source**;
2. onboarding progress and any provider-side waiting state;
3. a clear human checkpoint only when genuinely required;
4. **Connected**, with scopes, health, expiry, last rotation, and audit state;
5. **Revoke**, without ever seeing the raw password, token, or API key.

The platform must never claim that every provider can be 100% automated. It must instead maximize automation within each provider's officially permitted capabilities and make unavoidable human actions explicit.

## API workflow

List providers:

```text
GET /v1/provider-onboarding/providers
```

Start a workflow:

```text
POST /v1/provider-onboarding/providers/{source_id}/start
```

Record a human checkpoint:

```text
POST /v1/provider-onboarding/providers/{source_id}/human-checkpoint
```

Register a secret reference:

```text
POST /v1/provider-onboarding/providers/{source_id}/secret-reference
```

Verify deployment references:

```text
POST /v1/provider-onboarding/providers/{source_id}/verify
```

Revoke the configuration and remove all stored references:

```text
POST /v1/provider-onboarding/providers/{source_id}/revoke
```

Every state-changing operation requires an actor and creates an audit event. API responses return redacted reference schemes such as `env://***`, never the target variable or secret value.

## Failure handling

- `missing_secret_references`: register every required reference.
- `secret_reference_unavailable`: configure the referenced environment variable or mounted secret in the deployment.
- `manual_provider_authorization_required`: complete and review the provider-controlled authorization workflow.
- `mailbox_verification_timeout`: verify the managed mailbox connector and provider sender allowlist.
- `unexpected_verification_sender`: reject the message and require review.
- `credential_provisioning_failed`: revoke partial credentials and preserve the audit result.
- `scope_mismatch`: revoke or reject credentials whose granted permissions exceed or omit the approved scopes.
- `blocked`: do not attempt to bypass the restriction; review source governance and authorization evidence.

Revocation removes all registered references and verification timestamps while preserving the audit history.

## Required implementation tests

The zero-touch implementation is incomplete until tests prove that:

- disposable-email domains and unapproved mailboxes are rejected;
- generated passwords are unique, sufficiently strong, and never logged or persisted outside the secret backend;
- verification messages are limited by provider sender, recipient, transaction, time window, and link-host allowlist;
- unrelated mailbox content cannot be read or retained;
- CAPTCHA, MFA, payment, contractual acceptance, identity proof, and provider approval create human checkpoints;
- API keys and tokens are written directly to the secret backend;
- raw credentials never appear in API responses, database rows, logs, exceptions, analytics, or frontend state;
- requested and granted scopes are validated;
- connectivity tests are provider-specific and non-destructive;
- partial provisioning is cleaned up or revoked;
- expiration, rotation, revocation, and authorization expiry are enforced;
- account creation cannot be used to evade quotas, bans, trials, or per-customer limits;
- every transition and external side effect is auditable and idempotent.
