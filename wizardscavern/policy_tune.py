"""
CMA-ES tuner for smart_policy's PolicyConfig.

Goal: find PolicyConfig values that push agents deeper while keeping the
3000T survival rate inside a target band (default 3-8 alive / 60), so
the policy is competent but the game still feels roguelike-hard.

Usage:
    python3 -m wizardscavern.policy_tune --mode quick
    python3 -m wizardscavern.policy_tune --mode standard --out best.json
    python3 -m wizardscavern.policy_tune --mode thorough --seeds 30

Modes (pop=lambda, gen=generations, eval=(seeds, turns)):
    quick     pop=10 gen=15 eval=(20, 2000)   ~30 min
    standard  pop=15 gen=25 eval=(30, 2500)   ~2-3 hrs
    thorough  pop=20 gen=40 eval=(60, 3000)   ~6-12 hrs

Final winners are always validated on the full 60x3000 grid before
being declared the new default. The validation result is what gets
reported, not the cheap-eval fitness.
"""

import argparse
import json
import multiprocessing as mp
import os
import random
import sys
import time
from dataclasses import asdict
from pathlib import Path

import cma
import numpy as np

# Avoid importing the full game stack at module load time -- the worker
# pool needs a clean import on each fork.
from wizardscavern.policy_config import (
    FIELD_BOUNDS, PolicyConfig, config_to_vector, set_active_config,
    vector_field_order, vector_to_config,
)


# ----- Single-run evaluation -----

def _run_one(args):
    """Worker: run one (seed, race) episode with the given config dict.

    Returns dict with summary metrics. Designed to be picklable for mp.Pool.
    """
    seed, race, cfg_dict, turns = args
    # Import inside the worker to avoid sharing module state across forks.
    from wizardscavern import game_state as gs
    from wizardscavern.playtest_harness import new_game, smart_policy
    from wizardscavern.policy_config import PolicyConfig, set_active_config

    set_active_config(PolicyConfig.from_dict(cfg_dict))
    sess = new_game(seed=seed, race=race, starter_pack=True)
    rng = random.Random(seed)
    obs = sess.observe()
    max_floor_reached = obs["player"]["floor"]
    for _ in range(turns):
        if sess.is_done():
            break
        action = smart_policy(obs, rng, use_lantern=True)
        obs = sess.step(action)
        f = obs["player"]["floor"]
        if f > max_floor_reached:
            max_floor_reached = f

    p = obs["player"]
    return {
        "seed": seed,
        "race": race,
        "alive": bool(obs.get("alive")),
        "max_floor": max_floor_reached,
        "final_floor": p["floor"],
        "final_hp": p["hp"],
        "final_hunger": p["hunger"],
        "level": p.get("level", 1),
        "turns": sess.turn,
    }


# ----- Grid evaluation (parallel) -----

def evaluate_config(cfg, seeds, turns, races=("dwarf", "elf", "human"),
                    pool=None):
    """Run a grid of seeds x races against cfg. Returns per-run records."""
    cfg_dict = cfg.to_dict()
    args_list = [
        (seed, race, cfg_dict, turns)
        for seed in seeds
        for race in races
    ]
    if pool is None:
        results = [_run_one(a) for a in args_list]
    else:
        results = pool.map(_run_one, args_list)
    return results


# ----- Fitness function -----

def fitness(results, target_alive_lo, target_alive_hi):
    """Lower is better (CMA-ES minimizes).

    Components:
      - mean_max_floor (maximize) -> negate
      - alive_count band: 0 penalty inside [lo, hi], quadratic outside
      - small variance penalty to discourage all-or-nothing tunings
    """
    n = len(results)
    mean_floor = sum(r["max_floor"] for r in results) / n
    alive_count = sum(1 for r in results if r["alive"])
    var_floor = float(np.var([r["max_floor"] for r in results]))

    # Depth term: each extra floor is worth ~1.0 fitness.
    depth_term = -mean_floor

    # Survival band penalty.
    if alive_count < target_alive_lo:
        survival_penalty = 0.5 * (target_alive_lo - alive_count) ** 2
    elif alive_count > target_alive_hi:
        survival_penalty = 0.5 * (alive_count - target_alive_hi) ** 2
    else:
        survival_penalty = 0.0

    # Mild variance penalty (high variance = lucky outliers, not skill).
    var_penalty = 0.05 * min(var_floor, 8.0)

    return depth_term + survival_penalty + var_penalty


def summary(results):
    n = len(results)
    alive = sum(1 for r in results if r["alive"])
    mean_floor = sum(r["max_floor"] for r in results) / n
    f4_plus = sum(1 for r in results if r["max_floor"] >= 4)
    f6_plus = sum(1 for r in results if r["max_floor"] >= 6)
    return {
        "n": n,
        "alive": alive,
        "mean_max_floor": round(mean_floor, 3),
        "f4_plus": f4_plus,
        "f6_plus": f6_plus,
    }


# ----- CMA-ES driver -----

MODES = {
    "quick":    dict(pop=10, gen=15, seeds=20, turns=2000),
    "standard": dict(pop=15, gen=25, seeds=30, turns=2500),
    "thorough": dict(pop=20, gen=40, seeds=60, turns=3000),
}


