"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { label: "Command Center", href: null },
  { label: "Opportunities", href: "/" },
  { label: "Contracts", href: "/contracts" },
  { label: "Organizations", href: null },
  { label: "Research", href: "/research" },
  { label: "Vulnerabilities", href: "/vulnerabilities" },
  { label: "Incidents", href: "/incidents" },
  { label: "Threat Intel", href: "/threat-intelligence" },
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
                className={
                  isActive(pathname, item.href)
                    ? "nav-active"
                    : undefined
                }
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
