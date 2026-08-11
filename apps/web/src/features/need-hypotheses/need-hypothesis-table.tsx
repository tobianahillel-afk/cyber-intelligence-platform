import Link from "next/link";

import type { NeedHypothesis } from "./types";

interface NeedHypothesisTableProps {
  hypotheses: readonly NeedHypothesis[];
}

function label(value: string): string {
  return value.replaceAll("_", " ");
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function NeedHypothesisTable({ hypotheses }: NeedHypothesisTableProps) {
  return (
    <div className="table-wrapper">
      <table>
        <caption className="sr-only">Evidence-backed cyber need hypotheses</caption>
        <thead>
          <tr>
            <th scope="col">Confidence</th>
            <th scope="col">Organization</th>
            <th scope="col">Need hypothesis</th>
            <th scope="col">Services</th>
            <th scope="col">Urgency</th>
            <th scope="col">Evidence balance</th>
            <th scope="col">Rule</th>
          </tr>
        </thead>
        <tbody>
          {hypotheses.map((hypothesis) => (
            <tr key={hypothesis.id}>
              <td>
                <strong>{percent(hypothesis.confidence)}</strong>
                <span className="cell-secondary">{label(hypothesis.status)}</span>
              </td>
              <td>
                <Link href={`/need-hypotheses/${hypothesis.id}`}>
                  <strong>{hypothesis.organization}</strong>
                </Link>
                <span className="cell-secondary">{hypothesis.organization_id}</span>
              </td>
              <td>
                <span className="badge">{label(hypothesis.hypothesis_class)}</span>
                <span className="cell-secondary">{hypothesis.rationale}</span>
              </td>
              <td>
                {hypothesis.service_families.length > 0
                  ? hypothesis.service_families.map(label).join(", ")
                  : "Research only"}
                <span className="cell-secondary">
                  {hypothesis.applicable_offers.length} offer(s)
                </span>
              </td>
              <td>
                <span className={`badge hypothesis-urgency-${hypothesis.urgency}`}>
                  {label(hypothesis.urgency)}
                </span>
                <span className="cell-secondary">{label(hypothesis.horizon)}</span>
              </td>
              <td>
                <strong>{hypothesis.signal_ids.length} supporting</strong>
                <span className="cell-secondary">
                  {hypothesis.conflicting_signal_ids.length} conflicting ·{" "}
                  {hypothesis.negative_signal_ids.length} negative
                </span>
              </td>
              <td>
                {hypothesis.rule_id}
                <span className="cell-secondary">
                  v{hypothesis.rule_version} · taxonomy {hypothesis.taxonomy_version}
                </span>
                <Link className="text-link" href={`/need-hypotheses/${hypothesis.id}`}>
                  Inspect fusion
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
