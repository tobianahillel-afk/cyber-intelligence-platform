import Link from "next/link";

export default function OpportunityNotFound() {
  return (
    <section className="page-stack">
      <Link className="back-link" href="/">
        ← Back to Opportunity Inbox
      </Link>
      <div className="panel unavailable-state">
        <p className="eyebrow">Not found</p>
        <h1>This opportunity does not exist</h1>
        <p>It may have been deleted, filtered by retention, or the identifier is invalid.</p>
      </div>
    </section>
  );
}
