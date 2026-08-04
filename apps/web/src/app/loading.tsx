export default function Loading() {
  return (
    <section className="page-stack" aria-busy="true" aria-live="polite">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Analyst workspace</p>
          <h1>Loading opportunities</h1>
          <p>The latest persisted evidence and score calculations are being loaded.</p>
        </div>
      </div>
      <div className="summary-grid skeleton-grid">
        {Array.from({ length: 4 }, (_, index) => (
          <div className="summary-card skeleton" key={index} />
        ))}
      </div>
      <div className="panel skeleton skeleton-panel" />
    </section>
  );
}
