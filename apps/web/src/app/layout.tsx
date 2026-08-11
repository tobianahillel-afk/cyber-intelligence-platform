import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/shared/components/app-shell";

import "./globals.css";
import "../features/opportunities/opportunities.css";
import "../features/need-hypotheses/need-hypotheses.css";
import "../features/sources/sources.css";
import "../features/contracts/contracts.css";
import "../features/public-footprint/public-footprint.css";
import "../features/research-plans/research-plans.css";
import "../features/vulnerabilities/vulnerabilities.css";
import "../features/incidents/incidents.css";
import "../features/threat-telemetry/threat-telemetry.css";
import "../features/passive-exposure/passive-exposure.css";
import "../features/vulnerability-applicability/vulnerability-applicability.css";
import "../features/corporate-changes/corporate-changes.css";
import "../features/relationships/relationships.css";
import "../features/corporate-graph/corporate-graph.css";

export const metadata: Metadata = {
  title: "Cyber Intelligence Platform",
  description: "Human-operated cyber revenue intelligence workspace",
};

interface RootLayoutProps {
  children: ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
