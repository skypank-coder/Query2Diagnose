"""Sanity-check the hypothesis model: provenance coverage, how informative each
attribute is, and a heatmap of p(attribute = value | fault).

    python -m bench.hypothesis_heatmap [--weights NAME] [--text]

The heatmap is written to results/sanity/hypothesis_heatmap[_NAME].png.
"""

from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from core.hypothesis import load_hypothesis_model
from core.paths import RESULTS

SHADES = " .:-=+*#%@"


def mutual_information(table: np.ndarray) -> float:
    """I(Z; A) in bits under a uniform prior over faults."""
    pz = np.full(table.shape[0], 1.0 / table.shape[0])
    joint = pz[:, None] * table
    pa = joint.sum(axis=0)
    return max(0.0, float(np.sum(joint * np.log2(table / pa[None, :]))))


def provenance_counts(model) -> dict[str, int]:
    counts = {"cited": 0, "definitional": 0, "healthy": 0, "uniform": 0}
    for fault in model.faults:
        for attribute in model.schema.attributes:
            counts[model.spec.source(fault, attribute)] += 1
    return counts


def print_text_table(model) -> None:
    for attribute, attr in model.schema.attributes.items():
        print(f"\n{attribute}")
        print(f"  {'':28}" + "".join(f"{v[:12]:>13}" for v in attr.values))
        for i, fault in enumerate(model.faults):
            cells = "".join(
                f"{p:>11.2f} {SHADES[min(int(p * len(SHADES)), len(SHADES) - 1)]}"
                for p in model.table[attribute][i])
            print(f"  {fault:28}{cells}")


def plot(model, path) -> None:
    columns, blocks = [], []
    for attribute, attr in model.schema.attributes.items():
        columns += [f"{attribute}={v}" for v in attr.values]
        blocks.append(model.table[attribute])
    matrix = np.hstack(blocks)
    fig, ax = plt.subplots(figsize=(max(12, 0.28 * len(columns)), 0.45 * len(model.faults) + 4))
    im = ax.imshow(matrix, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_xticks(range(len(columns)), columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(model.faults)), model.faults, fontsize=8)
    edge = -0.5
    for block in blocks[:-1]:
        edge += block.shape[1]
        ax.axvline(edge, color="white", linewidth=0.8)
    fig.colorbar(im, ax=ax, fraction=0.02, label="p(value | fault)")
    ax.set_title("Hypothesis model p(attribute = value | fault)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Sanity-check the hypothesis model.")
    ap.add_argument("--weights", help="sensitivity weight set from configs/hypothesis.yaml")
    ap.add_argument("--text", action="store_true", help="also print every row as a shaded table")
    args = ap.parse_args()
    model = load_hypothesis_model(args.weights)

    counts = provenance_counts(model)
    total = sum(counts.values())
    print(f"faults: {len(model.faults)}  attributes: {len(model.schema.attributes)}  "
          f"(fault, attribute) rows: {total}")
    print("  " + "  ".join(f"{k}: {v} ({v / total:.0%})" for k, v in counts.items()))

    print("\nI(Z; A) in bits, uniform prior over faults (how much one answer can tell apart):")
    ranked = sorted(((mutual_information(model.table[a]), a) for a in model.schema.attributes), reverse=True)
    for mi, attribute in ranked:
        effort = model.schema.attributes[attribute].effort
        print(f"  {attribute:28} {mi:6.3f}  {'#' * int(mi * 40)}  (effort {effort})")

    if args.text:
        print_text_table(model)
    suffix = f"_{args.weights}" if args.weights else ""
    path = RESULTS / "sanity" / f"hypothesis_heatmap{suffix}.png"
    plot(model, path)
    print(f"\nheatmap -> {path.relative_to(RESULTS.parent)}")


if __name__ == "__main__":
    main()
