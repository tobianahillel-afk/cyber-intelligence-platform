import { overrideScoreComponentAction } from "./actions";
import type { OpportunityScoreComponent } from "./types";

interface ScoreComponentsProps {
  opportunityId: string;
  components: readonly OpportunityScoreComponent[];
}

export function ScoreComponents({ opportunityId, components }: ScoreComponentsProps) {
  return (
    <section className="panel detail-section" aria-labelledby="score-title">
      <div className="panel-heading">
        <div>
          <h2 id="score-title">Explainable score</h2>
          <p>Each contribution links the prioritization decision to evidence and a versioned rule.</p>
        </div>
      </div>
      <div className="component-list">
        {components.map((component) => {
          const action = overrideScoreComponentAction.bind(
            null,
            opportunityId,
            component.id,
          );
          return (
            <article className="component-card" key={component.id}>
              <div className="component-heading">
                <div>
                  <strong>{formatLabel(component.rule_id)}</strong>
                  <span className="cell-secondary">{component.reason}</span>
                </div>
                <div className="component-score">
                  <strong>{formatSigned(component.contribution)}</strong>
                  <span>{component.kind}</span>
                </div>
              </div>
              <div className="component-meta">
                <span>Value {component.value.toFixed(3)}</span>
                <span>Weight {component.weight.toFixed(1)}</span>
                <span>{component.evidence_ids.length} evidence link(s)</span>
                {component.analyst_overridden ? (
                  <span className="warning">Analyst override active</span>
                ) : null}
              </div>
              <form action={action} className="component-form">
                <label>
                  Analyst
                  <input name="actor" required placeholder="name@example.com" />
                </label>
                <label>
                  Value
                  <input
                    defaultValue={component.value}
                    max="1"
                    min="0"
                    name="value"
                    step="0.01"
                    type="number"
                  />
                </label>
                <label>
                  Weight
                  <input
                    defaultValue={component.weight}
                    max="100"
                    min="0"
                    name="weight"
                    step="0.5"
                    type="number"
                  />
                </label>
                <label className="component-reason">
                  Reason
                  <input defaultValue={component.reason} name="reason" />
                </label>
                <button type="submit">Apply override</button>
              </form>
              {component.original_value !== null ? (
                <p className="baseline-note">
                  Latest automatic baseline: value {component.original_value.toFixed(3)}, weight{" "}
                  {component.original_weight?.toFixed(1)}.
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function formatLabel(value: string): string {
  return value.replaceAll("-", " ").replaceAll("_", " ");
}

function formatSigned(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}`;
}
