import { notFound } from "next/navigation";

import {
  loadConditionalProvider,
  loadConditionalProviderValue,
} from "@/features/conditional-integrations/api";
import { ConditionalProviderDetailView } from "@/features/conditional-integrations/detail";
import { loadSourcePortfolio } from "@/features/sources/api";

interface ConditionalProviderPageProps {
  params: Promise<{ sourceId: string }>;
}

export default async function ConditionalProviderPage({
  params,
}: ConditionalProviderPageProps) {
  const { sourceId } = await params;
  const portfolio = await loadSourcePortfolio();
  const candidate = portfolio.items.find(
    (source) => source.source_id === sourceId && source.category.startsWith("conditional_"),
  );
  if (!candidate) notFound();

  const [provider, value] = await Promise.all([
    loadConditionalProvider(sourceId),
    loadConditionalProviderValue(sourceId),
  ]);
  return (
    <ConditionalProviderDetailView
      candidate={candidate}
      provider={provider}
      value={value}
    />
  );
}
