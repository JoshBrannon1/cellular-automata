"""Generates the log-log fit charts for the README from ca_headless_results.json."""

import json
import math
import matplotlib.pyplot as plt

with open("ca_headless_results.json") as f:
    data = json.load(f)

plt.rcParams.update({
    "font.size": 11,
    "axes.edgecolor": "#444444",
    "axes.labelcolor": "#222222",
    "text.color": "#222222",
    "xtick.color": "#444444",
    "ytick.color": "#444444",
})

# --- Chart 1: population growth, log-log ---
history = data["history"]
gens = [g for g, p, _ in history if g >= 1 and p > 0]
pops = [p for g, p, _ in history if g >= 1 and p > 0]
log_gens = [math.log(g) for g in gens]
log_pops = [math.log(p) for p in pops]

fit = data["power_law_fit"]
exp_fit = data["exponential_fit"]
slope, intercept, r2 = fit["exponent"], fit["intercept"], fit["r_squared"]

fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
ax.scatter(log_gens, log_pops, s=10, alpha=0.6, color="#2f6fed", label="measured (per generation)")
xline = [min(log_gens), max(log_gens)]
yline = [slope * x + intercept for x in xline]
ax.plot(xline, yline, color="#e0433d", linewidth=2,
        label=f"power-law fit: N ∝ g^{slope:.2f}  (R²={r2:.3f})")
ax.set_xlabel("log(generation)")
ax.set_ylabel("log(population)")
ax.set_title("Population growth, log-log")
ax.legend(loc="lower right", fontsize=9)
ax.grid(True, alpha=0.25)
fig.tight_layout()
fig.savefig("assets/growth_law_loglog.png")
plt.close(fig)

# --- Chart 2: box-counting dimension ---
bc = data["box_counting_dimension"]
eps_values = bc["eps_values"]
# recompute N(eps) points from history isn't stored per-eps in JSON beyond eps_values;
# re-derive log points the same way ca_headless_analysis.py printed them by reusing D fit
# (the raw N(eps) counts were printed to ca_run_log.txt -- parse them from there)
import re

box_points = []
pattern = re.compile(r"eps=\s*(\d+)\s+N\(eps\)=\s*(\d+)")
with open("ca_run_log.txt") as f:
    for line in f:
        m = pattern.search(line)
        if m:
            box_points.append((int(m.group(1)), int(m.group(2))))

log_inv_eps = [math.log(1.0 / e) for e, n in box_points]
log_n = [math.log(n) for e, n in box_points]
D, dim_r2 = bc["D"], bc["r_squared"]
# recover intercept via same least squares as harness (mean-based)
mean_x = sum(log_inv_eps) / len(log_inv_eps)
mean_y = sum(log_n) / len(log_n)
dim_intercept = mean_y - D * mean_x

fig2, ax2 = plt.subplots(figsize=(7, 5), dpi=150)
ax2.scatter(log_inv_eps, log_n, s=40, color="#2f6fed", zorder=3, label="measured box counts")
xline2 = [min(log_inv_eps), max(log_inv_eps)]
yline2 = [D * x + dim_intercept for x in xline2]
ax2.plot(xline2, yline2, color="#e0433d", linewidth=2,
         label=f"fit: D = {D:.2f}  (R²={dim_r2:.3f})")
ax2.set_xlabel("log(1/ε)")
ax2.set_ylabel("log N(ε)")
ax2.set_title("Box-counting dimension, final grid")
ax2.legend(loc="lower right", fontsize=9)
ax2.grid(True, alpha=0.25)
fig2.tight_layout()
fig2.savefig("assets/box_counting_loglog.png")
plt.close(fig2)

print("Wrote assets/growth_law_loglog.png and assets/box_counting_loglog.png")
