# Sprite Map Handoff — Chat Session

You (the chat session) already have the history of carving these monster sheets.
This handoff covers **the change in direction** and **the JSON sprite map** we now
need you to produce.

---

## 0. WHAT'S DIFFERENT NOW (read this first)

We are upgrading the **stronger monsters** (bosses, shard guardians, deep-tier
elites, and giants) to a new sprite standard:

- **LARGER.** The legacy in-game sprites are tiny (96×96). These strong monsters
  render big in combat (96–150px, and bosses/legendaries **loom over the HUD**),
  so their source art must be high-resolution. **Target 512×512** for bosses and
  shard guardians, **256×256+** for the deep/giant elites.
- **TRANSPARENT BACKGROUNDS.** Unlike the legacy sprites (which bake in a dark
  square), these use a **real alpha-transparent background (PNG RGBA)**. This is
  deliberate: a transparent sprite composites cleanly over the combat panel and
  lets the boss "loom" past the HUD with no ugly dark rectangle behind it.
  - If a generated image has a true transparent background, keep it.
  - If it has a flat color or a checkerboard backdrop, **key that background out
    to alpha** (flood-fill from the image borders so you don't punch holes in
    gray/among-the-creature pixels).
- **FRAMING.** Creature centered, occupying ~65–70% of the frame, with even
  padding all around (so they sit at a consistent scale and have headroom to
  loom). One creature per file.

So: **big, transparent, centered, high-res.** That's the spec for everything in
the map below.

---

## 1. Your output: the JSON sprite map

Produce a JSON object mapping each **exact map key** → a list of sprite variants.

### Schema
```json
{
  "<exact map key>": [ ["<pid>", <variant_index>], ... ],
  ...
}
```
- One entry per monster.
- The value is an ordered list of variants. **variant_index starts at 0** (the
  primary look) and increments. The game picks one variant at random per fight,
  so multiple entries = visual variety.
- `<pid>` = the **filename stem** of the carved sprite (no extension). These are
  placeholders; see §4.

A pre-filled starter is committed at **`sprite_package/monster_sprite_map.json`**
(all 51 keys, each with one variant-0 placeholder pid). Edit that — confirm/replace
each placeholder pid with the actual carved-sprite filename, and add extra
variants where a monster has more than one look.

### Example
```json
{
  "ZOT'S GUARDIAN": [["zots_guardian", 0]],
  "DRAGON": [["ancient_dragon", 0], ["ancient_demon_dragon", 1]],
  "Nightmare Lich": [["nightmare_lich", 0]]
}
```

---

## 2. The monster keys (case + spacing are exact — do not normalize them)

The game resolves decorated in-game names down to these keys, so they must match
exactly. **The short ALL-CAPS keys are shard guardians whose in-game names are
truncated** — the legend tells you which creature each one is.

**Bosses (3):** `ZOT'S GUARDIAN`  ·  `Platino`  ·  `BUG QUEEN`

**Shard guardians (8) — odd keys, legend:**
| key | creature it is |
|---|---|
| `DRAGON` | Ancient Dragon (battle shard) |
| `TREASURE GOLEM` | Treasure Golem (treasure) |
| `DIVINE AVATAR` | Divine Avatar (devotion) |
| `LORD` | Water Elemental Lord (reflection) |
| `ARCHLICH` | Archlich (knowledge) |
| `DEMON` | Shadow Demon (secrets) |
| `DEATH KNIGHT` | Death Knight (eternity) |
| `ANCIENT` | Treant Ancient (growth) |

**Deep tier L12–15 (24):** `Elder Starspawn` `Voidmaw Devourer` `Cataclysm Fiend`
`Nightmare Lich` `Soulflayer Wraith` `Infernal Warlord` `Abyssal Archfiend`
`Starspawn Aberration` `Crimson Wyrmlord` `Sepulchral Lich` `Maw of the Deep`
`Glacian Titan` `Abyssal Fiend` `Illithid Overmind` `Hundred-Eyed Watcher`
`Necrarch Lich` `Graven Colossus` `Cryptborn Wraith` `Hollow Lich`
`Emberscale Drake` `Gnashing Horror` `Iron Vanguard` `Cinderborn Efreet`
`Rimebound Djinn`

**Giants L9–11 (16):** `Cinder Serpent` `Gloomback Bear` `Ridgeback Wyvern`
`Voidspawn Brute` `Sporelord Myconid` `Balrog` `Balor` `Demilich` `Elder Brain`
`Pit Fiend` `Storm Giant` `Cyclops` `Dragon Turtle` `Fire Giant` `Purple Worm`
`Sphinx`

That's **51 keys total.** All of them already exist in the game's map EXCEPT
`ZOT'S GUARDIAN`, which is brand new.

---

## 3. Do NOT map these (reserve art, no game monster)

Creatures we generated that have **no monster in the game** — keep them as
reserve art, do not put them in the JSON:
Ragnarok · the Overlord · Gravewright · Bone Choir · Chain Tyrant · Sin-Eater ·
Clockwork Inquisitor · Mirror Sentinel · Petrifang Hydra · Thornhag · The Hollow
King · Bog Mother · Veiled Oracle · Star-Eater Cultist · (and any other brainstorm
creatures). They can only be wired once someone adds the monster to `game_data.py`.

---

## 4. The pid reality (important)

In a chat session there are no real pool IDs. The game's actual sprite IDs look
like `MN1829`, assigned only when a sprite is promoted into the canonical pool
(a code/pipeline step, not chat). So:

- Use your **carved filename stems as placeholder pids** in the JSON.
- Keep a side-list: `filename → monster key` so the later swap is mechanical.
- When the sprites are promoted into the pool, the placeholders get find-replaced
  with the real `MN####` ids.

The JSON you produce now is the **plan/source of truth for assignments** — not a
file the game loads directly yet.

---

## 5. How it lands in the game (context, not your job)

This JSON mirrors the game's Python structure:
```python
_MONSTERS_MAP = { name: [(pid, variant_index), ...] }
```
Converting JSON → Python is mechanical (lists → tuples). It then gets applied to
**both** copies that must stay in sync:
- `wizardscavern/sprites/monsters.py` (runtime)
- `sprite_package/code/sprite_data_monsters.py` (pool build)

and the pool is rebuilt with `sprite_package/code/promote_all_sprites.py`.

---

## 6. Checklist for this session

1. Confirm every carved strong-monster sprite is **transparent (RGBA), large
   (256–512px), centered with padding.** Re-key/upscale any that aren't.
2. Open `sprite_package/monster_sprite_map.json` and, for each of the 51 keys,
   set the placeholder pid to the real carved filename stem (add variants where
   you have multiple looks for one monster).
3. Maintain the `filename → key` side-list for the eventual `MN####` swap.
4. Leave reserve creatures (§3) OUT of the JSON.
5. Output the final JSON (valid, sorted by key) + the side-list.

## 7. Per-sprite notes from review
- **Death Knight** art had a stone pedestal — every other sprite floats; drop the
  base or re-roll it.
- **Archlich / Shadow Demon / Death Knight** looked too similar (all dark purple) —
  push their palettes apart.
- **Platino** read as a generic white dragon — push the platinum/metallic sheen.
