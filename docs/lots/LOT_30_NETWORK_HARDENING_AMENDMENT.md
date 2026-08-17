# Lot 30 — Network acquisition hardening amendment

## Status

`PLANNED_LOCKED` as part of Lot 30.

## Purpose

This amendment assigns the remaining Lot 12 DNS-resolution hardening risk to an existing future product lot instead of leaving it as unowned "future hardening".

Lot 12 explicitly recorded DNS-resolution pinning as a residual topic. SA-16 subsequently delivered strong host/path/origin/source-policy enforcement, redirect checks, browser request interception, bounded HTTP/browser/download execution, and controlled authenticated acquisition. Those controls materially reduce attack surface but do not by themselves prove protection against a DNS answer changing from an approved public address to an internal or otherwise forbidden address between authorization and connection.

Lot 30 therefore owns the final network-resolution safety boundary for every governed outbound acquisition path.

## Primary business outcome

Ensure that an authorized hostname cannot be used, through DNS rebinding, resolver drift, CNAME manipulation, address-family tricks, redirect/retry behavior, or connection reuse, to make the platform connect to an internal, local, non-routable, or otherwise forbidden network address.

## Dependencies

- Lot 12 governed public HTTP acquisition;
- Lot 23 governed research execution boundaries;
- merged SA-16 static, browser, authenticated, and controlled-download runtimes;
- Lot 30 observability, resilience, failure recovery, and operational telemetry.

## Deliverables

- one shared outbound-address policy used by static HTTP, browser interception, authenticated browser flows, controlled downloads, and any other product-owned HTTP client;
- canonical handling of A, AAAA, CNAME chains, trailing-dot hosts, IDNA hostnames, and IPv4-mapped IPv6 addresses;
- explicit rejection of loopback, private, link-local, multicast, unspecified, reserved/documentation-only, carrier-grade/NAT or other non-approved address classes as appropriate to the deployment policy;
- validation of every resolved address set before connection, not only validation of the hostname string;
- prevention of a later resolver answer silently changing an already-authorized destination into a forbidden address;
- redirect, retry, reconnect, browser-subresource, OAuth/token, authenticated navigation, and download paths re-evaluate address safety when a new network connection may occur;
- fail-closed behavior on ambiguous resolution, mixed public/private answer sets, forbidden CNAME chains, or address-policy drift;
- bounded DNS/network telemetry that records decision metadata without leaking credentials, session material, query parameters, private HTML, or other sensitive content;
- explicit deployment escape hatches only for separately reviewed internal integrations, never inferred from an ordinary public-source authorization.

## Implementation constraint

The lot must not weaken TLS hostname verification merely to pin an IP address. The implementation may use connection-pool/resolver controls, transport hooks, browser network interception, or equivalent mechanisms, but the security property is authoritative: the address actually contacted must remain inside the approved address policy for the requested hostname throughout the network action.

## Required tests

- approved public hostname resolving only to public addresses succeeds;
- hostname initially resolving publicly and later rebinding to loopback/private/link-local is denied before the forbidden connection;
- mixed public and private answers fail closed unless an explicit reviewed policy defines a safe deterministic subset;
- IPv4-mapped IPv6, IPv6 loopback/link-local, integer/alternate IP representations, trailing dots, IDNA, and credential-bearing URLs cannot bypass the policy;
- CNAME chain ending in a forbidden address is denied;
- redirect to a separately allowed hostname still re-runs DNS/address validation;
- retry/reconnect after DNS drift cannot reuse stale authorization as permission for a newly forbidden address;
- browser subresources/XHR/fetch, authenticated navigation, OAuth/token endpoints, screenshots/download helpers, and static HTTP all use the same effective address-safety rule;
- no test disables certificate verification or broadens source host/path authorization to make the suite pass;
- structured telemetry distinguishes policy denial, resolution failure, timeout, and provider failure without storing secrets;
- full architecture, backend, security, browser/runtime, and regression gates pass on one exact final head.

## Exit gate

Lot 30 cannot be marked complete while any product-owned outbound acquisition path can pass hostname/source authorization and then connect to an internal or forbidden address because DNS resolution changed or was interpreted inconsistently. The final proof must include deterministic rebinding fixtures for static HTTP and browser-backed acquisition paths and demonstrate fail-closed behavior without weakening TLS or source-governance controls.
