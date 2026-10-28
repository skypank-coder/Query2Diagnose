import { Section } from "../components/ui";
import { Tex } from "../components/Tex";

const STEPS = [
  ["Sample", "Draw K interpretations of the message x from the LLM with a strict schema prompt; normalise Romanized Kannada / Hindi first, keeping the original text."],
  ["Cluster", "Group samples that agree on every schema field; class frequency estimates p(s | x). Its entropy is the linguistic uncertainty."],
  ["Initialise", "b₀(s, z) ∝ p(z | s) p(s | x), with p(z | s) from a hand-built hypothesis model whose every tag cites a troubleshooting passage."],
  ["Ask", "Candidates: clarification questions for uncertain attributes, diagnostic questions for unknown attributes that still separate faults. Pick by eq. (3)."],
  ["Update", "Parse the answer and update the joint belief with eq. (2), allowing for wrong and “not sure” answers."],
  ["Stop or refer", "Answer when max_z b(z) ≥ τ and a retrieved passage supports z; refer immediately if that fault is unsafe; refer with the collected facts at T_max."],
];

export default function Method() {
  return (
    <div className="max-w-3xl">
      <h1 className="font-serif text-3xl font-semibold text-slate-900 dark:text-white">Method</h1>
      <p className="mt-3 muted">
        The opening message x is not taken at face value. Its structured interpretation s (device, symptom, observations, negations)
        is itself uncertain, so the system reasons over the joint space of interpretations and fault categories z.
      </p>

      <Section title="1 · Marginal over interpretations">
        <div className="card"><Tex block>{String.raw`p(z \mid x) = \sum_{s \in \mathcal{S}} p(z \mid s)\, p(s \mid x)`}</Tex>
          <p className="text-sm muted"><Tex>{String.raw`p(s\mid x)`}</Tex> carries linguistic uncertainty; <Tex>{String.raw`p(z\mid s)`}</Tex> carries diagnostic uncertainty.</p></div>
      </Section>

      <Section title="2 · Belief update">
        <div className="card"><Tex block>{String.raw`b_{t+1}(s, z) \;\propto\; p(a_t \mid q_t, s, z)\, b_t(s, z)`}</Tex>
          <Tex block>{String.raw`H_L(b_t) = H\Big(\sum_z b_t(s,z)\Big), \qquad H_D(b_t) = H\Big(\sum_s b_t(s,z)\Big)`}</Tex>
          <p className="text-sm muted">A clean but brief message has low H<sub>L</sub> and high H<sub>D</sub>; a heavily code-mixed one can have both high.</p></div>
      </Section>

      <Section title="3 · Question selection">
        <div className="card"><Tex block>{String.raw`q_t = \arg\max_{q \in \mathcal{Q}_t} \Big[\, \mathbb{E}_a\big[\Delta H_t(q, a)\big] - \lambda\, C(q) - \mu\, A(q) \,\Big]`}</Tex>
          <p className="text-sm muted">
            <Tex>{String.raw`\Delta H_t(q,a) = H(b_t) - H(b_{t+1} \mid q, a)`}</Tex> is taken over the joint space, so clarification and diagnostic
            questions compete on equal terms: when linguistic uncertainty dominates, clarification wins; once the reading is settled,
            diagnostic questions take over. C(q) is user effort, A(q) the estimated chance the question is misunderstood; λ and μ are tuned on validation only.
          </p></div>
      </Section>

      <Section title="Algorithm">
        <ol className="space-y-3">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="card flex gap-4">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-600 text-sm font-semibold text-white">{i + 1}</span>
              <div><div className="font-semibold">{title}</div><p className="mt-1 text-sm muted">{text}</p></div>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="Baselines">
        <ul className="list-disc space-y-1 pl-5 text-sm muted">
          <li><strong>B1</strong> direct answer: one LLM call with the message and retrieved passages.</li>
          <li><strong>B2</strong> LLM questioning: the same LLM asks follow-ups with ordinary prompting, same turn budget and simulator.</li>
          <li><strong>B3</strong> information gain over faults only: one interpretation, H<sub>L</sub> = 0, no clarification, no cost or clarity terms.</li>
        </ul>
      </Section>
    </div>
  );
}
