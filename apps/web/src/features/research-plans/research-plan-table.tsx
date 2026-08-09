import Link from "next/link";

import type { ResearchPlan } from "./types";

interface ResearchPlanTableProps {
  plans: readonly ResearchPlan[];
}

export function ResearchPlanTable({ plans }: ResearchPlanTableProps) {
  return (
    <div className="table-scroll">
      <table className="research-plan-table">
        <thead>
          <tr>
            <th>Research question</th>
            <th>State</th>
            <th>Purpose</th>
            <th>Budget</th>
            <th>Scope</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {plans.map((plan) => (
            <tr key={plan.id}>
              <td>
                <Link className="research-plan-link" href={`/research/plans/${plan.id}`}>
                  {plan.question}
                </Link>
                <small>{plan.data_category.replaceAll("_", " ")}</small>
              </td>
              <td>
                <span className={`research-state research-state-${plan.state}`}>
                  {plan.state.replaceAll("_", " ")}
                </span>
              </td>
              <td>{plan.purpose.replaceAll("-", " ")}</td>
              <td>
                <strong>{plan.max_steps}</strong> steps
                <small>
                  {plan.max_automated_steps} automated · {formatCost(plan.max_total_cost)} cap
                </small>
              </td>
              <td>
                {plan.allowed_source_ids.length} source(s)
                <small>{plan.allowed_tool_ids.length} tool(s)</small>
              </td>
              <td>{formatDate(plan.updated_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCost(value: number): string {
  return value === 0 ? "no paid spend" : value.toFixed(2);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
