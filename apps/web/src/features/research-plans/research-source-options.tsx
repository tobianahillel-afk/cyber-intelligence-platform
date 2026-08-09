import type { ResearchSourceOptions as ResearchSourceOptionsData } from "./source-types";

interface ResearchSourceOptionsProps {
  options: ResearchSourceOptionsData;
}

export function ResearchSourceOptions({ options }: ResearchSourceOptionsProps) {
  return (
    <section className="panel" aria-labelledby="research-source-options-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Persisted source selection</p>
          <h2 id="research-source-options-title">Recommended governed sources</h2>
          <p>
            Ranked for {label(options.purpose)} / {label(options.data_category)} from persisted
            value, freshness, cost, quota, authorization and risk. No source is executed here.
          </p>
        </div>
      </div>

      {options.items.length > 0 ? (
        <div className="table-scroll">
          <table className="research-source-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Source / tool</th>
                <th>Mode</th>
                <th>Value</th>
                <th>Freshness</th>
                <th>Cost / quota</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {options.items.map((option) => (
                <tr key={`${option.mode}:${option.source_id}:${option.tool_id}`}>
                  <td>#{option.rank}</td>
                  <td>
                    <strong>{option.source_id}</strong>
                    <small>{option.tool_id}</small>
                  </td>
                  <td>
                    {label(option.mode)}
                    <small>{availability(option)}</small>
                  </td>
                  <td>{percent(option.value_score)}</td>
                  <td>{percent(option.freshness_score)}</td>
                  <td>
                    {option.estimated_cost.toFixed(2)}
                    <small>
                      quota {option.quota_remaining === null ? "n/a" : option.quota_remaining}
                    </small>
                  </td>
                  <td>{label(option.risk_level)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <h3>No governed source option</h3>
          <p>
            No persisted or governed source is currently eligible for this research context.
          </p>
        </div>
      )}
    </section>
  );
}

function availability(option: ResearchSourceOptionsData["items"][number]): string {
  if (option.mode === "persisted_search") return "local evidence first";
  if (option.mode === "manual_link") return "explicit analyst action";
  if (option.authorized && option.executable) return "runtime candidate";
  return "blocked";
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function label(value: string): string {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}
