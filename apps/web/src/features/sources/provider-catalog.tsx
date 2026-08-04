import { ProviderCard } from "./provider-card";
import type { ProviderOnboarding } from "./types";

interface ProviderCatalogProps {
  providers: readonly ProviderOnboarding[];
}

export function ProviderCatalog({ providers }: ProviderCatalogProps) {
  if (providers.length === 0) {
    return (
      <div className="empty-state">
        <h3>No provider matches this view</h3>
        <p>Change the state filter to display the remaining governed sources.</p>
      </div>
    );
  }
  return (
    <div className="provider-grid">
      {providers.map((provider) => (
        <ProviderCard key={provider.source_id} provider={provider} />
      ))}
    </div>
  );
}
