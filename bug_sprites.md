# Bug Monster Sprite Assignments

All bug monsters use the **Compendium** sprite sheet (18x18 pixel cells, 30 columns x 18 rows).

## Current Assignments

| Monster | Sheet | Col | Row | Description |
|---------|-------|-----|-----|-------------|
| **BUG QUEEN** | Compendium | 18 | 9 | The boss |
| **Titan Beetle** | Compendium | 4 | 11 | Heavy beetle/crawler |
| **Stinkbug Brute** | Compendium | 4 | 10 | Spiky dark beetle |
| **Fly Swarm** | Compendium | 10 | 11 | Buzzing fly swarm |
| **Pill Bug Golem** | Compendium | 2 | 10 | Armored shell creature (tank) |
| **Firefly Mage** | Compendium | 14 | 11 | Bright glowing flier |
| **Ant Soldier** | Compendium | 1 | 11 | Dark ant |
| **Dung Beetle Lord** | Compendium | 1 | 3 | Chunky dark beetle |
| **Dragonfly Enchantress** | Compendium | 9 | 11 | Iridescent dragonfly |
| **Earthworm** | Compendium | 10 | 10 | Segmented earthworm |
| **Snail** | Compendium | 8 | 10 | Giant snail with shell |

## How to Change a Sprite

In `sprite_data.py`, find `generate_monster_sprite_html()` and update the `_MAP` entry:

```python
'Monster Name': ('Compendium', col, row),
```

Coordinates are `(col, row)` matching the Compendium reference grid.
