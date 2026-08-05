import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/shared/components/app-shell";

import "./globals.css";
import "../features/opportunities/opportunities.css";
import "../features/sources/sources.css";
import "../features/contracts/contracts.css";

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
