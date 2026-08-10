# Priority B — Public RDAP Authorization

## Scope

`iana-rdap-public` is a bounded public-registration capability for explicitly configured domain, IPv4, IPv6, and ASN targets. It is not a WHOIS contact harvester and it does not request nonpublic registration data.

The adapter uses the IANA RDAP bootstrap registries defined by RFC 9224:

- `https://data.iana.org/rdap/dns.json`
- `https://data.iana.org/rdap/ipv4.json`
- `https://data.iana.org/rdap/ipv6.json`
- `https://data.iana.org/rdap/asn.json`

The policy-authorized first hop is restricted to `data.iana.org/rdap/`.

## Authoritative second-hop rule

The authoritative RDAP endpoint is not supplied by a user, search result, redirect, or provider payload outside the IANA bootstrap document.

For each target the adapter:

1. downloads the matching IANA bootstrap registry over HTTPS;
2. selects the most specific matching service for the domain suffix, IP prefix, or ASN range;
3. accepts only an HTTPS base URL from that matching service;
4. derives one exact resource URL under the same scheme and host;
5. performs no redirect following;
6. revalidates that the returned RDAP object covers the requested target.

A bootstrap entry without an HTTPS endpoint fails closed. A derived URL that changes host, embeds credentials, or escapes the selected authoritative endpoint fails closed.

## Public fields only

The persisted provider model contains only a minimal registration/allocation subset needed for passive evidence:

- object class;
- public handle/name/domain identifier where applicable;
- public IP allocation range or ASN range where applicable;
- bounded status values and public event timestamps.

RDAP `entities`, vCards, email addresses, telephone numbers, postal/contact records, registrant/administrative/technical contacts, and other person-oriented fields are intentionally absent from the materialized schema. Unknown provider fields are ignored before `RawObservation` is constructed; the raw HTTP response body itself is not stored.

## Explicit exclusions

The capability must not:

- use ICANN RDRS or another nonpublic-registration access path;
- authenticate to retrieve nonpublic registration data;
- harvest registrant or contact PII;
- enumerate targets not explicitly present in the deployment target registry;
- use RDAP registration/allocation as proof of current operational ownership;
- infer deployment, vulnerability applicability, exposure, compromise, need, opportunity, or outreach authorization;
- actively probe, connect to, scan, or exploit the returned resource.

## Target and schedule activation

`policies/rdap_targets.yml` is checked in empty. The RDAP schedule is checked in disabled. Deployment activation requires explicit organization-bound targets and an operational decision to enable the schedule.

`live_tested` remains false until a separately authorized controlled provider validation is recorded on an exact release candidate.

## References reviewed

- RFC 9224, *Finding the Authoritative Registration Data (RDAP) Service*: https://www.rfc-editor.org/rfc/rfc9224
- IANA RDAP bootstrap registries: https://data.iana.org/rdap/
- ICANN RDAP resources: https://www.icann.org/en/contracted-parties/registry-operators/resources/registration-data-access-protocol
- ICANN Registration Data Request Service information: https://www.icann.org/rdrs-en
