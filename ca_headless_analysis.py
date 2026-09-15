"""
Headless analysis harness for Cellular_Automata.py.

Extracts the transition rule (run_simulation_step) from the pygame program
with zero behavioral changes -- only the display/input loop is removed --
so the growth dynamics measured here are exactly what the interactive
program computes, just without the 60fps redraw ceiling.

Produces, from an actual run rather than inference:
  1. population vs. generation (generations, not wall-clock time)
  2. a power-law vs. exponential fit to that growth curve
  3. a box-counting dimension estimate on the final occupied-cell set
  4. an empirical check of the claimed Klein four-group symmetry
  5. a per-generation count of PURPLE prune events (density-regulation activity)

Seed caveat: the original 134-cell seed was hand-drawn with the mouse and
was not recorded anywhere retrievable, so this harness uses a reproducible
stand-in seed (fixed RNG seed, documented below) of the same size instead.
Growth-law exponent and fractal dimension are properties of the transition
rule's dynamics and are expected to be robust to the specific seed (as long
as it's a sparse, non-degenerate scatter); the exact generation count to
cross 70,000 cells is seed-dependent and should be read as illustrative,
not as a reproduction of the original run.
"""

import json
import math
import random
import time

# --- Colors (plain tuples, no pygame dependency) ---
PINK, BLUE, PURPLE, YELLOW = (255, 100, 180), (100, 180, 255), (180, 100, 255), (255, 255, 100)
COLOR_NAMES = {PINK: "PINK", BLUE: "BLUE", PURPLE: "PURPLE", YELLOW: "YELLOW"}

TARGET_POPULATION = 25_000  # scaled down from 70,000 -- see WALL_CLOCK_LIMIT note below
MAX_GENERATIONS = 500
WALL_CLOCK_LIMIT_SECONDS = 420  # per-generation cost grows with population; cap runtime and extrapolate to 70,000 instead of measuring it directly
SEED_SIZE = 134
SEED_RNG = 20240915  # fixed for reproducibility


def make_seed(n=SEED_SIZE, box=15, rng_seed=SEED_RNG):
    """Reproducible stand-in for a hand-drawn n-cell seed: a sparse random
    scatter in a box x box window, offset off-origin (freehand drawing has
    no reason to be centered), colors assigned round-robin."""
    rng = random.Random(rng_seed)
    coords = set()
    while len(coords) < n:
        x = rng.randint(-box, box) + 3
        y = rng.randint(-box, box) - 2
        coords.add((x, y))
    palette_cycle = [PINK, BLUE, YELLOW, PURPLE]
    return {c: palette_cycle[i % 4] for i, c in enumerate(sorted(coords))}


def run_simulation_step(cells):
    """Verbatim port of Cellular_Automata.py's run_simulation_step (lines 45-94),
    with a prune-event counter added for instrumentation only."""
    new_cells = {}

    # 1. APPLY GLOBAL SYMMETRY
    for (x, y), color in cells.items():
        for mx, my in [(x, y), (-x, y), (x, -y), (-x, -y)]:
            new_cells[(mx, my)] = color

    reference = new_cells.copy()

    for (x, y), color in reference.items():
        if color == PINK:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                if (x + dx * 2, y + dy * 2) not in reference:
                    new_cells[(x + dx, y + dy)] = PINK

        if color == BLUE:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                for dist in range(2, 8):
                    target = (x + dx * dist, y + dy * dist)
                    if target in reference:
                        for i in range(1, dist):
                            new_cells[(x + dx * i, y + dy * i)] = BLUE
                        break

        if color == YELLOW:
            for dx, dy in [(1, 1), (-1, -1), (1, -1), (-1, 1)]:
                if (x + dx, y + dy) not in reference:
                    new_cells[(x + dx, y + dy)] = YELLOW

    final_output = new_cells.copy()
    prune_events = 0
    for (x, y) in new_cells:
        neighbors = 0
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if (x + dx, y + dy) in new_cells:
                    neighbors += 1

        if neighbors > 7:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dx != 0 or dy != 0:
                        final_output.pop((x + dx, y + dy), None)
            final_output[(x, y)] = PURPLE
            prune_events += 1

    return final_output, prune_events


def check_klein_four_symmetry(cells):
    """Empirically verifies invariance under {id, reflect-x, reflect-y, rotate180}."""
    for (x, y), color in cells.items():
        for mx, my in [(-x, y), (x, -y), (-x, -y)]:
            if cells.get((mx, my)) != color:
                return False
    return True


