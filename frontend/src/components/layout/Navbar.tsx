import { NavLink } from "react-router-dom";
import { ShieldCheck } from "lucide-react";

const navItems = [
  { label: "Home", to: "/" },
  { label: "Analyze", to: "/analyze" },
  { label: "Dashboard", to: "/dashboard" },
  { label: "History", to: "/history" },
  { label: "About", to: "/about" },
];

function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#071114]/90 backdrop-blur">
      <nav className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8" aria-label="Primary navigation">
        <NavLink className="flex items-center gap-3 text-sm font-semibold text-white" to="/">
          <span className="grid h-9 w-9 place-items-center rounded-lg border border-white/15 bg-white/10">
            <ShieldCheck className="h-5 w-5 text-teal-300" />
          </span>
          Network Security
        </NavLink>
        <div className="flex flex-wrap gap-2 text-sm text-slate-300">
          {navItems.map((item) => (
            <NavLink
              className={({ isActive }) =>
                `rounded-md px-3 py-2 transition ${
                  isActive ? "bg-white/10 text-white" : "hover:bg-white/10 hover:text-white"
                }`
              }
              end={item.to === "/"}
              key={item.to}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </header>
  );
}

export { Navbar };
