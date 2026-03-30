# Regolith Mining Skill Development Log

## Version: 1.1.0

---

## Architecture Overview

Regolith is a **mining data assistant** for Star Citizen that integrates multiple data sources:

```
┌─────────────────────────────────────────────────────────────┐
│  main.py (WingmanAI Skill)                                  │
│  - 16 AI tools for mining queries                           │
│  - Cache management                                         │
│  - Data loading orchestration                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  api.py (RegolithAPI Client)                                │
│  - Regolith.Rocks GraphQL client                            │
│  - UEX Corp REST client                                     │
│  - 24-hour cache with JSON persistence                      │
│  - Value calculation engine                                 │
└─────────────────────────────────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Regolith.Rocks     │     │  UEX Corp           │
│  GraphQL API        │     │  REST API           │
│  - Survey data      │     │  - Market prices    │
│  - Ore probabilities│     │  - Best sell locs   │
│  - Rock class data  │     │                     │
└─────────────────────┘     └─────────────────────┘
```

---

## Design Principles

1. **Data-Driven Accuracy**: Uses real survey data from player scans, not estimates
2. **Multi-Source Integration**: Combines Regolith survey data with UEX market prices
3. **Smart Caching**: 24-hour cache reduces API calls while keeping data fresh
4. **Value-Based Recommendations**: Calculates expected deposit value using mineral densities
5. **Voice-Optimized Responses**: Prompt guides AI to give concise, structured answers
6. **Discovery-Based Activation**: Skill activates when user asks about mining (30+ keywords)

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | WingmanAI skill class with 16 AI tools |
| `regolith_api.py` | GraphQL/REST client and value calculations |
| `default_config.yaml` | Skill config with discovery keywords and AI prompt |
| `clear_cache.py` | Standalone cache cleaner utility |
| `__init__.py` | Package exports |
| `Devlog.md` | This file |
| `TODO.md` | Task tracking |

---

## AI Tools Reference

### Cache Management
| Tool | Purpose |
|------|---------|
| `clear_cache` | Delete cache file |
| `refresh_cache` | Force refresh from APIs |

### Ore Information
| Tool | Purpose |
|------|---------|
| `get_ore_info` | Detailed info for specific ore |
| `list_all_ores` | All ores with densities |
| `get_ore_prices` | Raw/refined prices from UEX lookups |
| `get_mineral_prices` | All UEX prices sorted by value |
| `get_ore_market_price` | UEX price for specific ore |

### Refinery Operations
| Tool | Purpose |
|------|---------|
| `get_refinery_methods` | All methods with yield/time/cost ratings |
| `get_refinery_locations` | All refinery locations |
| `get_refinery_bonuses` | Bonuses for specific ore at all refineries |
| `find_best_refinery` | Best refinery for one or more ores |
| `calculate_refinery_job` | Estimate job output and value |

### Mining Locations
| Tool | Purpose |
|------|---------|
| `get_mining_locations` | All bodies grouped by type |
| `get_mining_ships` | Ships with mining capability |
| `get_location_ore_composition` | Ore probabilities at specific location |
| `search_location` | Search locations by name |
| `find_best_mining_location_by_value` | Best location for specific ore |
| `find_most_valuable_locations` | Most valuable locations overall |

### Development
| Tool | Purpose |
|------|---------|
| `debug_inspect_api` | Inspect GraphQL schema |

---

## Value Calculation Algorithm

The skill uses a sophisticated value calculation based on Lazarr Bandara's research:

```python
# For each ore at each location:
1. mineral_mass = deposit_mass × medPct × rock_probability × ore_probability
2. mineral_volume_scu = mineral_mass / mineral_density
3. mineral_value = mineral_volume_scu × price_per_scu

# Total deposit value = Σ mineral_value for all ores
```

**Key insight**: Each mineral has a different density, so mass-to-SCU conversion must be per-mineral.

### Mineral Density Table (excerpt)
```
Quantanium:  681.26 kg/SCU
Gold:        643.57 kg/SCU
Tungsten:    642.94 kg/SCU
Laranite:    383.09 kg/SCU
Taranite:    339.67 kg/SCU
...
Ice:          33.19 kg/SCU
```
Source: SC_Signature_Scanner project (datamined from game files)

---

## Changelog

### v1.1.0 (2026-02-18)
- **Logging**: Added `logger.exception()` to all 12 silent except blocks in `regolith_api.py` and `main.py` — failures now leave a diagnostic trail
- **DRY — `_requires_data` decorator**: Replaced 16 identical guard-clause blocks in `main.py` with a single decorator
- **DRY — `_get_location_label` helper**: Replaced 5 duplicate body-lookup patterns in `regolith_api.py`
- **Dead code removed**: `get_prompt` override, `find_best_mining_locations_by_value`, `find_best_refinery_for_ore`, unused `asdict`/`os` imports
- **Type hints modernized**: Replaced all `Optional[X]` with `X | None` (Python 3.10+ syntax)
- **Unit tests**: 34 tests covering value calculations, ore deposit info, location ranking, and helper methods
- **Fixed re-raise**: `load_lookups` now uses bare `raise` instead of wrapping in a new `Exception`

### v1.0.0 (2026-02-01)
- **Initial release** - Feature complete implementation
- **API Integration**: Regolith.Rocks GraphQL + UEX Corp REST
- **16 AI Tools**: Full suite of mining data queries
- **Smart Caching**: 24-hour JSON cache with background loading
- **Value Calculations**: Mass-to-SCU using mineral densities
- **Survey Data**: Real rock class and ore probability data
- **AI Prompt**: Response format rules for consistent output
- **Cache Utility**: Standalone `clear_cache.py` script
- **Multi-Language**: English and German hints in config

---

## Data Sources

### Regolith.Rocks (GraphQL)
- **Lookups**: Ore densities, refinery methods, ore processing values
- **Survey Data**: Player-submitted mining scan data
  - Rock class distribution by location
  - Ore content by rock class
  - Median rock mass values
  - Deposit spawn bonus multipliers

### UEX Corp (REST)
- **Commodities**: Mineral metadata
- **Prices**: Current market prices at all terminals

### Datamined (hardcoded)
- **Mineral Densities**: kg/SCU conversion factors
- **Manufacturer Codes**: Not currently used

---

## Cache Structure

```json
{
  "timestamp": 1706745600,
  "ore_densities": {...},
  "refinery_methods": {...},
  "ore_processing": {...},
  "bodies": [...],
  "max_prices": {...},
  "refinery_bonuses": {...},
  "ships": [...],
  "tradeports": [...],
  "refineries": [...],
  "ship_ore_probs": {...},
  "vehicle_ore_probs": {...},
  "bonus_map": {...},
  "bonus_map_roc": {...},
  "rock_class_by_location": {...},
  "ore_by_rock_class": {...},
  "uex_minerals": {...},
  "uex_prices": {...}
}
```

Location: `%APPDATA%/ShipBit/WingmanAI/<version>/skills/regolith/cache/regolith_cache.json`
