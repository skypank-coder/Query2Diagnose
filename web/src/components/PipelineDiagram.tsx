// Fig. 1 of the paper: the Query2Diagnose interaction pipeline.
const STEPS = [
  ["User description", "noisy, code-mixed, incomplete"],
  ["Input understanding", "sample K interpretations: device, symptoms, observations, negation"],
  ["Structured fault state", "confirmed facts, uncertain readings, missing attributes"],
  ["Question selection", "score clarification and diagnostic questions by gain, effort, clarity"],
] as const;

export default function PipelineDiagram() {
  const w = 560, boxH = 54, gap = 22, x = 40, bw = 400;
  const y = (i: number) => 10 + i * (boxH + gap);
  const decisionY = y(4) + 10;
  const outY = decisionY + 90;
  return (
    <svg viewBox={`0 0 ${w} ${outY + boxH + 12}`} className="h-auto w-full max-w-xl" role="img" aria-label="Query2Diagnose pipeline">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="fill-slate-400" />
        </marker>
      </defs>
      {STEPS.map(([title, sub], i) => (
        <g key={title}>
          <rect x={x} y={y(i)} width={bw} height={boxH} rx="10"
            className={i === 0 ? "fill-slate-100 stroke-slate-300 dark:fill-slate-800 dark:stroke-slate-600" : "fill-accent-50 stroke-accent-400 dark:fill-accent-700/20 dark:stroke-accent-500"} />
          <text x={x + bw / 2} y={y(i) + 22} textAnchor="middle" className="fill-slate-900 text-[14px] font-semibold dark:fill-white">{title}</text>
          <text x={x + bw / 2} y={y(i) + 40} textAnchor="middle" className="fill-slate-500 text-[11px] dark:fill-slate-400">{sub}</text>
          <line x1={x + bw / 2} y1={y(i) + boxH} x2={x + bw / 2} y2={y(i) + boxH + gap - 2} className="stroke-slate-400" markerEnd="url(#arrow)" />
        </g>
      ))}
      {/* Stop? decision */}
      <polygon points={`${x + bw / 2},${decisionY - 6} ${x + bw / 2 + 52},${decisionY + 26} ${x + bw / 2},${decisionY + 58} ${x + bw / 2 - 52},${decisionY + 26}`}
        className="fill-white stroke-slate-400 dark:fill-slate-900" />
      <text x={x + bw / 2} y={decisionY + 31} textAnchor="middle" className="fill-slate-900 text-[13px] font-semibold dark:fill-white">Stop?</text>
      {/* no: ask user, update belief, loop back to question selection */}
      <line x1={x + bw / 2 + 52} y1={decisionY + 26} x2={w - 20} y2={decisionY + 26} className="stroke-slate-400" />
      <line x1={w - 20} y1={decisionY + 26} x2={w - 20} y2={y(3) + boxH / 2} className="stroke-slate-400" />
      <line x1={w - 20} y1={y(3) + boxH / 2} x2={x + bw + 2} y2={y(3) + boxH / 2} className="stroke-slate-400" markerEnd="url(#arrow)" />
      <text x={w - 26} y={decisionY + 18} textAnchor="end" className="fill-slate-500 text-[11px]">no: ask user,</text>
      <text x={w - 26} y={decisionY + 44} textAnchor="end" className="fill-slate-500 text-[11px]">update belief (eq. 2)</text>
      {/* yes: output */}
      <line x1={x + bw / 2} y1={decisionY + 58} x2={x + bw / 2} y2={outY - 2} className="stroke-slate-400" markerEnd="url(#arrow)" />
      <text x={x + bw / 2 + 8} y={decisionY + 76} className="fill-slate-500 text-[11px]">yes</text>
      <rect x={x} y={outY} width={bw} height={boxH} rx="10" className="fill-slate-900 dark:fill-accent-600" />
      <text x={x + bw / 2} y={outY + 22} textAnchor="middle" className="fill-white text-[14px] font-semibold">Evidence-grounded output</text>
      <text x={x + bw / 2} y={outY + 40} textAnchor="middle" className="fill-slate-300 text-[11px] dark:fill-accent-50">fault category, cited manual passages, safe next steps, or referral</text>
    </svg>
  );
}
