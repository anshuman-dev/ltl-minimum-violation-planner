"""
Visualization: static grid image + animated GIF of the planned path.
"""

import io
from typing import List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
import numpy as np
from PIL import Image

from .grid_world import GridWorld
from .planner import PlanResult

# Cell type → RGBA color
CELL_COLORS = {
    "free":     "#F5F5F5",
    "obstacle": "#2C2C2C",
    "zone_a":   "#A8D5FF",   # light blue
    "zone_b":   "#A8FFB8",   # light green
    "zone_c":   "#FFD6A8",   # light orange
    "danger":   "#FFAAAA",   # light red
    "goal":     "#FFE066",   # yellow
    "start":    "#D0B4FF",   # purple
}

PATH_COLOR   = "#1A73E8"
CYCLE_COLOR  = "#E83A1A"
START_MARKER = "#7B2FBE"


def _draw_grid(ax, grid: GridWorld, path: Optional[List[Tuple[int, int]]] = None,
               cycle_start_idx: int = 0, step: int = -1, show_path: bool = True):
    n = grid.n
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect("equal")
    ax.set_xticks(range(n + 1))
    ax.set_yticks(range(n + 1))
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.grid(True, color="#CCCCCC", linewidth=0.5)

    # Draw cells
    for r in range(n):
        for c in range(n):
            cell_type = grid.grid[r][c]
            color = CELL_COLORS.get(cell_type, "#F5F5F5")
            rect = mpatches.FancyBboxPatch(
                (c + 0.05, n - r - 1 + 0.05), 0.9, 0.9,
                boxstyle="round,pad=0.02",
                facecolor=color, edgecolor="#AAAAAA", linewidth=0.8,
            )
            ax.add_patch(rect)
            # label
            if cell_type not in ("free", "obstacle"):
                short = {"zone_a": "A", "zone_b": "B", "zone_c": "C",
                         "danger": "⚠", "goal": "★", "start": "S"}.get(cell_type, "")
                ax.text(c + 0.5, n - r - 0.5, short,
                        ha="center", va="center", fontsize=8,
                        color="#444444", fontweight="bold")

    # Start marker
    sr, sc = grid.start
    ax.plot(sc + 0.5, n - sr - 0.5, "o", color=START_MARKER,
            markersize=10, zorder=5, markeredgecolor="white", markeredgewidth=1.5)

    if not show_path or path is None or len(path) == 0:
        return

    static_mode = (step < 0)
    display_path = path if static_mode else path[:step + 1]

    def to_xy(pos):
        r, c = pos
        return c + 0.5, n - r - 0.5

    # In static mode show full path split by color; in animation mode show
    # only the portion reached so far.
    if static_mode:
        prefix = display_path[:cycle_start_idx + 1]
        cycle  = display_path[cycle_start_idx:]

        if len(prefix) > 1:
            xs, ys = zip(*[to_xy(p) for p in prefix])
            ax.plot(xs, ys, "-o", color=PATH_COLOR, linewidth=2,
                    markersize=4, zorder=4, alpha=0.85)

        if len(cycle) > 1:
            xs, ys = zip(*[to_xy(p) for p in cycle])
            ax.plot(xs, ys, "-o", color=CYCLE_COLOR, linewidth=2.5,
                    markersize=4, zorder=4, alpha=0.9)

        # Robot at end of path
        if display_path:
            rx, ry = to_xy(display_path[-1])
            ax.plot(rx, ry, "D", color="#FF6B00", markersize=9, zorder=6,
                    markeredgecolor="white", markeredgewidth=1.5)
    else:
        # Animation: colour prefix blue, cycle red, as steps accumulate
        if step < cycle_start_idx:
            # Still in prefix
            seg = display_path
            if len(seg) > 1:
                xs, ys = zip(*[to_xy(p) for p in seg])
                ax.plot(xs, ys, "-o", color=PATH_COLOR, linewidth=2,
                        markersize=4, zorder=4, alpha=0.85)
        else:
            prefix_seg = path[:cycle_start_idx + 1]
            cycle_seg  = display_path[cycle_start_idx:]
            if len(prefix_seg) > 1:
                xs, ys = zip(*[to_xy(p) for p in prefix_seg])
                ax.plot(xs, ys, "-o", color=PATH_COLOR, linewidth=2,
                        markersize=4, zorder=4, alpha=0.85)
            if len(cycle_seg) > 1:
                xs, ys = zip(*[to_xy(p) for p in cycle_seg])
                ax.plot(xs, ys, "-o", color=CYCLE_COLOR, linewidth=2.5,
                        markersize=4, zorder=4, alpha=0.9)

        if display_path:
            rx, ry = to_xy(display_path[-1])
            ax.plot(rx, ry, "D", color="#FF6B00", markersize=9, zorder=6,
                    markeredgecolor="white", markeredgewidth=1.5)


