import type { ReactNode } from "react";

const navigation = [
  "Command Center",
  "Opportunities",
  "Organizations",
  "Research",
  "Alerts",
  "Contacts",
  "Offers",
  "Sources",
  "Tasks",
  "Settings",
] as const;

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">CIP</div>
        <nav>
          <ul>
            {navigation.map((item) => (
              <li key={item}>
                <span className={item === "Opportunities" ? "nav-active" : undefined}>
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <label className="global-search">
            <span className="sr-only">Search the intelligence workspace</span>
            <input
              type="search"
              placeholder="Search organization, domain, CVE or professional role"
              disabled
            />
          </label>
          <div className="topbar-status" aria-label="Application status">
            <span>Sources: foundation mode</span>
            <span>Jobs: 0</span>
          </div>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
