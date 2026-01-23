# Refactoring Notes

*Compiled: 2025-01-23*

This document tracks code smells, technical debt, and improvement opportunities discovered during the vulnerability calculation audit.

---

## Priority: High

### 1. Duplicate Calculation Logic

**Location:** `StatCards.tsx:12-13` duplicates `database.py:220-221`

**Issue:** Flip opportunities and retention risks are calculated in both frontend and backend:
- Frontend: `races.filter(r => r.vulnerability_score >= 1.2 && r.margin_pct < 10).length`
- Backend: Similar calculation in database service

**Risk:** Logic divergence over time. If threshold changes in one place, breaks in the other.

**Fix:**
- Frontend should consume backend stats endpoint, not recalculate
- Single source of truth for these metrics
- Backend provides pre-calculated counts

**Estimated effort:** 2-3 hours

---

### 2. No Unit Tests for Complex Calculations

**Location:** `backend/app/services/database.py`

**Issue:** Vulnerability scoring, margin calculations, fusion leverage have **zero test coverage**. These are the most critical calculations in the application.

**Risk:**
- No protection against regression
- Can't verify formula correctness
- Edge cases untested (0% margin, missing data, division by zero)

**Fix:** Add pytest tests for:
- **Edge cases:**
  - 0% margin races
  - Missing total_votes_cast
  - Null turnout data
  - Division by zero in swing_potential
- **Known good values (regression tests):**
  - Manually verified examples from real data
  - Before/after for any formula changes
- **Formula correctness:**
  - Round-trip tests (if margin=5%, expect score X)
  - Threshold boundary tests (4.99% vs 5.01%)

**Estimated effort:** 1-2 days

**Priority justification:** These calculations drive the entire UI. No tests = no confidence.

---

## Priority: Medium

### 3. God Function

**Location:** `database.py` `get_races()` function

**Issue:** 80+ lines doing:
- Database query
- Vulnerability calculation
- Filtering by county/category
- Sorting

**Violations:**
- Single Responsibility Principle
- Difficult to test individual pieces
- Hard to understand control flow

**Fix:** Extract into smaller, testable functions:

```python
def query_races(county: str, year: int) -> List[Race]:
    """Query races from database"""

def calculate_vulnerability(races: List[Race]) -> List[Race]:
    """Apply vulnerability scoring to races"""

def apply_filters(races: List[Race], county: str, category: str) -> List[Race]:
    """Filter races by county and category"""

def sort_races(races: List[Race], sort_by: str) -> List[Race]:
    """Sort races by specified field"""

def get_races(...):
    races = query_races(county, year)
    races = calculate_vulnerability(races)
    races = apply_filters(races, county, category)
    races = sort_races(races, sort_by)
    return races
```

**Estimated effort:** 4-6 hours

---

### 4. Magic Numbers

#### 4.1 Margin Multiplier

**Location:** `database.py:305-306`

```python
if margin_pct < 5:
    vulnerability_score *= 1.3  # Why 1.3?
```

**Issue:** 1.3 multiplier for <5% margin races is undocumented. Why 1.3? Why not 1.5 or 1.2?

**Fix:**
```python
CLOSE_RACE_THRESHOLD = 5.0  # Percent margin
CLOSE_RACE_MULTIPLIER = 1.3  # 30% boost for highly competitive races

if margin_pct < CLOSE_RACE_THRESHOLD:
    vulnerability_score *= CLOSE_RACE_MULTIPLIER
```

**Estimated effort:** 15 minutes

---

#### 4.2 Turnout Thresholds

**Location:** `database.py:318-327`

```python
if turnout < 5000:
    turnout_weight = 0.5
elif turnout < 10000:
    turnout_weight = 0.75
elif turnout < 25000:
    turnout_weight = 1.0
elif turnout < 50000:
    turnout_weight = 1.25
else:
    turnout_weight = 1.5
```

**Issue:** Thresholds (5k/10k/25k/50k) hardcoded without explanation. What do these buckets represent? Why these specific values?

**Fix:**
```python
# Turnout buckets based on NY election district sizes
# Small district: < 5k (town council, village races)
# Medium district: 5k-10k (small city council)
# Standard district: 10k-25k (county legislature)
# Large district: 25k-50k (state assembly)
# Major district: 50k+ (state senate, congressional)
TURNOUT_VERY_SMALL = 5_000
TURNOUT_SMALL = 10_000
TURNOUT_MEDIUM = 25_000
TURNOUT_LARGE = 50_000

def calculate_turnout_weight(turnout: int) -> float:
    """Weight based on district size (higher turnout = more strategic value)"""
    if turnout < TURNOUT_VERY_SMALL:
        return 0.5
    elif turnout < TURNOUT_SMALL:
        return 0.75
    elif turnout < TURNOUT_MEDIUM:
        return 1.0
    elif turnout < TURNOUT_LARGE:
        return 1.25
    else:
        return 1.5
```

**Estimated effort:** 30 minutes

---

### 5. Inconsistent Key Names

**Location:** `load_db.py:128`

```python
total_votes = race_data.get("total_votes") or race_data.get("total")
```

**Issue:** Handles both `total_votes` and `total` for the same concept. Why two keys?

**Root cause:** Different PDF extractors use different key names. This is a workaround.

**Fix:** Normalize at extraction time, use single key throughout:

```python
# In extractor registry or base class
def normalize_race_data(data: dict) -> dict:
    """Normalize keys across different extractor formats"""
    if "total" in data and "total_votes" not in data:
        data["total_votes"] = data.pop("total")
    return data
```

**Estimated effort:** 1-2 hours (test all extractors)

---

## Priority: Low

### 6. Category Multiplier Documentation

**Location:** `database.py` vulnerability scoring

```python
# Category weighting (~10% weight)
if category == "Other":
    vulnerability_score *= 0.7
```

**Issue:** Comment says "10% weight" but it's actually a final multiplier (0.7x = 30% reduction, not 10%).

**Fix:** Clarify documentation:

```python
# Category multiplier: De-prioritize "Other" races (30% reduction)
# Focuses analysis on County Leg, Town Board, City Council
CATEGORY_MULTIPLIER_OTHER = 0.7

if category == "Other":
    vulnerability_score *= CATEGORY_MULTIPLIER_OTHER
```

**Estimated effort:** 5 minutes

---

## Already Fixed This Session

- [x] **UI tooltip threshold mismatch** (`RacesTable.tsx`) - Tooltip said >1.3, code checked >=1.2
- [x] **Inverted swing_potential formula** (`database.py`) - Was 100 - turnout, should be turnout

---

## Future Considerations

### Data Quality Issues (out of scope for refactoring)

- Missing `total_votes_cast` for many races (defaults to 0, breaks calculations)
- Inconsistent party line ordering across counties
- Vote totals that don't match sum of candidates

**Recommendation:** Create separate data quality audit document.

### Performance Optimization

- `get_races()` recalculates vulnerability for every request
- Consider caching calculated scores
- Precompute during import, store in database

**Not urgent:** Current performance is acceptable for dataset size.

---

## Notes

- Refactoring should be done incrementally, not big-bang
- Add tests BEFORE refactoring to prevent regression
- Each fix should be a separate commit with clear description
- Consider creating GitHub issues for Priority: High items

---

*Next review: After next major feature addition*
