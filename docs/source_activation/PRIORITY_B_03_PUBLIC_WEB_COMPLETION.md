# Priority B-3 — Public Feeds, security.txt and Bounded Documents

## Objective

Complete the existing Lot 12 governed public-web capability without creating a second crawler or a general-purpose browsing runtime.

Priority B-3 adds three bounded discovery and parsing paths to the existing target-driven public-web collector:

- explicitly configured RSS 2.0 and Atom feeds;
- optional RFC 9116 `/.well-known/security.txt` discovery;
- bounded public PDF text extraction for already approved in-scope document URLs.

All traffic remains subject to Source Governance, explicit organization targets, robots rules, host/path allowlists, page and byte budgets, redirect limits, MIME validation, retention and the shared collection scheduler/worker.

## Runtime path

```text
explicit approved organization target
  -> robots.txt
  -> configured sitemap and/or configured feed
  -> bounded same-origin discovery
  -> optional exact /.well-known/security.txt
  -> approved page/document fetch
  -> bounded parser
  -> sanitized PublicResource/PublicResourceVersion
  -> optional target-content claims only where content semantics support them
  -> existing Lot 12 persistence
```

No page view triggers collection. No unrestricted recursive crawler is introduced.

## Feed boundary

RSS and Atom feeds are discovery lineage. A feed entry can identify a public page or document to retrieve through the same approved target path. The feed and its linked target are not independent corroboration merely because both exist.

Feed parsing must:

- reject DTD/entity declarations and malformed XML;
- enforce byte and entry-count bounds;
- accept only configured feed URLs;
- canonicalize and deduplicate links;
- reject links outside the approved target origin/scope before retrieval;
- never retain raw feed bodies beyond bounded processing.

## security.txt boundary

`security.txt` is an optional exact-path capability at `/.well-known/security.txt` for an explicitly enabled public-web target.

It is treated as a public security-disclosure/contact route, not as evidence that an organization is vulnerable, breached, exposed, or currently buying cybersecurity services. It must not create an automatic CommercialSignal, NeedHypothesis, score, opportunity or outreach action.

The parser accepts bounded UTF-8 `text/plain`, requires at least one valid `Contact` field, validates any `Canonical` URL, and ignores unsupported fields rather than interpreting them as commercial evidence.

## PDF/document boundary

PDF extraction applies only to already approved public URLs returned by the bounded target discovery paths. Documents are never executed.

The parser must:

- require an allowed PDF MIME type and bounded response size before parsing;
- reject malformed or encrypted documents it cannot safely process;
- enforce page-count and extracted-text bounds;
- extract text only, ignoring scripts, embedded files, annotations and active content;
- keep only hashes, bounded excerpts/claims and provenance in canonical persistence rather than storing the raw document body.

## Non-goals

Priority B-3 does not add:

- arbitrary URL fetching;
- recursive site-wide crawling;
- authentication, private portals, CAPTCHA/MFA/paywall bypass;
- browser automation;
- downloads initiated by analyst page views;
- archive execution or embedded-object extraction;
- credential/private-message/victim-file collection;
- automatic opportunity or outreach generation.

## Completion gate

B-3 is complete only when:

- the existing Lot 12 public-web target schema supports explicit feed URLs and optional security.txt discovery;
- the same PublicWebClient/collector enforces all host/path/robots/redirect/page/byte controls for the new paths;
- RSS/Atom and security.txt parsers are deterministic and fail closed on malformed or unsafe input;
- PDF extraction is bounded and does not persist raw document bodies;
- feed-linked pages and documents reuse the existing PublicResource/PublicResourceVersion model;
- feed lineage does not count as independent corroboration of its linked content;
- security.txt creates no vulnerability, exposure or commercial-need inference;
- deterministic parser, target-registry, client, collector and persistence tests pass;
- Source Activation truth and the Source Coverage Matrix describe the delivered capability accurately;
- one exact final SHA passes the complete backend and frontend CI;
- `live_tested` remains false until separately authorized controlled validation is evidenced.
