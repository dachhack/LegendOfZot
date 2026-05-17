"""
Per-floor guaranteed item supply.

Each floor at generation time gets a fixed budget of guaranteed items
distributed across the vendor inventory and a chest-bonus queue. Chests
opened on the floor pop one bonus item from the queue IN ADDITION TO
their normal RNG roll, until the queue is empty. The vendor inventory
gets supplemental items appended at vendor instantiation.

This is a "supply floor" that augments existing RNG, not a replacement.
Lucky chest opens can still grant extra; unlucky ones still grant the
guaranteed minimums. The intent is to flatten run-to-run variance in
the early-game economy so balance changes can be tested against a
predictable supply baseline.

Budget per floor (constants below):
  upgrade_scrolls = 3   (tier scales with floor; vendor 1 + chest 2)
  rations         = 6   (vendor stack-count 3 + chest 3 single drops)
  healing_potions = 3   (vendor 1 + chest 2)
  lantern_fuel    = 3   (vendor 1 + chest 2)

Total chest-queue size: 9 items (2 scrolls + 3 rations + 2 pots + 2 fuel).
Floors typically have 3-7 chests; not every queue item is guaranteed to
land, but the budget is sized to drain on most layouts.
"""

import random


# Per-floor counts. Same across all floors; tier scales for scrolls.
UPGRADE_SCROLLS_PER_FLOOR = 3
RATIONS_PER_FLOOR = 6
HEALING_POTIONS_PER_FLOOR = 3
LANTERN_FUEL_PER_FLOOR = 3

# Split between vendor inventory (always there when vendor stocks) and
# chest-bonus queue (consumed on chest opens). Build-325 diagnostic
# showed 6/9 chest-queue items left undelivered per floor (chest open
# rate 41.5%), while vendor visits buy nearly everything stocked
# (rations 99%, scrolls 83%). Shift 1 ration + 1 heal + 1 fuel from
# chest queue to vendor supplement: redirects budget toward the
# higher-throughput delivery channel. Chest queue drops 9 -> 6 items.
VENDOR_SHARE = {
    "upgrade_scrolls": 1,
    "rations": 4,  # ration stack count, single item
    "healing_potions": 2,
    "lantern_fuel": 2,
}


def upgrade_scroll_for_floor(floor_level):
    """Return (name, description, effect_desc, value, level, tier_str)
    for an upgrade scroll matching the floor's tier. Mirrors the vendor
    upgrade-scroll formula in vendor.py:206-235.
    """
    if floor_level >= 25:
        return ("Scroll of Divine Upgrade",
                "The ultimate scroll of enhancement.",
                "Upgrade items to +20 maximum.", 1200, 25)
    elif floor_level >= 20:
        return ("Scroll of Mythic Upgrade",
                "A scroll touched by the gods themselves.",
                "Upgrade items to +17 maximum.", 850, 20)
    elif floor_level >= 15:
        return ("Scroll of Epic Upgrade",
                "A legendary scroll pulsing with raw power.",
                "Upgrade items to +14 maximum.", 600, 15)
    elif floor_level >= 10:
        return ("Scroll of Superior Upgrade",
                "An ancient scroll that can enhance weapon or armor.",
                "Upgrade items to +10 maximum.", 400, 10)
    elif floor_level >= 5:
        return ("Scroll of Greater Upgrade",
                "A powerful scroll that can enhance weapon or armor.",
                "Upgrade items to +6 maximum.", 250, 5)
    else:
        return ("Scroll of Upgrade",
                "A mystical scroll that can enhance weapon or armor.",
                "Upgrade items to +3 maximum.", 150, 1)


def _make_vendor_supply(floor_level):
    """Return a list of items the vendor should append to its inventory."""
    # Late imports: items.py imports game_state which is hairy at module load.
    from .items import Scroll, Food, Potion, LanternFuel

    out = []
    n_scroll = VENDOR_SHARE["upgrade_scrolls"]
    if n_scroll > 0:
        name, desc, eff, val, lvl = upgrade_scroll_for_floor(floor_level)
        for _ in range(n_scroll):
            out.append(Scroll(name, desc, eff, val, lvl, 'upgrade'))
    n_ration = VENDOR_SHARE["rations"]
    if n_ration > 0:
        out.append(Food(
            "Rations", "Standard travel rations.",
            value=10, level=0, nutrition=50, count=n_ration,
        ))
    n_pot = VENDOR_SHARE["healing_potions"]
    for _ in range(n_pot):
        out.append(Potion(
            "Minor Healing Potion",
            "A small vial of red liquid that heals minor wounds.",
            value=30, level=0,
            potion_type="healing", effect_magnitude=30,
        ))
    n_fuel = VENDOR_SHARE["lantern_fuel"]
    for _ in range(n_fuel):
        out.append(LanternFuel(
            "Lantern Fuel", "A small flask of oil for your lantern.",
            value=5, level=0, fuel_restore_amount=20,
        ))
    return out


def _make_chest_queue(floor_level):
    """Return a list of items that should drop as chest bonuses, one per
    chest open, in shuffled order so different chests on the same floor
    deliver varied bonuses.
    """
    from .items import Scroll, Food, Potion, LanternFuel

    out = []
    n_scroll = UPGRADE_SCROLLS_PER_FLOOR - VENDOR_SHARE["upgrade_scrolls"]
    if n_scroll > 0:
        name, desc, eff, val, lvl = upgrade_scroll_for_floor(floor_level)
        for _ in range(n_scroll):
            out.append(Scroll(name, desc, eff, val, lvl, 'upgrade'))
    n_ration = RATIONS_PER_FLOOR - VENDOR_SHARE["rations"]
    for _ in range(n_ration):
        out.append(Food(
            "Rations", "Standard travel rations.",
            value=10, level=0, nutrition=50, count=1,
        ))
    n_pot = HEALING_POTIONS_PER_FLOOR - VENDOR_SHARE["healing_potions"]
    for _ in range(n_pot):
        out.append(Potion(
            "Minor Healing Potion",
            "A small vial of red liquid that heals minor wounds.",
            value=30, level=0,
            potion_type="healing", effect_magnitude=30,
        ))
    n_fuel = LANTERN_FUEL_PER_FLOOR - VENDOR_SHARE["lantern_fuel"]
    for _ in range(n_fuel):
        out.append(LanternFuel(
            "Lantern Fuel", "A small flask of oil for your lantern.",
            value=5, level=0, fuel_restore_amount=20,
        ))
    random.shuffle(out)
    return out


def attach_supply(floor, floor_level):
    """Attach per-floor guaranteed supply to a Floor object. Called from
    Tower.add_floor() right after the layout is built.
    """
    floor.guaranteed_vendor_supply = _make_vendor_supply(floor_level)
    floor.guaranteed_chest_queue = _make_chest_queue(floor_level)


def pop_chest_bonus(floor):
    """Return the next bonus item from the floor's chest queue, or None
    if exhausted. Safe to call on floors generated before this system
    existed (returns None).
    """
    q = getattr(floor, "guaranteed_chest_queue", None)
    if not q:
        return None
    return q.pop()


def consume_vendor_supply(floor):
    """Return the floor's vendor supply list and clear it on the floor.
    Vendors call this once at instantiation. Subsequent vendors on the
    same floor get an empty list (the supply is once-per-floor, not
    once-per-vendor).
    """
    out = getattr(floor, "guaranteed_vendor_supply", None) or []
    if hasattr(floor, "guaranteed_vendor_supply"):
        floor.guaranteed_vendor_supply = []
    return out
