"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { label: "Command Center", href: null },
  { label: "Opportunities", href: "/" },
  { label: "Contracts", href: "/contracts" },
  { label: "Relationships", href: "/relationships" },
  { label: "Corporate Graph", href: "/graph" },
  { label: "Organizations", href: null },
  { label: "Research", href: "/research" },
  { label: "Vulnerabilities", href: "/vulnerabilities" },
  { label: "Applicability", href: "/vulnerability-applicability" },
  { label: "Incidents", href: "/incidents" },
  { label: "Corporate Changes", href: "/corporate-changes" },
  { label: "Threat Intel", href: "/threat-intelligence" },
  { label: "Passive Exposure", href: "/passive-exposure" },
  { label: "Alerts", href: null },
  { label: "Contacts", href: null },
  { label: "Offers", href: null },
  { label: "Sources", href: "/sources" },
  { label: "Tasks", href: null },
  { label: "Settings", href: null },
] as const;

export function PrimaryNavigation() {
  const pathname = usePathname();
  return (
    <nav>
      <ul>
        {navigation.map((item) => (
          <li key={item.label}>
            {item.href ? (
              <Link
                className={isActive(pathname, item.href) ? "nav-active" : undefined}
                href={item.href}
              >
                {item.label}
              </Link>
            ) : (
              <span aria-disabled="true">{item.label}</span>
            )}
          </li>
        ))}
      </ul>
    </nav>
  );
}

function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
