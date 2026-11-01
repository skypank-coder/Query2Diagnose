import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import Home from "./pages/Home";
import { Loading } from "./components/ui";

// Pages load on demand so the home page does not pull in charts or KaTeX.
const Demo = lazy(() => import("./pages/Demo"));
const Benchmark = lazy(() => import("./pages/Benchmark"));
const Results = lazy(() => import("./pages/Results"));
const Method = lazy(() => import("./pages/Method"));

const NAV = [
  ["/", "Home"], ["/demo", "Live demo"], ["/results", "Results"], ["/benchmark", "Benchmark"], ["/method", "How it works"],
] as const;
const GITHUB = "https://github.com/skypank-coder/Query2Diagnose";

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

function Logo() {
  return (
    <NavLink to="/" className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent-400 to-accent-700 font-serif text-sm font-bold text-white shadow-sm">Q2</span>
      <span className="font-serif text-lg font-semibold text-slate-900 dark:text-white">
        Query<span className="text-accent-600 dark:text-accent-400">2</span>Diagnose
      </span>
    </NavLink>
  );
}

function Page({ children }: { children: ReactNode }) {
  return <div className="container-page py-10">{children}</div>;
}

export default function App() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); setOpen(false); }, [pathname]);
  return (
    <div className="flex min-h-screen flex-col overflow-x-clip">
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/80 backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80">
        <div className="container-page flex items-center justify-between py-3">
          <Logo />
          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"}
                className={({ isActive }) => `rounded-md px-3 py-1.5 text-sm transition ${isActive ? "bg-accent-50 font-medium text-accent-700 dark:bg-accent-700/20 dark:text-accent-300" : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"}`}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <a href={GITHUB} target="_blank" rel="noreferrer" className="btn-ghost hidden px-3 sm:inline-flex">GitHub</a>
            <ThemeToggle />
            <button className="btn-ghost px-3 md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">☰</button>
          </div>
        </div>
        {open && (
          <nav className="border-t border-slate-200 px-4 py-2 md:hidden dark:border-slate-800">
            {NAV.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"} className="block py-2 text-sm">{label}</NavLink>
            ))}
          </nav>
        )}
      </header>
      <main className="flex-1">
        <Suspense fallback={<Page><Loading /></Page>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/demo" element={<Page><Demo /></Page>} />
            <Route path="/results" element={<Page><Results /></Page>} />
            <Route path="/benchmark" element={<Page><Benchmark /></Page>} />
            <Route path="/method" element={<Page><Method /></Page>} />
          </Routes>
        </Suspense>
      </main>
      <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
        <div className="container-page grid gap-6 py-8 text-xs text-slate-500 md:grid-cols-[1.4fr_1fr]">
          <div>
            <div className="font-serif text-sm font-semibold text-slate-800 dark:text-slate-100">Query2Diagnose</div>
            <p className="mt-1">Saatwik Kumar Yadav (team lead) · Rachana Bhaskar Gowda · Priyanshu Kumar Senapati · S Md Adil Ahmed</p>
            <p className="mt-1">School of Computer Science and Engineering, RV University, Bengaluru, India</p>
            <p className="mt-3">Research prototype, not repair advice. Unsafe faults are always referred to a technician.</p>
          </div>
          <div className="md:text-right">
            <p>Code: MIT · Troubleshooting text: iFixit (CC BY-NC-SA 3.0) and ENERGY STAR (public domain)</p>
            <p className="mt-1">
              Photos on Unsplash by{" "}
              <a className="underline" href="https://unsplash.com/photos/_iiZXwwYFpQ" target="_blank" rel="noreferrer">Zhen Yao</a>,{" "}
              <a className="underline" href="https://unsplash.com/photos/ohynLBdsU9Y" target="_blank" rel="noreferrer">S. Laiba Ali</a> and{" "}
              <a className="underline" href="https://unsplash.com/photos/-Ifr1HGFeW8" target="_blank" rel="noreferrer">Caleb Woods</a>
            </p>
            <p className="mt-1"><a className="underline" href={GITHUB} target="_blank" rel="noreferrer">github.com/skypank-coder/Query2Diagnose</a></p>
          </div>
        </div>
      </footer>
    </div>
  );
}