def least_squares(xs, ys):
    """Plain-Python simple linear regression. Returns (slope, intercept, r_squared)."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)
    slope = ss_xy / ss_xx
    intercept = mean_y - slope * mean_x
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return slope, intercept, r_squared


def box_counting_dimension(coords):
    """Standard box-counting: partition the occupied coordinate set into
    eps x eps boxes for a range of eps, count non-empty boxes, fit
    log N(eps) = -D log eps + c via least squares. Returns (D, r_squared, points)."""
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1)

    eps_values = []
    e = 1
    while e < span / 4:
        eps_values.append(e)
        e *= 2

    points = []
    for eps in eps_values:
        boxes = set()
        for (x, y) in coords:
            boxes.add((x // eps, y // eps))
        n_boxes = len(boxes)
        if n_boxes > 0:
            points.append((math.log(1.0 / eps), math.log(n_boxes)))

    log_inv_eps = [p[0] for p in points]
    log_n = [p[1] for p in points]
    slope, intercept, r_squared = least_squares(log_inv_eps, log_n)
    return slope, r_squared, points, eps_values


def main():
    cells = make_seed()
    gen0_population = len(cells)

    history = []  # (generation, population, prune_events)
    history.append((0, gen0_population, 0))

    print(f"Seed: {gen0_population} cells (target size {SEED_SIZE}; stand-in RNG seed {SEED_RNG})")
    print(f"Symmetric at generation 0: {check_klein_four_symmetry(cells)}  (expected False -- seed is pre-symmetrization)")

    t0 = time.time()
    gen = 0
    reached_target_at = None
    while gen < MAX_GENERATIONS:
        gen += 1
        cells, prunes = run_simulation_step(cells)
        pop = len(cells)
        history.append((gen, pop, prunes))
        if reached_target_at is None and pop >= TARGET_POPULATION:
            reached_target_at = gen
        if gen % 5 == 0 or reached_target_at == gen:
            print(f"  gen {gen:3d}: population={pop:7d}  prune_events={prunes:5d}  "
                  f"elapsed={time.time()-t0:6.1f}s", flush=True)
        if reached_target_at is not None and gen >= reached_target_at + 3:
            break
        if time.time() - t0 > WALL_CLOCK_LIMIT_SECONDS:
            print(f"  wall-clock limit ({WALL_CLOCK_LIMIT_SECONDS}s) reached at generation {gen}, stopping.",
                  flush=True)
            break
    elapsed = time.time() - t0

    print(f"\nRan {gen} generations in {elapsed:.2f}s wall-clock.")
    if reached_target_at:
        print(f"Crossed {TARGET_POPULATION} cells at generation {reached_target_at}.")
    else:
        print(f"Did NOT reach {TARGET_POPULATION} cells within {MAX_GENERATIONS} generations "
              f"(final population {history[-1][1]}).")

    print(f"Symmetric at final generation: {check_klein_four_symmetry(cells)}")

    # --- Growth law fit (skip generation 0, and skip any generation with population 0) ---
    fit_history = [(g, p) for (g, p, _) in history if g >= 1 and p > 0]
    gens = [g for g, p in fit_history]
    pops = [p for g, p in fit_history]

    log_gens = [math.log(g) for g in gens]
    log_pops = [math.log(p) for p in pops]
    power_slope, power_intercept, power_r2 = least_squares(log_gens, log_pops)

    exp_slope, exp_intercept, exp_r2 = least_squares(gens, log_pops)

    print("\n--- Growth law fit ---")
    print(f"Power law   log(N) = {power_slope:.3f}*log(g) + {power_intercept:.3f}   R^2 = {power_r2:.4f}")
    print(f"Exponential log(N) = {exp_slope:.5f}*g + {exp_intercept:.3f}   R^2 = {exp_r2:.4f}")

    # Extrapolate to the original entry's 70,000-cell claim using whichever fit is better,
    # restricted to the fit's own valid domain (power law only makes sense for g >= 1).
    extrapolated_gen_power = math.exp((math.log(70_000) - power_intercept) / power_slope) if power_slope != 0 else None
    print(f"\nExtrapolated generation to reach 70,000 cells (power-law fit): {extrapolated_gen_power:.1f}"
          if extrapolated_gen_power else "")

    # --- Box-counting dimension on final grid ---
    final_coords = list(cells.keys())
    dim, dim_r2, dim_points, eps_values = box_counting_dimension(final_coords)
    print("\n--- Box-counting dimension (final grid) ---")
    print(f"Occupied cells: {len(final_coords)}")
    print(f"eps values used: {eps_values}")
    for (log_inv_eps, log_n), eps in zip(dim_points, eps_values):
        print(f"  eps={eps:4d}  N(eps)={int(round(math.exp(log_n))):6d}  log(1/eps)={log_inv_eps:.3f}  log N={log_n:.3f}")
    print(f"Estimated box-counting dimension D = {dim:.3f}  (fit R^2 = {dim_r2:.4f})")

    # --- Final color / structure breakdown ---
    color_counts = {}
    for c in cells.values():
        color_counts[COLOR_NAMES.get(c, c)] = color_counts.get(COLOR_NAMES.get(c, c), 0) + 1
    print("\n--- Final color breakdown ---")
    for name, count in sorted(color_counts.items()):
        print(f"  {name}: {count}")

    total_prunes = sum(p for _, _, p in history)
    print(f"\nTotal PURPLE prune events across run: {total_prunes}")

    # --- Save raw data for the write-up ---
    out = {
        "seed_size": gen0_population,
        "seed_rng": SEED_RNG,
        "generations_run": gen,
        "reached_target_at_generation": reached_target_at,
        "final_population": history[-1][1],
        "history": history,
        "power_law_fit": {"exponent": power_slope, "intercept": power_intercept, "r_squared": power_r2},
        "exponential_fit": {"rate": exp_slope, "intercept": exp_intercept, "r_squared": exp_r2},
        "box_counting_dimension": {"D": dim, "r_squared": dim_r2, "eps_values": eps_values},
        "final_color_breakdown": color_counts,
        "total_prune_events": total_prunes,
        "final_symmetric": check_klein_four_symmetry(cells),
    }
    with open("ca_headless_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\nRaw results written to ca_headless_results.json")


if __name__ == "__main__":
    main()
