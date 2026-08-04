import { reviewOpportunityAction } from "./actions";
import type { OpportunityState } from "./types";

interface ReviewPanelProps {
  opportunityId: string;
  state: OpportunityState;
}

export function ReviewPanel({ opportunityId, state }: ReviewPanelProps) {
  const action = reviewOpportunityAction.bind(null, opportunityId);
  return (
    <section className="panel detail-section" aria-labelledby="review-title">
      <div className="panel-heading">
        <div>
          <h2 id="review-title">Analyst review</h2>
          <p>Every transition is persisted with the actor, reason and timestamp.</p>
        </div>
        <span className="badge">{formatLabel(state)}</span>
      </div>
      <div className="review-grid">
        <form action={action} className="action-form">
          <input name="action" type="hidden" value="qualify" />
          <ActorField />
          <label>
            Review note
            <textarea name="note" placeholder="Evidence checked and relevant." />
          </label>
          <button type="submit">Qualify</button>
        </form>

        <form action={action} className="action-form">
          <input name="action" type="hidden" value="request_enrichment" />
          <ActorField />
          <label>
            Missing information
            <textarea name="note" placeholder="Request another source or role lookup." />
          </label>
          <button type="submit">Request enrichment</button>
        </form>

        <form action={action} className="action-form">
          <input name="action" type="hidden" value="snooze" />
          <ActorField />
          <label>
            Resume at
            <input name="snoozed_until" required type="datetime-local" />
          </label>
          <label>
            Note
            <textarea name="note" placeholder="Wait for the tender deadline or more evidence." />
          </label>
          <button type="submit">Snooze</button>
        </form>

        <form action={action} className="action-form action-form-danger">
          <input name="action" type="hidden" value="reject" />
          <ActorField />
          <label>
            Rejection reason
            <textarea name="note" required placeholder="Explain why this is not an opportunity." />
          </label>
          <button type="submit">Reject</button>
        </form>

        {state !== "needs_review" ? (
          <form action={action} className="action-form action-form-compact">
            <input name="action" type="hidden" value="reopen" />
            <ActorField />
            <button type="submit">Reopen for review</button>
          </form>
        ) : null}
      </div>
    </section>
  );
}

function ActorField() {
  return (
    <label>
      Analyst
      <input name="actor" required placeholder="name@example.com" />
    </label>
  );
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}
