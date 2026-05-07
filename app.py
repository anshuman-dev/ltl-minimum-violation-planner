"""
Minimum-Violation LTL Planning — Interactive Demo
Reproduces: Tumova et al., "Minimum-Violation LTL Planning with Conflicting
Specifications", ACC 2013 (arXiv:1303.3679)

Change spec priorities → watch the plan change to satisfy the highest-priority rules.
"""

import gradio as gr

from src.grid_world import make_scenario, GridWorld, CELL_PROPS
from src.automata import parse_spec, BuchiAut
from src.planner import plan
from src.visualize import render_static, render_animation, spec_table_html


# ── Preset spec bundles per scenario ─────────────────────────────────────────

SCENARIO_SPECS = {
    "road": [
        ("G(!danger)",  "Never cross double line (danger zone)", 80),
        ("GF(zone_a)",  "Periodically visit pickup zone A",      50),
        ("GF(zone_b)",  "Periodically visit dropoff zone B",     30),
        ("F(goal)",     "Eventually reach the goal",             10),
    ],
    "patrol": [
        ("G(!danger)",  "Stay away from danger zones",    100),
        ("GF(zone_a)",  "Patrol zone A repeatedly",        60),
        ("GF(zone_b)",  "Patrol zone B repeatedly",        40),
    ],
    "rescue": [
        ("G(!danger)",  "Avoid hazardous areas",           90),
        ("F(zone_a)",   "Reach survivor site A",           70),
        ("F(zone_b)",   "Reach survivor site B",           50),
        ("GF(zone_c)",  "Return to base (zone C) always",  20),
    ],
}

SCENARIO_DESCRIPTIONS = {
    "road": "🚗 Road network — robot must navigate around a danger zone to reach pickup/dropoff areas and a destination.",
    "patrol": "🏭 Warehouse patrol — robot periodically covers two inspection zones while avoiding a hazardous area.",
    "rescue": "🚁 Rescue mission — robot must reach two survivor sites and periodically return to base, avoiding hazards.",
}


def run_planning(scenario, r0, r1, r2, r3, animate):
    grid = make_scenario(scenario)
    specs_raw = SCENARIO_SPECS[scenario]
    n_specs = len(specs_raw)
    rewards_input = [r0, r1, r2, r3][:n_specs]

    automata = []
    rewards  = []
    for i, (formula, _, _) in enumerate(specs_raw):
        try:
            aut = parse_spec(formula, label=formula)
            automata.append(aut)
            rewards.append(float(rewards_input[i]))
        except ValueError as e:
            return None, None, f"<p style='color:red'>Error: {e}</p>"

    result = plan(grid, automata, rewards)
    table_html = spec_table_html(result)

    static_img = render_static(grid, result)

    if animate and result.success:
        gif_path = render_animation(grid, result, fps=3)
        return static_img, gif_path, table_html
    else:
        return static_img, None, table_html


def update_scenario_ui(scenario):
    specs = SCENARIO_SPECS[scenario]
    desc  = SCENARIO_DESCRIPTIONS[scenario]
    n = len(specs)

    updates = []
    for i in range(4):
        if i < n:
            _, label, default_r = specs[i]
            updates.append(gr.update(label=label, value=default_r, visible=True))
        else:
            updates.append(gr.update(visible=False))

    return [gr.update(value=f"**{desc}**")] + updates


# ── Build the Gradio UI ───────────────────────────────────────────────────────

with gr.Blocks(title="Minimum-Violation LTL Planner", theme=gr.themes.Soft()) as demo:

    gr.Markdown("""
# Minimum-Violation LTL Planning
**Reproducing:** Tumova et al., *"Minimum-Violation LTL Planning with Conflicting Specifications"*, ACC 2013

When robot specs conflict, instead of failing, this planner finds the path that satisfies
the **highest-priority** rules and minimally violates the rest.

> **Try it:** drag the reward sliders to swap priorities — watch the planned path change.
""")

    with gr.Row():
        with gr.Column(scale=1):
            scenario_dd = gr.Dropdown(
                choices=["road", "patrol", "rescue"],
                value="road",
                label="Scenario",
            )
            scenario_desc = gr.Markdown("**Loading...**")

            gr.Markdown("### Spec Priorities (higher reward = harder to violate)")

            sliders = []
            default_specs = SCENARIO_SPECS["road"]
            for i in range(4):
                visible = i < len(default_specs)
                _, lbl, val = default_specs[i] if visible else ("", f"Spec {i+1}", 10)
                s = gr.Slider(
                    minimum=0, maximum=200, step=5,
                    value=val, label=lbl,
                    visible=visible,
                )
                sliders.append(s)

            animate_cb = gr.Checkbox(label="Generate animation (GIF)", value=True)
            plan_btn   = gr.Button("▶  Synthesize Plan", variant="primary")

            gr.Markdown("""
---
**How it works:**
1. Each spec φᵢ becomes a Büchi automaton
2. Product automaton = grid × aut₁ × aut₂ × ...
3. SCCs with accepting states for each spec are found
4. Max-reward SCC is chosen → lasso path reconstructed

🔵 Prefix path &nbsp;&nbsp; 🔴 Repeating cycle &nbsp;&nbsp; 🟣 Start &nbsp;&nbsp; 🟠 Robot
""")

        with gr.Column(scale=2):
            grid_img  = gr.Image(label="Planned Path", type="pil", height=420)
            anim_img  = gr.Image(label="Animation (GIF)", type="filepath", height=420)
            result_md = gr.HTML(label="Spec Satisfaction")

    # ── Event handlers ────────────────────────────────────────────────────────

    scenario_dd.change(
        fn=update_scenario_ui,
        inputs=[scenario_dd],
        outputs=[scenario_desc] + sliders,
    )

    plan_btn.click(
        fn=run_planning,
        inputs=[scenario_dd] + sliders + [animate_cb],
        outputs=[grid_img, anim_img, result_md],
    )

    # Run on load with default scenario
    demo.load(
        fn=lambda: update_scenario_ui("road"),
        outputs=[scenario_desc] + sliders,
    )

    demo.load(
        fn=lambda: run_planning("road", 80, 50, 30, 10, False),
        outputs=[grid_img, anim_img, result_md],
    )


if __name__ == "__main__":
    demo.launch()
