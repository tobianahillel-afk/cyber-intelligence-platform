import { formatTimestamp, readable } from "./passive-asset-table";
import type { PassiveObservation } from "./types";

interface PassiveObservationHistoryProps {
  observations: readonly PassiveObservation[];
}

export function PassiveObservationHistory({
  observations,
}: PassiveObservationHistoryProps) {
  return (
    <section className="panel" aria-labelledby="passive-history-title">
      <div className="panel-heading">
        <div>
          <h2 id="passive-history-title">Immutable observation history</h2>
          <p>
            Corrections, retractions, reassignment risks and technology evidence
            remain visible without becoming vulnerability applicability.
          </p>
        </div>
      </div>
      <div className="passive-observation-list">
        {observations.map((observation) => (
          <ObservationCard key={observation.id} observation={observation} />
        ))}
      </div>
    </section>
  );
}

interface ObservationCardProps {
  observation: PassiveObservation;
}

function ObservationCard({ observation }: ObservationCardProps) {
  return (
    <article className="passive-observation">
      <header>
        <div>
          <ObservationBadges observation={observation} />
          <h3>{observation.source_id}</h3>
        </div>
        <time>{formatTimestamp(observation.modified_at)}</time>
      </header>
      <dl className="passive-observation-facts">
        <Fact label="Observed" value={formatTimestamp(observation.observed_at)} />
        <Fact label="Published" value={formatTimestamp(observation.published_at)} />
        <Fact label="Expires" value={formatTimestamp(observation.expires_at)} />
        <Fact label="Confidence" value={percentage(observation.confidence)} />
        <Fact
          label="Link method"
          value={readable(observation.organization_link_method)}
        />
        <Fact
          label="Link confidence"
          value={percentage(observation.organization_link_confidence)}
        />
        <Fact label="Service" value={serviceLabel(observation)} />
        <Fact
          label="Supersedes"
          value={observation.supersedes_record_key ?? "No prior source revision"}
        />
      </dl>
      <TechnologyEvidence observation={observation} />
      {observation.attribution_risks.length > 0 ? (
        <div className="passive-badges">
          {observation.attribution_risks.map((risk) => (
            <span key={risk}>{readable(risk)}</span>
          ))}
        </div>
      ) : null}
      {observation.organization_link_reasons.length > 0 ? (
        <p>{observation.organization_link_reasons.join(" · ")}</p>
      ) : null}
      <a href={observation.source_url} rel="noreferrer" target="_blank">
        Open published source
      </a>
    </article>
  );
}

function ObservationBadges({ observation }: ObservationCardProps) {
  return (
    <div className="passive-badges">
      <span>{readable(observation.state)}</span>
      <span>{readable(observation.observation_kind)}</span>
      <span>{readable(observation.organization_link_status)}</span>
      {!observation.active ? <span>Inactive</span> : null}
      {observation.historical_only ? <span>Historical only</span> : null}
    </div>
  );
}

function TechnologyEvidence({ observation }: ObservationCardProps) {
  const technology = observation.technology;
  if (!technology) {
    return null;
  }
  return (
    <div className="passive-technology">
      <strong>{readable(technology.evidence_level)}</strong>
      <span>
        {technology.product_name ?? "Unknown product"}
        {technology.product_version ? ` ${technology.product_version}` : ""}
      </span>
      {technology.component_name ? <span>{technology.component_name}</span> : null}
      <small>Observed metadata only; vulnerability applicability not assessed.</small>
    </div>
  );
}

interface FactProps {
  label: string;
  value: string;
}

function Fact({ label, value }: FactProps) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function percentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function serviceLabel(observation: PassiveObservation): string {
  if (observation.port === null || !observation.protocol) {
    return "Not applicable";
  }
  return `${observation.port}/${observation.protocol}`;
}
