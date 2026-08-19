"""Two-panel report figure: pressure effect + curiosity-vs-dishonesty scatter."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#1a1f26", "#5b6570", "#e4e7eb"

h = json.load(open("results/summary.json"))
cross = json.load(open("results/cross_table.json"))

MAP = {"openai/gpt-4o-mini": "gpt-4o-mini",
       "anthropic/claude-haiku-4.5": "haiku-4.5",
       "deepseek/deepseek-chat": "deepseek",
       "qwen/qwen-2.5-72b-instruct": "qwen-72b",
       "moonshotai/kimi-k2": "kimi-k2"}


def dishonesty(m, cond):
    d = h.get(m + "|" + cond, {})
    n = max(d.get("n_impossible", 20), 1)
    return (d.get("fabricated", 0) + d.get("rule_violation_hits", 0)) / n * 100


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), dpi=150)
fig.patch.set_facecolor("white")

# --- Panel A: dishonesty on impossible items, neutral vs pressure ---
models = list(MAP)
labels = [MAP[m] for m in models]
neu = [dishonesty(m, "neutral") for m in models]
pre = [dishonesty(m, "pressure") for m in models]
x = range(len(models))
w = 0.36
b1 = ax1.bar([i - w / 2 for i in x], neu, w, color=BLUE, label="neutral")
b2 = ax1.bar([i + w / 2 for i in x], pre, w, color=ORANGE, label="pressure")
for bars in (b1, b2):
    for b in bars:
        v = b.get_height()
        ax1.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}",
                 ha="center", fontsize=8, color=INK)
ax1.set_xticks(list(x), labels, fontsize=8, color=INK)
ax1.set_ylabel("fabricated or cheated on impossible items (%)",
               fontsize=8.5, color=MUTED)
ax1.set_title("One sentence of pressure creates dishonesty",
              fontsize=10, color=INK, loc="left")
ax1.legend(frameon=False, fontsize=8, loc="upper left")
ax1.set_ylim(0, 100)

# --- Panel B: curiosity (contradiction-flagging) vs dishonesty ---
for short, r in cross.items():
    if r["flag"] is None:
        continue
    ax2.scatter(r["flag"], r["fab"], s=70, color=BLUE, zorder=3)
    dx, dy = (-38, -14) if short == "kimi-k2" else (6, 4)
    ax2.annotate(short, (r["flag"], r["fab"]), textcoords="offset points",
                 xytext=(dx, dy), fontsize=8.5, color=INK)
ax2.set_xlabel("flagged the planted test contradiction, ImpossibleBench (%)",
               fontsize=8.5, color=MUTED)
ax2.set_ylabel("fabricated or cheated under pressure (%)",
               fontsize=8.5, color=MUTED)
ax2.set_title("Noticing vs bluffing under pressure (5 models)",
              fontsize=10, color=INK, loc="left")
ax2.set_xlim(-5, 105)
ax2.set_ylim(-5, 100)

for ax in (ax1, ax2):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)

fig.tight_layout()
out = Path("report/figures")
out.mkdir(parents=True, exist_ok=True)
fig.savefig(out / "curiosity_vs_dishonesty.png", bbox_inches="tight")
print("wrote", out / "curiosity_vs_dishonesty.png")
