# Provider onboarding runbook

## Purpose

The provider onboarding workspace automates every step that a documented public API exposes without authentication. When a provider requires an account, email verification, MFA, acceptance of terms, approval, or issuance of credentials, the workflow records a human checkpoint and waits for the operator.

The platform does not create fake accounts, control disposable mailboxes, solve CAPTCHAs, bypass MFA, scrape credentials, or circumvent provider approval and access controls.

## Safe secret model

Secret values must remain outside Git, application responses, logs, fixtures, and the application database. The database stores only validated references:

- `env://CIP_PROVIDER_SECRET`
- `file-secret:///run/secrets/provider-secret`
- `vault://secret/data/cip/provider`

The local runtime can verify environment and mounted-file references without returning their values. Vault references are accepted as deployment metadata but require a future vault resolver before they can be verified as available.

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

A successful local reference check proves that the deployment can access the configured secret references. Provider-specific authenticated connectivity must be implemented by the future INPI/RNE collection adapter before that source can collect data.

## LinkedIn official API workflow

LinkedIn remains a manual provider onboarding workflow:

1. Open the official developer application portal.
2. Sign in and complete provider-managed MFA.
3. Create or select the official developer application.
4. Request the required product access and scopes.
5. Record the workflow as awaiting provider approval.
6. Review the granted scopes and authorization evidence before changing source governance.

The onboarding module does not automate LinkedIn registration, authentication, MFA, product approval, or browser collection. The authorized browser source remains blocked until the isolated runtime in issue #3 exists and exact written authorization has been reviewed.

## Blocked providers

A blocked provider cannot be started, verified, or given a secret reference. BrixHub remains quarantined. Account creation, authentication, scraping, downloads, and imports are prohibited.

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
- `blocked`: do not attempt to bypass the restriction; review source governance and authorization evidence.

Revocation removes all registered references and verification timestamps while preserving the audit history.
