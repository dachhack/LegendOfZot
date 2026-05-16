"""
PolicyConfig: tunable knobs for smart_policy.

Each field captures a magic number that was hand-set in playtest_harness.py
across builds 280-321. CMA-ES tuning (policy_tune.py) treats these as a
genome to optimize for survival depth + alive-count fitness while keeping
the survival rate inside a roguelike-appropriate band.

GAME BALANCE knobs (hunger decay rate, starter pack contents, meat drop
rate, monster stats) are NOT tuned here -- they're set by hand for the
desired difficulty target. This config covers only the playtest AGENT's
decision-making thresholds.
"""

from dataclasses import dataclass, field, asdict
import json


@dataclass
class PolicyConfig:
    # --- Food / hunger triggers ---
    eat_hunger_threshold: int = 50
    # Eat when hunger < this. Rations are 50 nutrition so 50 is near-optimal
    # for waste-free consumption; lower = more well-fed time but more food
    # waste; higher = more eat-cycles but tighter food clock.

    urgent_meat_rot_threshold: int = 20
    # Eat raw meat about-to-rot when rot_timer <= this. Lower = waste fresh
    # meat protecting against rot; higher = lose meat to rot.

    starving_threshold: int = 30
    # `starving` flag fires when hunger <= this AND no food in bag. Triggers
    # combat-mode flee-from-inedible override.

    # --- Heal / potion triggers ---
    heal_hp_critical_pct: float = 0.30
    # Drink heal potion at this HP fraction (highest-priority self-care).

    heal_hp_preemptive_pct: float = 0.80
    # Pre-emptive heal at this HP fraction when an M is adjacent (before
    # combat absorbs the next hit).

    combat_heal_pot_pct: float = 0.50
    # In combat_mode, open inventory to drink heal pot at this HP fraction.

    combat_heal_spell_pct: float = 0.55
    # In combat_mode, queue cast at this HP fraction if heal spell known.

    buff_potion_hp_low: float = 0.60
    # Pre-combat buff potion lower HP gate.

    buff_potion_hp_high: float = 0.95
    # Pre-combat buff potion upper HP gate.

    # --- Resource pressure ---
    resource_hunger_threshold: int = 60
    # `resources_pressing` fires when hunger < this. Tightens floor exit gates.

    resource_fuel_threshold: int = 15
    # `resources_pressing` fires when fuel_total < this.

    # --- Floor / exploration timing ---
    floor_stuck_turns: int = 300
    # Force descend tier when turns_on_floor > this.

    high_coverage_threshold: int = 50
    # Coverage % at which `high_coverage_descend` fires. Build 315 lowered
    # 90 -> 50 after grid showed 90% was dead code.

    min_kills_floor_base: int = 3
    # Minimum kills required at F1 (and floor of the min-kills curve).

    min_kills_floor_scale: int = 2
    # Per-floor kill increment: min_kills = min(12, max(base, pc_z * scale + 1)).

    wedge_visit_count: int = 6
    # current_tile_visits >= this triggers wedge Hail Mary.

    # --- Combat threat assessment ---
    flee_level_gap_general: int = 2
    # Flee general monsters when m_level > pc_level + this.

    flee_level_gap_undead: int = 0
    # Flee undead when m_level > pc_level + this (0 = flee at +1).

    flee_level_gap_elite: int = -1
    # Flee elite undead when m_level >= pc_level + this + 1 (= -1 means parity).

    flee_hp_bag_ratio: float = 2.0
    # Flee when m_max_hp > this * pc_max_hp.

    spell_use_prob: float = 0.90
    # In combat: rng.random() < this triggers spell cast (vs melee attack).

    attack_vs_flee_prob: float = 0.92
    # In combat fallback: rng.random() < this triggers attack (vs flee).

    # --- Vendor gates ---
    heal_pot_vendor_threshold: int = 2
    # wants_vendor fires when healing_count < this (and gold >= 50).

    # ----- serialization -----
    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        # Tolerate missing keys by falling back to dataclass defaults.
        defaults = cls()
        merged = {**defaults.to_dict(), **(d or {})}
        # Cast numeric types correctly (JSON loses int/float distinction).
        out = {}
        for k, v in merged.items():
            default_v = getattr(defaults, k)
            if isinstance(default_v, int) and not isinstance(default_v, bool):
                out[k] = int(round(v))
            else:
                out[k] = float(v)
        return cls(**out)

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, s):
        return cls.from_dict(json.loads(s))

    @classmethod
    def load(cls, path):
        with open(path, "r") as f:
            return cls.from_json(f.read())

    def save(self, path):
        with open(path, "w") as f:
            f.write(self.to_json())


# Field bounds for CMA-ES. Each entry: (min, max). Order matches
# vector_field_order() so the CMA-ES genome <-> PolicyConfig mapping
# is deterministic.
FIELD_BOUNDS = {
    "eat_hunger_threshold":      (30, 75),
    "urgent_meat_rot_threshold": (5, 40),
    "starving_threshold":        (10, 50),
    "heal_hp_critical_pct":      (0.10, 0.50),
    "heal_hp_preemptive_pct":    (0.50, 0.95),
    "combat_heal_pot_pct":       (0.25, 0.70),
    "combat_heal_spell_pct":     (0.30, 0.70),
    "buff_potion_hp_low":        (0.40, 0.80),
    "buff_potion_hp_high":       (0.80, 1.00),
    "resource_hunger_threshold": (40, 80),
    "resource_fuel_threshold":   (5, 40),
    "floor_stuck_turns":         (100, 500),
    "high_coverage_threshold":   (30, 80),
    "min_kills_floor_base":      (1, 8),
    "min_kills_floor_scale":     (0, 4),
    "wedge_visit_count":         (3, 12),
    "flee_level_gap_general":    (0, 5),
    "flee_level_gap_undead":     (-2, 3),
    "flee_level_gap_elite":      (-3, 1),
    "flee_hp_bag_ratio":         (1.0, 3.5),
    "spell_use_prob":            (0.50, 1.00),
    "attack_vs_flee_prob":       (0.70, 1.00),
    "heal_pot_vendor_threshold": (1, 5),
}


def vector_field_order():
    """Deterministic order for CMA-ES genome <-> PolicyConfig conversion."""
    return list(FIELD_BOUNDS.keys())


def config_to_vector(cfg):
    """PolicyConfig -> list[float] in vector_field_order()."""
    return [float(getattr(cfg, name)) for name in vector_field_order()]


def vector_to_config(vec):
    """list[float] -> PolicyConfig, clamping to FIELD_BOUNDS first."""
    out = {}
    for name, v in zip(vector_field_order(), vec):
        lo, hi = FIELD_BOUNDS[name]
        out[name] = max(lo, min(hi, v))
    return PolicyConfig.from_dict(out)


# Mutable module-level config. smart_policy reads from this. Tests /
# CMA-ES drivers set it via set_active_config(...) before each grid run.
_ACTIVE_CONFIG = PolicyConfig()


def active_config():
    return _ACTIVE_CONFIG


def set_active_config(cfg):
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = cfg
