"""
Maximum-reward lasso planner.

Given a product automaton and per-spec rewards, finds:
  1. The SCC with maximum total reward that is reachable from the initial state
  2. A lasso path: prefix (initial → SCC) + cycle (within SCC visiting accepting states)

Returns the path as a sequence of grid positions plus a result summary.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .grid_world import GridWorld
from .automata import BuchiAut
from .product import ProductGraph


@dataclass
class PlanResult:
    path: List[Tuple[int, int]]       # grid positions (prefix + one full cycle)
    cycle_start_idx: int               # index in path where cycle begins
    satisfied: List[int]               # indices of satisfied specs
    violated: List[int]                # indices of violated specs
    total_reward: float
    max_possible_reward: float
    spec_names: List[str]
    spec_rewards: List[float]
    success: bool
    message: str


def plan(
    grid: GridWorld,
    automata: List[BuchiAut],
    rewards: List[float],
) -> PlanResult:
    spec_names = [a.name for a in automata]
    max_possible = sum(rewards)

    pg = ProductGraph(grid, automata)
    sccs = pg.compute_sccs()
    reachable = pg.reachable_from_initial()

    # Filter to nontrivial SCCs reachable from initial
    init_idx = pg.state_index[pg.initial]
    candidates = []
    for scc in sccs:
        scc_set = set(scc)
        if not any(v in reachable for v in scc):
            continue
        if not pg.is_nontrivial_scc(scc):
            continue
        reward, satisfied_set = pg.scc_satisfied_specs(scc, rewards)
        candidates.append((reward, satisfied_set, scc))

    if not candidates:
        return PlanResult(
            path=[], cycle_start_idx=0,
            satisfied=[], violated=list(range(len(automata))),
            total_reward=0, max_possible_reward=max_possible,
            spec_names=spec_names, spec_rewards=list(rewards),
            success=False,
            message="No reachable accepting cycle found. Check for obstacles blocking all paths.",
        )

    # Pick best SCC
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_reward, satisfied_set, best_scc = candidates[0]
    best_scc_set = set(best_scc)
    violated_set = set(range(len(automata))) - satisfied_set

    # Build accepting state sets per spec (restricted to the best SCC)
    required_accepting = []
    for i, aut in enumerate(automata):
        if i in satisfied_set:
            acc_in_scc = {
                v for v in best_scc_set
                if aut.is_accepting(pg.states[v][1 + i])
            }
            required_accepting.append(acc_in_scc)

    # Find prefix: initial → any state in best SCC
    prefix_path = pg.bfs_path(init_idx, best_scc_set)
    if prefix_path is None:
        return PlanResult(
            path=[], cycle_start_idx=0,
            satisfied=[], violated=list(range(len(automata))),
            total_reward=0, max_possible_reward=max_possible,
            spec_names=spec_names, spec_rewards=list(rewards),
            success=False,
            message="Could not find path to best SCC (graph error).",
        )

    # Find cycle within SCC through required accepting states
    cycle_start_prod = prefix_path[-1]
    cycle_scc = best_scc_set  # restrict to scc

    # For cycle, we need to start from the endpoint of the prefix
    cycle_entry = prefix_path[-1]
    cycle = pg.find_cycle_through(best_scc_set, required_accepting)

    if cycle is None:
        return PlanResult(
            path=[], cycle_start_idx=0,
            satisfied=[], violated=list(range(len(automata))),
            total_reward=0, max_possible_reward=max_possible,
            spec_names=spec_names, spec_rewards=list(rewards),
            success=False,
            message="Could not construct cycle within SCC.",
        )

    # Connect prefix end to cycle start (they may differ)
    if prefix_path[-1] != cycle[0]:
        bridge = pg.bfs_path(prefix_path[-1], {cycle[0]})
        if bridge is None:
            bridge = [prefix_path[-1]]
        full_prod_path = prefix_path[:-1] + bridge + cycle[1:]
        cycle_start_idx = len(prefix_path[:-1] + bridge) - 1
    else:
        full_prod_path = prefix_path + cycle[1:]
        cycle_start_idx = len(prefix_path) - 1

    # Extract grid positions
    grid_path = [pg.states[v][0] for v in full_prod_path]

    return PlanResult(
        path=grid_path,
        cycle_start_idx=cycle_start_idx,
        satisfied=sorted(satisfied_set),
        violated=sorted(violated_set),
        total_reward=best_reward,
        max_possible_reward=max_possible,
        spec_names=spec_names,
        spec_rewards=list(rewards),
        success=True,
        message=f"Plan found! Satisfies {len(satisfied_set)}/{len(automata)} specs "
                f"(reward {best_reward:.0f}/{max_possible:.0f}).",
    )
