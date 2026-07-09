import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/products", label: "Products" },
  { to: "/review-queue", label: "Review Queue" },
  { to: "/calendar", label: "Calendar" },
  { to: "/assets", label: "Assets" },
  { to: "/analytics", label: "Analytics" },
  { to: "/settings", label: "Settings" },
];

export function DashboardLayout() {
  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-mark">PV</span>
          <div>
            <strong>PelleVista</strong>
            <span>Content Autopilot</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Main navigation">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav-link active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="page-shell">
        <Outlet />
      </main>
    </div>
  );
}

