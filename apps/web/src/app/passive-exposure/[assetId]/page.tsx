import { notFound } from "next/navigation";

import {
  loadPassiveAssetDetail,
  PassiveExposureApiError,
} from "@/features/passive-exposure/api";
import { PassiveAssetDetailView } from "@/features/passive-exposure/passive-asset-detail";

interface PassiveAssetDetailPageProps {
  params: Promise<{ assetId: string }>;
}

export default async function PassiveAssetDetailPage({
  params,
}: PassiveAssetDetailPageProps) {
  const { assetId } = await params;
  const detail = await loadDetail(assetId);

  return <PassiveAssetDetailView detail={detail} />;
}

async function loadDetail(assetId: string) {
  try {
    return await loadPassiveAssetDetail(assetId);
  } catch (error) {
    if (error instanceof PassiveExposureApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }
}
