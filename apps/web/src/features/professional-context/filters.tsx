import type { ProfessionalPeopleQuery } from "./api";

interface ProfessionalFiltersProps {
  values: ProfessionalPeopleQuery;
}

export function ProfessionalFilters({ values }: ProfessionalFiltersProps) {
  return (
    <form className="professional-filters" method="get">
      <label>
        Search
        <input
          defaultValue={values.query}
          maxLength={200}
          name="q"
          placeholder="name, role, team…"
        />
      </label>
      <label>
        Employment
        <select defaultValue={values.employmentState ?? ""} name="employment_state">
          <option value="">Any state</option>
          <option value="current">Current</option>
          <option value="stale">Stale</option>
          <option value="historical">Historical</option>
          <option value="disputed">Disputed</option>
          <option value="retracted">Retracted</option>
          <option value="unknown">Unknown</option>
        </select>
      </label>
      <label>
        Review
        <select defaultValue={values.reviewState ?? ""} name="review_state">
          <option value="">Any review state</option>
          <option value="unreviewed">Unreviewed</option>
          <option value="review_required">Review required</option>
          <option value="confirmed">Confirmed</option>
          <option value="rejected">Rejected</option>
        </select>
      </label>
      <label>
        Lawful basis
        <select defaultValue={values.lawfulBasis ?? ""} name="lawful_basis">
          <option value="">Any basis</option>
          <option value="legitimate_interests">Legitimate interests</option>
          <option value="consent">Consent</option>
          <option value="contract">Contract</option>
          <option value="legal_obligation">Legal obligation</option>
          <option value="public_task">Public task</option>
          <option value="review_required">Review required</option>
        </select>
      </label>
      <button type="submit">Apply</button>
    </form>
  );
}
