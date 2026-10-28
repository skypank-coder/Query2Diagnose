import { lazy, Suspense, useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import { Loading } from "./components/ui";

// Pages load on demand so the home page does not pull in charts or KaTeX.
const Demo = lazy(() => import("./pages/Demo"));
const Benchmark = lazy(() => import("./pages/Benchmark"));
const Results = lazy(() => import("./pages/Results"));
const Method = lazy(() => import("./pages/Method"));
const Paper = lazy(() => import("./pages/Paper"));

const NAV = [
  ["/", "Home"], ["/demo", "Live demo"], ["/benchmark", "Benchmark"], ["/results", "Results"], ["/method", "Method"], ["/paper", "Paper"],
] as const;

function ThemeToggle() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem("q2d-theme", dark ? "dark" : "light"); } catch { /* storage may be blocked */ }
  }, [dark]);
  return (
    <button className="btn-ghost px-3" onClick={() => setDark(!dark)} aria-label="Toggle dark mode">
      {dark ? "☀" : "☾"}
    </button>
  );
}

export default function App() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/85 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <NavLink to="/" className="font-serif text-lg font-semibold text-slate-900 dark:text-white">
            Query<span className="text-accent-600 dark:text-accent-400">2</span>Diagnose
          </NavLink>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"}
                className={({ isActive }) => `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-accent-50 font-medium text-accent-700 dark:bg-accent-700/20 dark:text-accent-400" : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"}`}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button className="btn-ghost px-3 md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
          </div>
        </div>
        {open && (
          <nav className="border-t border-slate-200 px-4 py-2 md:hidden dark:border-slate-800">
            {NAV.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"} onClick={() => setOpen(false)} className="block py-2 text-sm">{label}</NavLink>
            ))}
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/benchmark" element={<Benchmark />} />
          <Route path="/results" element={<Results />} />
          <Route path="/method" element={<Method />} />
          <Route path="/paper" element={<Paper />} />
        </Routes>
        </Suspense>
      </main>
      <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-500 dark:border-slate-800">
        Research prototype · School of CSE, RV University, Bengaluru · Code MIT · Troubleshooting text from iFixit (CC BY-NC-SA 3.0) and ENERGY STAR (public domain)
      </footer>
    </div>
  );
}
