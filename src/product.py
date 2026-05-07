"""
Product automaton: GridWorld × Büchi_1 × ... × Büchi_n

A product state is (grid_pos, aut_state_1, ..., aut_state_n).
We build the graph lazily via BFS, then run Tarjan's SCC algorithm.
"""

from collections import defaultdict, deque
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from .grid_world import GridWorld
from .automata import BuchiAut


# A product state is a tuple: (grid_pos, q1, q2, ..., qn)
ProductState = tuple


class ProductGraph:
    def __init__(self, grid: GridWorld, automata: List[BuchiAut]):
        self.grid = grid
        self.automata = automata
        self.n_aut = len(automata)

        # Initial product state
        init_aut = tuple(a.initial for a in automata)
        self.initial: ProductState = (grid.start,) + init_aut

        # Build graph
        self.states: List[ProductState] = []
        self.state_index: Dict[ProductState, int] = {}
        self.adj: Dict[int, List[int]] = defaultdict(list)      # forward edges
        self.radj: Dict[int, List[int]] = defaultdict(list)     # reverse edges
        self._build()

    # ── graph construction ────────────────────────────────────────────────────

    def _build(self):
        queue = deque([self.initial])
        self._add_state(self.initial)

        while queue:
            ps = queue.popleft()
            src_idx = self.state_index[ps]
            grid_pos = ps[0]
            aut_states = ps[1:]

            label = self.grid.label(grid_pos)

            for _, next_pos in self.grid.successors(grid_pos):
                next_label = self.grid.label(next_pos)
                # Advance each automaton on next_label (transition happens
                # when entering the next cell, consistent with standard semantics)
                next_aut = []
                valid = True
                for i, aut in enumerate(self.automata):
                    nq = aut.step(aut_states[i], next_label)
                    if nq is None:
                        valid = False
                        break
                    next_aut.append(nq)

                if not valid:
                    continue

                next_ps: ProductState = (next_pos,) + tuple(next_aut)
                if next_ps not in self.state_index:
                    self._add_state(next_ps)
                    queue.append(next_ps)

                dst_idx = self.state_index[next_ps]
                self.adj[src_idx].append(dst_idx)
                self.radj[dst_idx].append(src_idx)

    def _add_state(self, ps: ProductState) -> int:
        idx = len(self.states)
        self.states.append(ps)
        self.state_index[ps] = idx
        return idx

    # ── Tarjan's SCC ─────────────────────────────────────────────────────────

    def compute_sccs(self) -> List[List[int]]:
        """Returns list of SCCs (each a list of state indices), largest first."""
        n = len(self.states)
        index_counter = [0]
        stack = []
        lowlink = {}
        index = {}
        on_stack = {}
        sccs = []

        def strongconnect(v):
            index[v] = index_counter[0]
            lowlink[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack[v] = True

            for w in self.adj[v]:
                if w not in index:
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif on_stack.get(w):
                    lowlink[v] = min(lowlink[v], index[w])

            if lowlink[v] == index[v]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        import sys
        sys.setrecursionlimit(100000)

        for v in range(n):
            if v not in index:
                strongconnect(v)

        return sccs

    # ── SCC reward analysis ───────────────────────────────────────────────────

    def scc_satisfied_specs(self, scc: List[int], rewards: List[float]) -> Tuple[float, Set[int]]:
        """
        For an SCC, compute which specs have their accepting states inside it.
        Returns (total_reward, set_of_satisfied_spec_indices).
        """
        satisfied = set()
        for idx in scc:
            ps = self.states[idx]
            aut_states = ps[1:]
            for i, aut in enumerate(self.automata):
                if aut.is_accepting(aut_states[i]):
                    satisfied.add(i)

        total = sum(rewards[i] for i in satisfied)
        return total, satisfied

    def is_nontrivial_scc(self, scc: List[int]) -> bool:
        """An SCC is nontrivial if it has >1 state, or 1 state with a self-loop."""
        if len(scc) > 1:
            return True
        v = scc[0]
        return v in self.adj[v]

    # ── reachability ─────────────────────────────────────────────────────────

    def reachable_from_initial(self) -> Set[int]:
        visited = set()
        queue = deque([self.state_index[self.initial]])
        while queue:
            v = queue.popleft()
            if v in visited:
                continue
            visited.add(v)
            for w in self.adj[v]:
                if w not in visited:
                    queue.append(w)
        return visited

    def bfs_path(self, src: int, targets: Set[int]) -> Optional[List[int]]:
        """BFS from src to any state in targets. Returns list of state indices."""
        if src in targets:
            return [src]
        parent = {src: None}
        queue = deque([src])
        while queue:
            v = queue.popleft()
            for w in self.adj[v]:
                if w not in parent:
                    parent[w] = v
                    if w in targets:
                        # reconstruct
                        path = []
                        cur = w
                        while cur is not None:
                            path.append(cur)
                            cur = parent[cur]
                        return list(reversed(path))
                    queue.append(w)
        return None

    def find_cycle_through(self, scc_set: Set[int], required_accepting: List[Set[int]]) -> Optional[List[int]]:
        """
        Find a cycle within the SCC that passes through at least one accepting
        state for each required spec.
        Returns a list of state indices forming the cycle (first == last).
        """
        # Restrict graph to SCC nodes
        # Strategy: chain BFS paths through each required accepting set
        # Start from any state in scc, visit a state in required_accepting[0],
        # then required_accepting[1], ..., then return to start.

        if not scc_set:
            return None

        start = next(iter(scc_set))

        # Build checkpoints: for each spec, one state in scc that is accepting
        checkpoints = []
        for acc_set in required_accepting:
            candidates = acc_set & scc_set
            if candidates:
                checkpoints.append(next(iter(candidates)))

        if not checkpoints:
            # trivial cycle: just loop at start (if self-loop exists)
            if start in self.adj.get(start, []):
                return [start, start]
            # find any 2-cycle
            path = self._bfs_in_scc(start, {start}, scc_set)
            return path

        # chain: start -> cp0 -> cp1 -> ... -> cpN -> start
        waypoints = [start] + checkpoints + [start]
        full_path = []
        for i in range(len(waypoints) - 1):
            seg = self._bfs_in_scc(waypoints[i], {waypoints[i + 1]}, scc_set)
            if seg is None:
                return None
            if full_path:
                full_path.extend(seg[1:])  # skip duplicate junction
            else:
                full_path.extend(seg)

        return full_path

    def _bfs_in_scc(self, src: int, targets: Set[int], scc_set: Set[int]) -> Optional[List[int]]:
        """BFS from src to any target, restricted to scc_set."""
        if src in targets:
            return [src]
        parent = {src: None}
        queue = deque([src])
        while queue:
            v = queue.popleft()
            for w in self.adj[v]:
                if w in scc_set and w not in parent:
                    parent[w] = v
                    if w in targets:
                        path = []
                        cur = w
                        while cur is not None:
                            path.append(cur)
                            cur = parent[cur]
                        return list(reversed(path))
                    queue.append(w)
        return None