def normalize_to_unit(cfg_vec):
    """Map config vector to [0, 1] in each dimension via FIELD_BOUNDS."""
    out = []
    for name, v in zip(vector_field_order(), cfg_vec):
        lo, hi = FIELD_BOUNDS[name]
        out.append((v - lo) / max(1e-9, hi - lo))
    return out


def denormalize_from_unit(unit_vec):
    """Map [0, 1] back to FIELD_BOUNDS range. Clamped via vector_to_config."""
    out = []
    for name, u in zip(vector_field_order(), unit_vec):
        lo, hi = FIELD_BOUNDS[name]
        out.append(lo + u * (hi - lo))
    return out


def run_cma(args):
    cfg0 = PolicyConfig()
    x0_unit = normalize_to_unit(config_to_vector(cfg0))
    mode = MODES[args.mode]
    seeds = list(range(args.seed_base, args.seed_base + mode["seeds"]))

    es = cma.CMAEvolutionStrategy(
        x0_unit,
        0.20,  # initial sigma in unit space
        {
            "popsize": mode["pop"],
            "maxiter": mode["gen"],
            "bounds": [[0.0] * len(x0_unit), [1.0] * len(x0_unit)],
            "verbose": -9,
            "seed": args.cma_seed,
        },
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pool = mp.Pool(processes=args.workers) if args.workers > 1 else None
    try:
        best_overall = None
        gen = 0
        t0 = time.time()
        log_lines = []
        while not es.stop() and gen < mode["gen"]:
            gen += 1
            xs_unit = es.ask()
            fitnesses = []
            gen_t0 = time.time()
            for x_unit in xs_unit:
                cfg = vector_to_config(denormalize_from_unit(x_unit))
                results = evaluate_config(
                    cfg, seeds, mode["turns"], pool=pool,
                )
                f = fitness(results, args.target_lo, args.target_hi)
                fitnesses.append(f)
                s = summary(results)
                if best_overall is None or f < best_overall["fitness"]:
                    best_overall = {
                        "fitness": f,
                        "config": cfg.to_dict(),
                        "summary": s,
                        "generation": gen,
                    }
                    (out_dir / "best_so_far.json").write_text(
                        json.dumps(best_overall, indent=2, sort_keys=True)
                    )
            es.tell(xs_unit, fitnesses)
            gen_elapsed = time.time() - gen_t0
            line = (
                f"gen {gen:2d}/{mode['gen']:2d} "
                f"best_f={min(fitnesses):+.3f} "
                f"mean_f={sum(fitnesses) / len(fitnesses):+.3f} "
                f"overall_best_f={best_overall['fitness']:+.3f} "
                f"alive={best_overall['summary']['alive']} "
                f"floor={best_overall['summary']['mean_max_floor']} "
                f"gen_t={gen_elapsed:.1f}s"
            )
            print(line, flush=True)
            log_lines.append(line)
            (out_dir / "tune.log").write_text("\n".join(log_lines))
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    total_elapsed = time.time() - t0
    print(f"\nCMA-ES complete in {total_elapsed:.1f}s "
          f"({gen} generations).")
    print(f"Best fitness: {best_overall['fitness']:+.3f}")
    print(f"Best summary: {best_overall['summary']}")

    # Final validation on a clean 60x3000 grid using NEW seeds (avoid
    # overfitting to the training seed set).
    val_seeds = list(range(args.seed_base + 10000,
                           args.seed_base + 10000 + 20))
    print(f"\nValidating winner on seeds {val_seeds[0]}-{val_seeds[-1]} "
          f"x 3 races x 3000T ...")
    if args.workers > 1:
        val_pool = mp.Pool(processes=args.workers)
    else:
        val_pool = None
    try:
        val_results = evaluate_config(
            PolicyConfig.from_dict(best_overall["config"]),
            val_seeds, 3000, pool=val_pool,
        )
    finally:
        if val_pool is not None:
            val_pool.close()
            val_pool.join()
    val_s = summary(val_results)
    print(f"Validation: {val_s}")

    out = {
        "best": best_overall,
        "validation": {
            "seeds_range": [val_seeds[0], val_seeds[-1]],
            "turns": 3000,
            "summary": val_s,
        },
        "mode": args.mode,
        "mode_params": mode,
        "target_band": [args.target_lo, args.target_hi],
        "elapsed_sec": round(total_elapsed, 1),
    }
    out_path = out_dir / args.out
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(f"Wrote {out_path}")

    # Also write the bare config so it can be drop-in loaded.
    cfg_path = out_dir / "best_config.json"
    cfg_path.write_text(
        json.dumps(best_overall["config"], indent=2, sort_keys=True)
    )
    print(f"Wrote {cfg_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=list(MODES), default="quick")
    ap.add_argument("--seed-base", type=int, default=1)
    ap.add_argument("--target-lo", type=int, default=3)
    ap.add_argument("--target-hi", type=int, default=8)
    ap.add_argument("--cma-seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 1))
    ap.add_argument("--out-dir", default="/tmp/policy_tune")
    ap.add_argument("--out", default="tune_result.json")
    args = ap.parse_args()
    run_cma(args)


if __name__ == "__main__":
    main()
