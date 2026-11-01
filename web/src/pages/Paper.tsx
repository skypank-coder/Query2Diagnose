import { useEffect, useState } from "react";
import { api, type PaperInfo } from "../api";

const TITLE = "Query2Diagnose: Uncertainty-Aware Interactive Troubleshooting from Noisy, Code-Mixed and Incomplete User Descriptions";
const TEAM = ["Saatwik Kumar Yadav", "Rachana Bhaskar Gowda", "Priyanshu Kumar Senapati", "S Md Adil Ahmed"];
const BIBTEX = `@misc{yadav2026query2diagnose,
  author = {Saatwik Kumar Yadav and Rachana Bhaskar Gowda and Priyanshu Kumar Senapati and S Md Adil Ahmed},
  title  = {{Query2Diagnose}: Uncertainty-Aware Interactive Troubleshooting from Noisy, Code-Mixed and Incomplete User Descriptions},
  note   = {School of Computer Science and Engineering, RV University, Bengaluru, India},
  year   = {2026}
}`;

export default function Paper() {
  const [hasPdf, setHasPdf] = useState<boolean | null>(null);
  const [paper, setPaper] = useState<PaperInfo | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    fetch("/paper.pdf", { method: "HEAD" })
      .then((r) => setHasPdf(r.ok && (r.headers.get("content-type") ?? "").includes("pdf")))
      .catch(() => setHasPdf(false));
    api.paper().then(setPaper).catch(() => setPaper(null));
  }, []);
  const sectionNo = (() => { let n = 0; return (level: number) => (level === 1 ? ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"][n++] : ""); })();

  return (
    <div>
      <header className="rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900 to-accent-700 p-8 text-white shadow-xl md:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-300">IEEE conference paper</p>
        <h1 className="mt-3 max-w-4xl font-serif text-2xl font-semibold leading-snug md:text-4xl">{paper?.title ?? TITLE}</h1>
        <p className="mt-4 text-slate-200">{(paper?.authors.length ? paper.authors : TEAM).join(" · ")}</p>
        <p className="mt-1 text-sm text-slate-400">School of Computer Science and Engineering, RV University, Bengaluru, India</p>
        <div className="mt-6 flex flex-wrap gap-3">
          {hasPdf && <a className="btn bg-accent-400 text-slate-950 hover:bg-accent-300" href="/paper.pdf" target="_blank" rel="noreferrer">Open the PDF</a>}
          <button className="btn-glass" onClick={() => { navigator.clipboard?.writeText(BIBTEX); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
            {copied ? "BibTeX copied" : "Copy BibTeX"}
          </button>
          <a className="btn-glass" href="https://github.com/skypank-coder/Query2Diagnose" target="_blank" rel="noreferrer">Code and data</a>
        </div>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.6fr_1fr] [&>*]:min-w-0">
        <div className="space-y-6">
          <section className="card">
            <h2 className="font-serif text-xl font-semibold text-slate-900 dark:text-white">Abstract</h2>
            {paper?.abstract
              ? <p className="mt-3 leading-relaxed text-slate-700 dark:text-slate-300">{paper.abstract}</p>
              : <p className="mt-3 text-sm muted">The abstract is read from the local manuscript (paper/query2diagnose_paper.tex), which is not on this machine.</p>}
            {paper?.keywords.length ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {paper.keywords.map((k) => <span key={k} className="chip border-accent-200 bg-accent-50 text-accent-700 dark:border-accent-700 dark:bg-accent-700/20 dark:text-accent-300">{k}</span>)}
              </div>
            ) : null}
          </section>
          <section className="card p-0">
            {hasPdf ? (
              <iframe src="/paper.pdf" title="Query2Diagnose paper" className="h-[85vh] w-full rounded-xl" />
            ) : (
              <div className="p-8 text-sm muted">
                {hasPdf === null ? "Checking for the PDF…" : "Compile the paper on Overleaf and save it as web/public/paper.pdf (and web/dist/paper.pdf) to show it here."}
              </div>
            )}
          </section>
        </div>
        <aside className="space-y-6">
          {paper?.sections.length ? (
            <section className="card">
              <h2 className="font-semibold text-slate-900 dark:text-white">Contents</h2>
              <ol className="mt-3 space-y-1 text-sm">
                {paper.sections.map((sec, i) => (
                  <li key={i} className={sec.level === 1 ? "mt-2 font-medium text-slate-800 dark:text-slate-100" : "pl-6 muted"}>
                    {sec.level === 1 && <span className="mr-2 inline-block w-7 font-mono text-xs text-accent-600">{sectionNo(1)}.</span>}
                    {sec.title}
                  </li>
                ))}
              </ol>
            </section>
          ) : null}
          <section className="card">
            <h2 className="font-semibold text-slate-900 dark:text-white">Cite</h2>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-100 p-3 font-mono text-[11px] leading-relaxed dark:bg-slate-800">{BIBTEX}</pre>
          </section>
        </aside>
      </div>
    </div>
  );
}
