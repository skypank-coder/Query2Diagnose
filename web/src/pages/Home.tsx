import { Link } from "react-router-dom";
import PipelineDiagram from "../components/PipelineDiagram";
import { Section } from "../components/ui";

const TEAM = ["Saatwik Kumar Yadav", "Rachana Bhaskar Gowda", "Priyanshu Kumar Senapati", "S Md Adil Ahmed"];
const GITHUB = "https://github.com/skypank-coder/Query2Diagnose";

const IDEAS = [
  ["Two kinds of doubt", "Linguistic uncertainty (what did the user say?) and diagnostic uncertainty (which fault is it?) are tracked separately as H_L and H_D."],
  ["One objective for every question", "Clarification and diagnostic questions compete under expected information gain minus user effort and question clarity."],
  ["Grounded, and allowed to refer", "Answers cite retrieved troubleshooting passages; unsafe faults and unsupported conclusions always go to a technician."],
];

export default function Home() {
  return (
    <div>
      <section className="grid items-center gap-10 py-6 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <p className="text-sm font-medium uppercase tracking-wider text-accent-600 dark:text-accent-400">Research prototype</p>
          <h1 className="mt-3 font-serif text-4xl font-semibold leading-tight tracking-tight text-slate-900 md:text-5xl dark:text-white">
            Query2Diagnose: uncertainty-aware interactive troubleshooting from noisy, code-mixed and incomplete descriptions
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-slate-600 dark:text-slate-300">
            People rarely describe a broken appliance the way a manual does. A message like
            <span className="mx-1 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.9em] dark:bg-slate-800">fridge cooling agalla compressor sound ide</span>
            mixes Romanized Kannada with English and leaves out what a technician would ask first. Query2Diagnose keeps a belief over
            both <em>what the user meant</em> and <em>which fault is responsible</em>, asks the question that resolves the most of
            either, grounds its answer in retrieved documentation, and refers to a technician when no safe conclusion is supported.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link to="/demo" className="btn-primary">Try the live demo</Link>
            <Link to="/results" className="btn-ghost">Results</Link>
            <Link to="/paper" className="btn-ghost">Paper</Link>
            <a href={GITHUB} className="btn-ghost" target="_blank" rel="noreferrer">GitHub</a>
          </div>
        </div>
        <div className="card flex justify-center">
          <PipelineDiagram />
        </div>
      </section>

      <Section title="Key ideas">
        <div className="grid gap-4 md:grid-cols-3">
          {IDEAS.map(([title, text]) => (
            <div key={title} className="card">
              <h3 className="font-serif text-lg font-semibold text-slate-900 dark:text-white">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed muted">{text}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Team" subtitle="School of Computer Science and Engineering, RV University, Bengaluru">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {TEAM.map((name) => (
            <div key={name} className="card flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent-100 font-semibold text-accent-700 dark:bg-accent-700/30 dark:text-accent-400">
                {name.split(" ").map((p) => p[0]).slice(0, 2).join("")}
              </div>
              <div className="text-sm font-medium">{name}</div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}
