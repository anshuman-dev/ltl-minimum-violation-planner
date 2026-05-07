"""
Büchi automata for common LTL spec patterns.
Implemented directly — no external tool needed.

Supported patterns:
  G(!p)   — safety: never visit p
  GF(p)   — recurrence: visit p infinitely often
  F(p)    — reachability: eventually visit p
  G(p)    — invariance: always be in p

Each automaton is a dict-based structure with:
  states    : list of state names
  initial   : initial state name
  delta     : (state, label_frozenset) -> next_state | None  (None = sink/stuck)
  accepting : set of accepting states
"""

from typing import Callable, FrozenSet, NamedTuple, Optional


class BuchiAut:
    def __init__(self, states, initial, delta_fn, accepting, name=""):
        self.states = states          # list of hashable state ids
        self.initial = initial
        self._delta = delta_fn        # (state, frozenset) -> state | None
        self.accepting = set(accepting)
        self.name = name

    def step(self, state, label: FrozenSet[str]) -> Optional[object]:
        return self._delta(state, label)

    def is_accepting(self, state) -> bool:
        return state in self.accepting


# ── factory functions ─────────────────────────────────────────────────────────

def safety(prop: str, label: str = "") -> BuchiAut:
    """G(!prop) — automaton rejects if prop is ever true."""
    # States: q0 (safe), q_sink (violated, non-accepting)
    def delta(state, lbl):
        if state == "q0":
            return "q_sink" if prop in lbl else "q0"
        return "q_sink"  # once violated, stay violated

    return BuchiAut(
        states=["q0", "q_sink"],
        initial="q0",
        delta_fn=delta,
        accepting=["q0"],  # must stay in q0 infinitely → never violated
        name=label or f"G(!{prop})",
    )


def recurrence(prop: str, label: str = "") -> BuchiAut:
    """GF(prop) — must visit prop infinitely often."""
    # States: q0 (waiting), q1 (just saw prop — accepting)
    def delta(state, lbl):
        if state == "q0":
            return "q1" if prop in lbl else "q0"
        # q1: already accepted, loop back to wait for next occurrence
        return "q0"

    return BuchiAut(
        states=["q0", "q1"],
        initial="q0",
        delta_fn=delta,
        accepting=["q1"],
        name=label or f"GF({prop})",
    )


def reachability(prop: str, label: str = "") -> BuchiAut:
    """F(prop) — eventually reach prop (then stay accepting)."""
    # States: q0 (searching), q1 (reached — accepting sink)
    def delta(state, lbl):
        if state == "q0":
            return "q1" if prop in lbl else "q0"
        return "q1"  # once reached, stay accepting

    return BuchiAut(
        states=["q0", "q1"],
        initial="q0",
        delta_fn=delta,
        accepting=["q1"],
        name=label or f"F({prop})",
    )


def invariance(prop: str, label: str = "") -> BuchiAut:
    """G(prop) — always be in prop."""
    def delta(state, lbl):
        if state == "q0":
            return "q0" if prop in lbl else "q_sink"
        return "q_sink"

    return BuchiAut(
        states=["q0", "q_sink"],
        initial="q0",
        delta_fn=delta,
        accepting=["q0"],
        name=label or f"G({prop})",
    )


# ── simple formula parser ─────────────────────────────────────────────────────

def parse_spec(formula: str, label: str = "") -> BuchiAut:
    """
    Parse simple LTL formula string into a BuchiAut.
    Supported:
      G(!p)   → safety
      GF(p)   → recurrence
      F(p)    → reachability
      G(p)    → invariance
    """
    f = formula.strip().replace(" ", "")
    lbl = label or formula

    if f.startswith("GF(") and f.endswith(")"):
        return recurrence(f[3:-1], lbl)
    if f.startswith("G(!") and f.endswith(")"):
        return safety(f[3:-1], lbl)
    if f.startswith("G(") and f.endswith(")"):
        return invariance(f[2:-1], lbl)
    if f.startswith("F(") and f.endswith(")"):
        return reachability(f[2:-1], lbl)

    raise ValueError(
        f"Unsupported formula: '{formula}'. "
        "Supported: G(!p), GF(p), G(p), F(p)"
    )
