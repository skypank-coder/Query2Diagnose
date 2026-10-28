"""Joint belief b_t(s, z) over interpretations and faults (paper Sec. III-A).

Initialisation, eq. (1):  b_0(s, z) = p(z | s) p(s | x)
Update, eq. (2):          b_{t+1}(s, z) ∝ p(a_t | q_t, s, z) b_t(s, z)

Answer model (decision 3): the true value t of the asked attribute A is s[A]
if interpretation s mentions A, else drawn from the hypothesis model
p(A = t | z). The user says "not sure" with probability eta (uninformative);
otherwise reports t, or a uniformly random other value with probability
epsilon. Entropies are in bits.
"""

from __future__ import annotations

import numpy as np

from core.hypothesis import HypothesisModel
from core.schema import NOT_SURE


def entropy(p: np.ndarray) -> float:
    p = p[p > 0]
    return max(0.0, float(-(p * np.log2(p)).sum()))


class Belief:
    def __init__(self, model: HypothesisModel, interpretations: list[dict[str, str]], p_s: np.ndarray,
                 epsilon: float = 0.05, eta: float = 0.05):
        self.model = model
        self.interpretations = interpretations
        self.epsilon, self.eta = epsilon, eta
        p_z_given_s = np.stack([model.fault_posterior(s) for s in interpretations])   # (n_s, n_z)
        self.b = p_s[:, None] * p_z_given_s
        self.b /= self.b.sum()
        self.answers: dict[str, str] = {}

    # --- marginals and entropies ---------------------------------------------
    @property
    def p_s(self) -> np.ndarray:
        return self.b.sum(axis=1)

    @property
    def p_z(self) -> np.ndarray:
        return self.b.sum(axis=0)

    @property
    def h_l(self) -> float:
        return entropy(self.p_s)

    @property
    def h_d(self) -> float:
        return entropy(self.p_z)

    @property
    def h(self) -> float:
        return entropy(self.b.ravel())

    def top_faults(self, n: int = 3) -> list[tuple[str, float]]:
        order = np.argsort(self.p_z)[::-1][:n]
        return [(self.model.faults[i], float(self.p_z[i])) for i in order]

    # --- answer model ----------------------------------------------------------
    def answer_values(self, attribute: str) -> list[str]:
        return self.model.schema.attributes[attribute].values + [NOT_SURE]

    def likelihood(self, attribute: str, answer: str) -> np.ndarray:
        """p(a | q_A, s, z) for every (s, z): shape (n_s, n_z)."""
        n_s, n_z = self.b.shape
        if answer == NOT_SURE:
            return np.full((n_s, n_z), self.eta)
        values = self.model.schema.attributes[attribute].values
        n = len(values)
        right, wrong = (1 - self.eta) * (1 - self.epsilon), (1 - self.eta) * self.epsilon / (n - 1)
        p_true_z = self.model.likelihood(attribute, answer)            # p(t = a | z)
        from_model = right * p_true_z + wrong * (1 - p_true_z)        # sum over t of p(a|t) p(t|z)
        out = np.empty((n_s, n_z))
        for i, s in enumerate(self.interpretations):
            if attribute in s:
                out[i, :] = right if s[attribute] == answer else wrong
            else:
                out[i, :] = from_model
        return out

    def predictive(self, attribute: str) -> dict[str, float]:
        """p(a | b_t, q_A) for every possible answer."""
        return {a: float((self.likelihood(attribute, a) * self.b).sum()) for a in self.answer_values(attribute)}

    def posterior(self, attribute: str, answer: str) -> np.ndarray:
        post = self.likelihood(attribute, answer) * self.b
        return post / post.sum()

    def update(self, attribute: str, answer: str) -> None:
        """Eq. (2)."""
        self.b = self.posterior(attribute, answer)
        self.answers[attribute] = answer

    def copy(self) -> Belief:
        other = object.__new__(Belief)
        other.__dict__.update(self.__dict__)
        other.b = self.b.copy()
        other.answers = dict(self.answers)
        return other
