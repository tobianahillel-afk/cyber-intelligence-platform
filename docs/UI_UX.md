# Analyst UI and UX

## UX objective

The interface is designed for one primary job: help a human analyst move from a new signal to a justified commercial action without losing provenance, freshness, uncertainty, or context.

The interface must make it easy to answer:

- What changed?
- Which organizations are affected?
- Why is this an opportunity?
- How recent and reliable is the information?
- Who is the relevant professional contact?
- What should I review or do next?

## Design principles

- Information-dense without becoming visually noisy.
- Every score is explainable.
- Every important fact has a source and timestamp.
- Claims, confirmations, observations, and inferences use distinct visual labels.
- Freshness is visible everywhere.
- Sensitive professional-contact data is redacted unless the user has permission.
- Filters and selected tabs survive navigation and page refresh.
- Long-running jobs stream partial progress.
- No full-page refresh for live updates.
- Tables, graphs, timelines, and relationship views support deep linking.

## Application shell

### Left navigation

- Command Center
- Opportunities
- Organizations
- Research
- Alerts
- Contacts
- Offers
- Sources
- Tasks
- Settings

The navigation can collapse to icons while preserving tooltips and keyboard access.

### Top bar

- universal organization, domain, person-role, CVE, and event search;
- quick-create research job;
- active-job indicator;
- source-health indicator;
- notification center;
- current workspace and saved-view selector;
- user and team menu.

### Global context bar

Optional context that can persist across pages:

- date range;
- countries;
- sectors;
- company-size band;
- offer catalog subset;
- confidence threshold;
- freshness threshold.

## Command Center

The Command Center is a decision dashboard, not a generic analytics page.

### Top summary

- urgent opportunities;
- new opportunities in the last 24 hours;
- high-confidence opportunities;
- opportunities waiting for review;
- contracts entering a renewal window;
- sources currently unhealthy or stale.

### Priority stream

A chronological, deduplicated stream of meaningful changes:

- opportunity created;
- score increased or decreased;
- official incident confirmation added;
- relevant KEV match detected;
- tender published;
- renewal window opened;
- decision-maker role identified;
- source became stale;
- analyst task became overdue.

Each stream item has an inline action: open, assign, dismiss, snooze, or request enrichment.

### Coverage widgets

- source freshness by category;
- geographic coverage;
- sectors with increasing signals;
- evidence awaiting review;
- failed collection jobs.

## Opportunity Inbox

### Default columns

- priority;
- organization;
- opportunity family;
- recommended offer;
- score;
- confidence;
- strongest trigger;
- age of newest evidence;
- relevant roles available;
- owner;
- state;
- next action.

### Filters

- opportunity family;
- score and confidence;
- evidence freshness;
- country and sector;
- company size;
- recommended offer;
- assigned analyst;
- lifecycle state;
- source category;
- warnings;
- presence of a professional contact;
- renewal-window date.

### Saved views

Examples:

- Incident response now
- SIEM prospects this quarter
- Public tenders closing soon
- High-confidence KEV matches
- New French mid-market organizations
- Needs contact enrichment
- Monitoring: unconfirmed ransomware claims

### Opportunity card or row expansion

- concise explanation;
- component score breakdown;
- strongest evidence;
- contradictions and warnings;
- relevant people and roles;
- recommended offer;
- recommended timing;
- analyst actions.

## Opportunity detail

### Header

- organization name and identifiers;
- state and assignment;
- total score and confidence;
- opportunity family;
- recommended offer;
- freshness;
- last meaningful change;
- warnings.

### Sections

1. Why this opportunity exists
2. Evidence and source timeline
3. Score explanation
4. Need hypothesis
5. Recommended offer and timing
6. Buying committee
7. Organization context
8. Related opportunities
9. Tasks and notes
10. Lifecycle history

### Score explanation

Show the contribution of every component:

```text
Confirmed incident          +28
Recent public tender        +22
Relevant security hiring    +12
CISO identified              +8
Old technology observation   -7
Single weak source           -9
```

The analyst can exclude a component and preview the recalculated score before saving the decision.

## Organization Workspace

### Persistent organization header

- canonical and legal names;
- logo or initials;
- country and sector;
- employee and revenue ranges;
- group or parent;
- primary domains;
- active opportunities;
- current risk and data-quality warnings;
- latest collection time.

### Overview tab

- executive summary;
- detected needs;
- active and historical opportunities;
- key events;
- technology summary;
- contact-role coverage;
- open tasks;
- data freshness by category.

### Timeline tab

A merged timeline containing:

- incidents and claims;
- technology observations;
- vulnerability relevance changes;
- tenders and awards;
- job postings;
- funding, acquisition, or leadership changes;
- contract estimates;
- analyst notes;
- outreach events.

The user can filter by event type, confidence, source, and evidence status.

### External footprint tab

