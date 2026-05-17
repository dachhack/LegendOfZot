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

Budget per floor:
  upgrade_scrolls = 3 (F1-4) -> 4 (F5-9) -> 5 (F10+)
  rations         = 6  (flat)
  healing_potions = 3 (F1-4) -> 4 (F5-9) -> 5 (F10+)
  lantern_fuel    = 3  (flat)

Tiers also scale: upgrade-scroll power follows upgrade_scroll_for_floor;
healing-potion magnitude follows healing_potion_for_floor (Minor 30 hp
on F1-4 -> Healing 50 hp on F5-9 -> Greater 100 hp on F10-14 -> Heroic
200 hp on F15+). Build 333: introduced depth scaling for scrolls + pots
because b332 grid hit a hard F8 wall (0 F10+ runs) -- on-pace agents
got cratered by F7-F9 elites with Minor (30hp) pots against 40+ damage
hits. Now F5+ agents land with stronger pots and more upgrade-scroll
budget to lift weapon/armor enchant to match deeper monster scaling.
"""

import random


# Per-floor counts (flat for rations + fuel; scrolls + pots scale).
RATIONS_PER_FLOOR = 6
LANTERN_FUEL_PER_FLOOR = 3


def upgrade_scrolls_per_floor(floor_level):
    if floor_level >= 10:
        return 5
    if floor_level >= 5:
        return 4
    return 3


def healing_potions_per_floor(floor_level):
    if floor_level >= 10:
        return 5
    if floor_level >= 5:
        return 4
    return 3

# Vendor/chest split per floor is now computed by `_vendor_share` so it
# can scale with depth. Build-325 diagnostic remains the guidance:
# vendor visit 52% vs chest open 41.5%, so vendor is the higher-
# throughput delivery channel. Bonus budget at F5+ goes to vendor.


def healing_potion_for_floor(floor_level):
    """Return Potion ctor args (name, description, value, level,
    effect_magnitude) for a healing potion matching the floor's tier.
    F1-4 Minor (30 hp); F5-9 Healing (50 hp); F10-14 Greater (100 hp);
    F15+ Heroic (200 hp). Build 333: introduced so F5+ supply lands
    actual-useful pots instead of 30hp Minors against 40+ damage hits.
    """
    if floor_level >= 15:
        return ("Heroic Healing Potion",
                "A radiant vial that mends grievous wounds.",
                250, 10, 200)
    if floor_level >= 10:
        return ("Greater Healing Potion",
                "Restores 100 HP.", 100, 2, 100)
    if floor_level >= 5:
        return ("Healing Potion",
                "Restores 50 HP.", 50, 1, 50)
    return ("Minor Healing Potion",
            "A small vial of red liquid that heals minor wounds.",
            30, 0, 30)


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


def _vendor_share(floor_level):
    """Per-floor vendor share. Scaled with depth for scrolls + pots so
    the extra F5+ budget lands on the higher-throughput delivery
    channel (b325 diag: vendor visit 52% vs chest open 41.5%, and
    scroll buy rate 83% / heal pot buy rate 65% once visited).
    """
    n_scroll_total = upgrade_scrolls_per_floor(floor_level)
    n_pot_total = healing_potions_per_floor(floor_level)
    # Vendor takes 1 scroll on F1-4, 2 on F5-9, 3 on F10+.
    if floor_level >= 10:
        vendor_scrolls = 3
        vendor_pots = 3
    elif floor_level >= 5:
        vendor_scrolls = 2
        vendor_pots = 3
    else:
        vendor_scrolls = 1
        vendor_pots = 2
    # Clamp in case the per-floor total is ever smaller than the share.
    vendor_scrolls = min(vendor_scrolls, n_scroll_total)
    vendor_pots = min(vendor_pots, n_pot_total)
    return {
        "upgrade_scrolls": vendor_scrolls,
        "rations": 4,
        "healing_potions": vendor_pots,
        "lantern_fuel": 2,
    }


def _make_vendor_supply(floor_level):
    """Return a list of items the vendor should append to its inventory."""
    # Late imports: items.py imports game_state which is hairy at module load.
    from .items import Scroll, Food, Potion, LanternFuel

    share = _vendor_share(floor_level)
    out = []
    n_scroll = share["upgrade_scrolls"]
    if n_scroll > 0:
        name, desc, eff, val, lvl = upgrade_scroll_for_floor(floor_level)
        for _ in range(n_scroll):
            out.append(Scroll(name, desc, eff, val, lvl, 'upgrade'))
    n_ration = share["rations"]
    if n_ration > 0:
        out.append(Food(
            "Rations", "Standard travel rations.",
            value=10, level=0, nutrition=50, count=n_ration,
        ))
    n_pot = share["healing_potions"]
    if n_pot > 0:
        pot_name, pot_desc, pot_val, pot_lvl, pot_mag = healing_potion_for_floor(floor_level)
        for _ in range(n_pot):
            out.append(Potion(
                pot_name, pot_desc,
                value=pot_val, level=pot_lvl,
                potion_type="healing", effect_magnitude=pot_mag,
            ))
    n_fuel = share["lantern_fuel"]
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

    share = _vendor_share(floor_level)
    out = []
    n_scroll = upgrade_scrolls_per_floor(floor_level) - share["upgrade_scrolls"]
    if n_scroll > 0:
        name, desc, eff, val, lvl = upgrade_scroll_for_floor(floor_level)
        for _ in range(n_scroll):
            out.append(Scroll(name, desc, eff, val, lvl, 'upgrade'))
    n_ration = RATIONS_PER_FLOOR - share["rations"]
    for _ in range(n_ration):
        out.append(Food(
            "Rations", "Standard travel rations.",
            value=10, level=0, nutrition=50, count=1,
        ))
    n_pot = healing_potions_per_floor(floor_level) - share["healing_potions"]
    if n_pot > 0:
        pot_name, pot_desc, pot_val, pot_lvl, pot_mag = healing_potion_for_floor(floor_level)
        for _ in range(n_pot):
            out.append(Potion(
                pot_name, pot_desc,
                value=pot_val, level=pot_lvl,
                potion_type="healing", effect_magnitude=pot_mag,
            ))
    n_fuel = LANTERN_FUEL_PER_FLOOR - share["lantern_fuel"]
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