def make_legend():
    items = [
        mpatches.Patch(color=CELL_COLORS["zone_a"], label="Zone A"),
        mpatches.Patch(color=CELL_COLORS["zone_b"], label="Zone B"),
        mpatches.Patch(color=CELL_COLORS["zone_c"], label="Zone C"),
        mpatches.Patch(color=CELL_COLORS["danger"],  label="Danger"),
        mpatches.Patch(color=CELL_COLORS["goal"],    label="Goal"),
        mpatches.Patch(color=CELL_COLORS["obstacle"],label="Obstacle"),
        mpatches.Patch(color=PATH_COLOR,  label="Prefix path"),
        mpatches.Patch(color=CYCLE_COLOR, label="Cycle (repeating)"),
    ]
    return items


def render_static(grid: GridWorld, result: PlanResult, dpi: int = 120) -> Image.Image:
    """Render the full planned path as a static PIL image."""
    fig, ax = plt.subplots(figsize=(5, 5))
    _draw_grid(ax, grid, result.path, result.cycle_start_idx)
    ax.legend(handles=make_legend(), loc="upper right", fontsize=6,
              framealpha=0.85, ncol=2)
    title = "PLAN FOUND" if result.success else "NO PLAN"
    ax.set_title(title, fontsize=11, fontweight="bold",
                 color="#1A73E8" if result.success else "#CC0000")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).copy()


def render_animation(grid: GridWorld, result: PlanResult,
                     dpi: int = 100, fps: int = 4) -> Optional[str]:
    """
    Render an animated GIF of the robot following the path.
    Returns file path to a temp GIF, or None on failure.
    """
    if not result.success or not result.path:
        return None

    frames = []
    path = result.path
    n_steps = len(path)

    for step in range(n_steps):
        fig, ax = plt.subplots(figsize=(5, 5))
        _draw_grid(ax, grid, path, result.cycle_start_idx, step=step)
        phase = "CYCLE" if step >= result.cycle_start_idx else "PREFIX"
        ax.set_title(f"Step {step + 1}/{n_steps}  [{phase}]", fontsize=10)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        frames.append(Image.open(buf).copy())

    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
    tmp.close()
    frames[0].save(
        tmp.name,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=int(1000 / fps),
        optimize=False,
    )
    return tmp.name


def spec_table_html(result: PlanResult) -> str:
    rows = []
    for i, (name, reward) in enumerate(zip(result.spec_names, result.spec_rewards)):
        ok = i in result.satisfied
        icon  = "✅" if ok else "❌"
        color = "#1a7a1a" if ok else "#aa0000"
        rows.append(
            f"<tr>"
            f"<td style='padding:4px 10px;font-weight:bold;color:{color}'>{icon}</td>"
            f"<td style='padding:4px 10px;font-family:monospace'>{name}</td>"
            f"<td style='padding:4px 10px;text-align:right'>r = {reward:.0f}</td>"
            f"<td style='padding:4px 10px;color:{color};font-weight:bold'>"
            f"{'SATISFIED' if ok else 'VIOLATED'}</td>"
            f"</tr>"
        )
    header = (
        f"<div style='font-size:13px;margin-bottom:6px'>"
        f"<b>Total reward:</b> {result.total_reward:.0f} / {result.max_possible_reward:.0f}"
        f"</div>"
    )
    table = (
        "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
        "<thead><tr>"
        "<th style='padding:4px 10px'></th>"
        "<th style='padding:4px 10px;text-align:left'>Spec</th>"
        "<th style='padding:4px 10px;text-align:right'>Reward</th>"
        "<th style='padding:4px 10px;text-align:left'>Result</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    msg_color = "#1a7a1a" if result.success else "#aa0000"
    msg = f"<p style='color:{msg_color};font-weight:bold;margin-top:8px'>{result.message}</p>"
    return header + table + msg