- domains and subdomains;
- IP and ASN relations;
- certificates;
- hosting and cloud providers;
- discovered services from authorized passive sources;
- first and last seen;
- confidence and source coverage.

Provide table and relationship-graph modes. The graph never replaces the table.

### Technologies tab

- product and vendor;
- version when known;
- observation method;
- evidence count;
- first and last seen;
- expiry;
- confidence;
- relevant vulnerabilities;
- related job, support, documentation, or contract signals.

### Vulnerability relevance tab

- CVE;
- product match;
- match type;
- CVSS;
- EPSS;
- KEV status;
- affected-version confidence;
- remediation state when publicly known;
- evidence and analyst decision.

The UI must say `potential relevance` rather than `confirmed vulnerability` unless an authorized validation record exists.

### Incidents and claims tab

- event title;
- claim status;
- claimant;
- official confirmation;
- dates;
- impact summary;
- contradictory evidence;
- latest update;
- confidence.

### Contracts and tenders tab

- buyer entity;
- contract or tender title;
- scope;
- publication and closing dates;
- award date;
- incumbent supplier;
- duration and options;
- estimated renewal window;
- confidence and derivation.

### Organization chart tab

Views:

- hierarchy;
- buying committee;
- role coverage;
- source list.

Relationships must distinguish public fact from inferred reporting line.

### Professional contacts tab

Columns:

- name;
- role;
- buying-committee category;
- professional channel;
- relevance;
- source;
- last verified;
- confidence;
- notice and objection state;
- retention deadline.

### Evidence tab

- source;
- source type;
- evidence type;
- claim or observation supported;
- publication and collection dates;
- confidence;
- review state;
- permitted preview;
- retention status.

## Research Workspace

### Research job creation

Inputs:

- target organization, domain, technology, person-role, CVE, or keyword;
- research objective;
- source groups;
- maximum depth and time budget;
- allowed data categories;
- whether browser research is required;
- desired freshness;
- analyst note.

### Job progress

Show stages rather than a generic spinner:

```text
Policy check
Source selection
Queued
Collecting
Parsing
Normalizing
Resolving entities
Generating evidence
Recalculating opportunities
Completed with warnings
```

Display partial results as they become available.

### Result review

Group results into:

- accepted evidence;
- duplicate;
- irrelevant;
- sensitive metadata requiring review;
- failed or inaccessible;
- contradictory.

## Alerts

Alerts are user-facing notifications about meaningful changes. They are not raw events.

Alert types:

- urgent opportunity;
- official incident confirmation;
- high-confidence exposure signal;
- tender closing soon;
- renewal window opened;
- opportunity score changed materially;
- professional role changed;
- source or coverage failure;
- data-retention action required;
- analyst task overdue.

Users configure channels, thresholds, quiet periods, digest frequency, and deduplication windows.

## Sources UI

### Source list

- source name and category;
- status;
- collection method;
- authorization state;
- latest success;
- freshness lag;
- error rate;
- records processed;
- quota usage;
- next run;
- owner.

### Source detail

- manifest;
- legal and authorization records;
- permitted categories;
- prohibited categories;
- schedules;
- rate limits;
- retention;
- health history;
- recent jobs;
- parser or schema failures;
- dead-letter queue;
- pause and resume actions;
- kill switch.

## Offers UI

Each offer has:

- name and category;
- description;
- target company profiles;
- target professional roles;
- qualifying signal rules;
- disqualifying conditions;
- minimum confidence;
- required evidence;
- recommended outreach window;
- permitted messaging claims;
- price or package metadata when configured.

Analysts can see which active opportunities match an offer and why.

## Tasks and analyst collaboration

Task types:

- review evidence;
- verify entity match;
- confirm contact role;
- review sensitive search result;
- qualify opportunity;
- prepare outreach;
- follow up;
- review stale information;
- approve deletion or suppression.

Tasks support assignment, due date, comments, status, priority, linked organization, linked opportunity, and audit history.

## Responsive behavior

The primary target is desktop. Tablet supports review and triage. Mobile supports alerts, simple review, assignment, snooze, and notes, but not complex graph investigation.

## Accessibility

- full keyboard navigation;
- visible focus states;
- semantic headings and tables;
- screen-reader labels;
- no information conveyed by color alone;
- sufficient contrast;
- reduced-motion support;
- accessible chart summaries.

## Performance expectations

- initial application shell interactive within 2.5 seconds on a normal business connection;
- opportunity list filter response under 500 ms for indexed queries;
- organization overview under 1 second after cache warm-up;
- live job updates without full-page refresh;
- virtualized rendering for long tables and timelines;
- progressive loading for graphs and evidence previews.

## Visual language

Use a sober analyst interface:

- compact spacing with optional comfortable density;
- neutral background;
- clear severity and confidence badges;
- monospace only for technical identifiers;
- consistent evidence and provenance icons;
- charts used for comparison and trends, not decoration;
- explicit empty, loading, stale, partial, and error states.
