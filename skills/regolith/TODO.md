# Regolith Mining Skill TODO

## Current Status: Feature Complete - Testing Phase

Full integration with Regolith.Rocks GraphQL API and UEX Corp REST API.
16 AI tools implemented for mining data queries.

---

## Completed

### Core Infrastructure
- [x] `RegolithAPI` GraphQL client for Regolith.Rocks
- [x] UEX Corp REST API integration for market prices
- [x] 24-hour persistent JSON cache with validity checking
- [x] Background data loading during `prepare()`
- [x] Cache building state tracking for async handling
- [x] API key validation on startup

### Data Sources
- [x] CIG lookup data (ore densities, refinery methods, ore processing)
- [x] UEX lookup data (bodies, max prices, refinery bonuses, ships, tradeports)
- [x] Survey data (ship/vehicle ore probabilities, rock class data)
- [x] Bonus maps (deposit spawn multipliers by location)
- [x] UEX mineral prices with best sell locations

### AI Tools (16 total)
- [x] `clear_cache` - Clear cache file
- [x] `refresh_cache` - Force refresh from APIs
- [x] `get_ore_info` - Detailed ore information
- [x] `list_all_ores` - List all ores with densities
- [x] `get_refinery_methods` - All refinery methods with ratings
- [x] `get_refinery_locations` - All refinery locations
- [x] `get_refinery_bonuses` - Refinery bonuses for specific ore
- [x] `find_best_refinery` - Best refinery for one or more ores
- [x] `get_mining_locations` - All mining bodies grouped by type
- [x] `get_mining_ships` - Ships with mining capabilities
- [x] `get_location_ore_composition` - Ore probabilities at location
- [x] `get_ore_prices` - Raw/refined ore prices
- [x] `calculate_refinery_job` - Estimate refinery job output
- [x] `search_location` - Search for locations by name
- [x] `find_best_mining_location_by_value` - Best location for specific ore
- [x] `find_most_valuable_locations` - Most valuable mining locations overall
- [x] `get_mineral_prices` - All UEX mineral prices sorted by value
- [x] `get_ore_market_price` - UEX price for specific ore
- [x] `debug_inspect_api` - Schema inspection for development

### Value Calculation System
- [x] Mineral density table (datamined from SC game files)
- [x] Mass-to-SCU conversion using per-mineral densities
- [x] Real rock mass data from survey data
- [x] Expected deposit value calculation across all ores
- [x] Price integration for value-based recommendations

### Configuration
- [x] `default_config.yaml` with discovery keywords
- [x] AI prompt with response format rules
- [x] Multi-language hints (en/de)
- [x] `clear_cache.py` standalone utility

---

## In Progress

### Testing & Validation
- [ ] Test all 16 tools with live API data
- [ ] Validate value calculations against player reports
- [ ] Test cache expiry and refresh behavior
- [ ] Test error handling when APIs are unavailable

---

## Future Enhancements

### Priority 1: User Experience
- [x] Discovery-based activation via keywords (mining, ore, refinery, etc.)
- [ ] Add notification when cache is refreshed
- [ ] Add warning when cache is stale (>24h)
- [ ] Improve error messages for API failures

### Priority 2: Data Improvements
- [ ] Add Pyro system support (when survey data available)
- [ ] Add NYX system support (when survey data available)
- [ ] Add ROC/vehicle mining value calculations
- [ ] Track price history for trend analysis

### Priority 3: Advanced Features
- [ ] Mining route optimization (multiple stops)
- [ ] Refinery queue time estimation
- [ ] Profit calculator with fuel costs
- [ ] Integration with SC_LogReader for context-aware recommendations

### Priority 4: Code Quality
- [ ] Add unit tests for API client
- [ ] Add unit tests for value calculations
- [ ] Document mineral density sources
- [ ] Add type hints to remaining functions

---

## Known Issues

- None currently tracked

---

## API Data Structure Notes

### Regolith GraphQL Endpoints
- `lookups` - CIG and UEX lookup tables
- `surveyData(dataName, epoch)` - Survey probability data
  - `shipOreByGravProb` - Ship mining ore probabilities
  - `shipRockClassByGravProb` - Rock class distribution by location
  - `shipOreByRockClassProb` - Ore content by rock class
  - `vehicleProbs` - ROC/hand mining probabilities
  - `bonusMap` / `bonusMap.roc` - Deposit spawn multipliers

### UEX Corp REST Endpoints
- `/commodities` - Commodity metadata (is_mineral flag)
- `/commodities_prices_all` - All commodity prices

### Mineral Density Formula
```
mineral_volume (SCU) = mineral_mass / density
```
Source: SC_Signature_Scanner project datamined values
