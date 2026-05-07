---
title: Minimum-Violation LTL Planning
emoji: 🤖
colorFrom: blue
colorTo: red
sdk: gradio
sdk_version: "5.25.0"
app_file: app.py
pinned: false
license: mit
short_description: Interactive minimum-violation LTL planner (ACC 2013)
---

# Minimum-Violation LTL Planning

Interactive reproduction of:

> Tumova, Reyes-Castro, Karaman, Frazzoli, Rus — **"Minimum-Violation LTL Planning with Conflicting Specifications"** — ACC 2013. [arXiv:1303.3679](https://arxiv.org/abs/1303.3679)

## What it demonstrates

When a robot's logical specifications conflict (e.g. "always avoid the danger zone" vs "reach the goal through the danger zone"), a standard planner simply fails. This algorithm instead finds the plan that **satisfies the highest-priority specs** and minimally violates the rest.

**Core idea:**
- Each spec φᵢ has a reward rᵢ (higher = harder to violate)
- Build the product automaton: grid × Büchi(φ₁) × Büchi(φ₂) × ...
- Find the max-reward strongly connected component (SCC) reachable from the start
- Reconstruct a lasso path (prefix + repeating cycle) through that SCC

**Try it:** drag the reward sliders to swap priorities — the planned path changes to satisfy whichever spec now has the highest weight.

## Specs supported

| Formula | Meaning |
|---|---|
| `G(!p)` | Safety: never visit region p |
| `GF(p)` | Recurrence: visit p infinitely often |
| `F(p)` | Reachability: eventually reach p |
| `G(p)` | Invariance: always stay in p |

## Implementation

Pure Python, no external tools:
- **Büchi automata** implemented directly for each formula pattern
- **Product automaton** built lazily via BFS
- **SCC detection** via Tarjan's algorithm
- **Lasso reconstruction** via BFS within the winning SCC
- **Visualization** via matplotlib → PIL → Gradio

## Related work (Jana Tumova's group)

- [KTH RPL Planiacs](https://github.com/KTH-RPL-Planiacs)
- [Jana Tumova's homepage](https://sites.google.com/view/janatumova/home)
