# MineOS PrismarineJS data import

## Run
Open a terminal in the MineOS project root and run:

```bash
python scripts/sync_prismarine_data.py
```

The script downloads the selected Java Edition datasets from PrismarineJS/minecraft-data and writes them as ES modules directly inside `data/`. It also retrieves the newest matching asset snapshot published by PrismarineJS/minecraft-assets, placing those files under `assets/minecraft-assets/`.

## Version notes
- Requested Java data version: `1.21.11`. The script checks that this exact folder exists upstream before importing; it will not silently substitute a different game-data version.
- The assets repository may not publish a `1.21.11` snapshot. If not, the script uses `1.21.8` when available and clearly reports the mismatch.
- PrismarineJS/minecraft-data provides biomes, blocks, entities, items, recipes, enchantments and effects. `mobs.js` is sourced from its entity registry.
- The two selected repositories do not provide complete generated-structure, loot-table or advancement registries. Those files remain explicitly marked unavailable rather than filled with invented data.
- No sounds or paintings/music datasets are imported.

## Flat data folder
All database modules stay directly in `data/`: `biomes.js`, `mobs.js`, `blocks.js`, `items.js`, `structures.js`, `recipes.js`, `enchantments.js`, `effects.js`, `loot_tables.js`, `advancements.js`.

## Sources and licenses
- https://github.com/PrismarineJS/minecraft-data (MIT; check upstream notices for extracted data)
- https://github.com/PrismarineJS/minecraft-assets (check its repository license and included asset notices)
