import type { OpportunityReview } from "./types";

interface ReviewHistoryProps {
  reviews: readonly OpportunityReview[];
}

export function ReviewHistory({ reviews }: ReviewHistoryProps) {
  return (
    <section className="panel detail-section" aria-labelledby="history-title">
      <div className="panel-heading">
        <div>
          <h2 id="history-title">Review history</h2>
          <p>State changes and score overrides are retained as an analyst audit trail.</p>
        </div>
      </div>
      {reviews.length > 0 ? (
        <ol className="history-list">
          {reviews.map((review) => (
            <li key={review.id}>
              <div>
                <strong>{formatLabel(review.action)}</strong>
                <span className="cell-secondary">
                  {formatLabel(review.previous_state)} → {formatLabel(review.new_state)}
                </span>
              </div>
              <div>
                <span>{review.actor}</span>
                <span className="cell-secondary">{formatDate(review.occurred_at)}</span>
              </div>
              {review.note ? <p>{review.note}</p> : null}
              {review.snoozed_until ? (
                <p className="warning">Snoozed until {formatDate(review.snoozed_until)}</p>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <div className="empty-state compact-empty">
          <p>No analyst decision has been recorded yet.</p>
        </div>
      )}
    </section>
  );
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
