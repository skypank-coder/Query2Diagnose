import { useEffect, useState } from "react";

const BIBTEX = `@misc{yadav2026query2diagnose,
  title  = {Query2Diagnose: Uncertainty-Aware Interactive Troubleshooting from
            Noisy, Code-Mixed and Incomplete User Descriptions},
  author = {Yadav, Saatwik Kumar and Gowda, Rachana Bhaskar and
            Senapati, Priyanshu Kumar and Ahmed, S Md Adil},
  year   = {2026},
  note   = {School of Computer Science and Engineering, RV University, Bengaluru}
}`;

export default function Paper() {
  const [hasPdf, setHasPdf] = useState<boolean | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    fetch("/paper.pdf", { method: "HEAD" }).then((r) => setHasPdf(r.ok && (r.headers.get("content-type") ?? "").includes("pdf"))).catch(() => setHasPdf(false));
  }, []);
  return (
    <div>
      <h1 className="font-serif text-3xl font-semibold text-slate-900 dark:text-white">Paper</h1>
      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="card p-0">
          {hasPdf ? (
            <iframe src="/paper.pdf" title="Query2Diagnose paper" className="h-[80vh] w-full rounded-xl" />
          ) : (
            <div className="p-8 text-sm muted">
              {hasPdf === null ? "Checking for the paper…" : "The paper PDF is not published with this site yet. Place it at web/public/paper.pdf to embed it here."}
            </div>
          )}
        </div>
        <div className="space-y-4">
          <div className="card">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Cite</h2>
              <button className="btn-ghost px-3 py-1 text-xs" onClick={() => { navigator.clipboard?.writeText(BIBTEX); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
                {copied ? "Copied" : "Copy BibTeX"}
              </button>
            </div>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-100 p-3 font-mono text-xs dark:bg-slate-800">{BIBTEX}</pre>
          </div>
          {hasPdf && <a className="btn-primary w-full" href="/paper.pdf" target="_blank" rel="noreferrer">Open the PDF</a>}
        </div>
      </div>
    </div>
  );
}
