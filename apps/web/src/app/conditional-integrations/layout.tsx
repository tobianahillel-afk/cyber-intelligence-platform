import type { ReactNode } from "react";

import "../../features/conditional-integrations/conditional-integrations.css";

export const dynamic = "force-dynamic";

export default function ConditionalIntegrationsLayout({ children }: { children: ReactNode }) {
  return children;
}
