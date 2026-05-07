"""
Grid world transition system.
Each cell is labeled with a set of atomic propositions.
Robots move N/S/E/W; obstacles block movement.
"""

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Set, Tuple

MOVES = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}

# Cell type → set of atomic propositions true at that cell
CELL_PROPS = {
    "free":     frozenset(),
    "obstacle": frozenset({"obstacle"}),
    "zone_a":   frozenset({"zone_a"}),
    "zone_b":   frozenset({"zone_b"}),
    "zone_c":   frozenset({"zone_c"}),
    "danger":   frozenset({"danger"}),
    "goal":     frozenset({"goal"}),
    "start":    frozenset(),
}


@dataclass
class GridWorld:
    n: int
    grid: List[List[str]] = field(default_factory=list)
    start: Tuple[int, int] = (0, 0)

    def __post_init__(self):
        if not self.grid:
            self.grid = [["free"] * self.n for _ in range(self.n)]

    def label(self, pos: Tuple[int, int]) -> FrozenSet[str]:
        r, c = pos
        return CELL_PROPS.get(self.grid[r][c], frozenset())

    def successors(self, pos: Tuple[int, int]) -> List[Tuple[str, Tuple[int, int]]]:
        r, c = pos
        result = []
        for action, (dr, dc) in MOVES.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.n and 0 <= nc < self.n:
                if self.grid[nr][nc] != "obstacle":
                    result.append((action, (nr, nc)))
        # also allow staying in place (needed for sync / waiting)
        result.append(("stay", pos))
        return result

    def all_positions(self) -> List[Tuple[int, int]]:
        return [
            (r, c)
            for r in range(self.n)
            for c in range(self.n)
            if self.grid[r][c] != "obstacle"
        ]


def make_scenario(name: str) -> GridWorld:
    """Built-in demo scenarios."""
    if name == "road":
        # 8×8 road network
        # danger=double-line zone, zone_a=pickup, zone_b=dropoff, goal=destination
        n = 8
        g = GridWorld(n=n)
        g.start = (0, 0)
        # vertical danger strip (double line)
        for r in range(n):
            g.grid[r][3] = "danger"
        # obstacle block
        for r in range(2, 5):
            g.grid[r][5] = "obstacle"
        g.grid[1][6] = "zone_a"
        g.grid[6][1] = "zone_b"
        g.grid[7][7] = "goal"
        return g

    if name == "patrol":
        # 6×6 warehouse patrol
        n = 6
        g = GridWorld(n=n)
        g.start = (0, 0)
        g.grid[0][5] = "zone_a"
        g.grid[5][0] = "zone_b"
        g.grid[2][2] = "danger"
        g.grid[2][3] = "danger"
        g.grid[3][2] = "danger"
        g.grid[3][3] = "danger"
        return g

    if name == "rescue":
        # 7×7 rescue mission
        n = 7
        g = GridWorld(n=n)
        g.start = (3, 0)
        for c in range(1, 6):
            g.grid[3][c] = "obstacle"
        g.grid[3][3] = "free"
        g.grid[0][6] = "zone_a"
        g.grid[6][6] = "zone_b"
        for r in [1, 2, 4, 5]:
            g.grid[r][2] = "danger"
        g.grid[0][0] = "zone_c"
        return g

    raise ValueError(f"Unknown scenario: {name}")
