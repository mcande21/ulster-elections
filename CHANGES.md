# Changes to Brian's Boards 2025

## Overview

Implemented a strategic vulnerability scoring system to replace the simplistic `100 - margin_pct` formula. The new system factors in margin tightness, swing potential, turnout stability, and strategic categories.

## Files Changed

### Backend

**`backend/app/services/database.py`**

Added two functions:

1. **`calculate_vulnerability_score(margin_pct, total_votes, winner_party, county)`**
   - Multi-factor strategic scoring algorithm
   - Returns score 0-100 (higher = more vulnerable)
   - Factors:
     - 40%: Margin tightness (non-linear, <5% bonus)
     - 30%: Swing potential (votes in dispute)
     - 20%: Turnout factor (volatility by electorate size)
     - 10%: Category multiplier (D/R vs Other)

2. **`get_vulnerability_scores(limit=20)` - Modified**
   - Now calls `calculate_vulnerability_score()` for each race
   - Sorts by score descending (highest vulnerability first)
   - Previously sorted ascending by margin

**Example behavior change:**

Before:
```python
vulnerability_score = 100 - margin_pct
# 1% margin → 99
# 5% margin → 95
# 30% margin → 70
# Sorted: ascending by margin
```

After:
```python
# Multi-factor calculation
# 1% margin, 10k votes → 54 (moderate, decent electorate)
# 5% margin, 3k votes → 82 (very high, small electorate)
# 30% margin → ~50 (lower vulnerability regardless of size)
# Sorted: descending by vulnerability score
```

### Documentation

**`VULNERABILITY_SCORING.md`** (new)
- Comprehensive methodology guide
- Component explanations with examples
- Scoring interpretation scale
- Design rationale
- Known limitations
- Future enhancement suggestions

**`IMPLEMENTATION_SUMMARY.md`** (new)
- Quick reference guide to changes
- Test results with sample scenarios
- API documentation
- Migration notes

### Tests

**`backend/test_vulnerability_logic.py`** (new)
- Unit tests for scoring logic
- 10 test scenarios covering edge cases
- Can run without database dependencies

### Frontend

**No changes needed** - Components already designed for this scoring system:

- `frontend/src/components/VulnerabilityPanel.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/types/index.ts`

All were already correctly expecting this backend implementation.

## API Changes

**Endpoint:** `GET /api/races/vulnerability?limit=20`

**Response format:** (unchanged)
```json
{
  "id": number,
  "vulnerability_score": number (0-100),
  "category": "flip_opportunity" | "retention_risk" | "other",
  "race_title": string,
  "county": string,
  "margin_pct": number
}
```

**Sort order change:**
- Before: Ascending by margin (closest first)
- After: Descending by vulnerability_score (highest risk first)

## Key Improvements

### 1. Smaller Electorates Get Appropriate Weight

A 5% margin in a 3,000-voter race is fundamentally different from 5% in a 50,000-voter race:
- 3,000 voters: 82.0 score (extremely vulnerable)
- 50,000 voters: 68.0 score (very vulnerable)
- Difference: 14 points captures real electoral volatility

### 2. Very Tight Races Get Emphasis

Races under 5% margin get 1.3x boost to distinguish them:
- 1% margin: Higher vulnerability bonus
- 5% margin: Peak of swing potential calculation
- 20% margin: Moderate vulnerability
- 50%+ margin: Safe (score <40)

### 3. Rational Score Distribution

Results now span the full 0-100 scale meaningfully:
- Blowouts: 30-40 (safe)
- Moderate margins: 50-70 (varied risk)
- Tight races: 70-85 (high risk)
- Small electorates with tight margins: 80-100 (extreme risk)

### 4. Strategic Sorting

Returns highest-vulnerability races first - perfect for:
- Resource allocation decisions
- Campaign priority setting
- Risk assessment for messaging
- Targeting strategy

## Backward Compatibility

**Database:** No schema changes - all calculations are done at query time

**Existing Features:** Unaffected
- Regular race queries still work
- Fusion voting analysis unchanged
- Filter options unchanged
- Stats calculations unchanged

**API Breaking Change:** Sort order is now descending by score

This is intentional and beneficial - most users want to see highest-risk races first.

## Testing

### Run Test Script
```bash
python3 backend/test_vulnerability_logic.py
```

Expected output: 10 scenarios with scores ranging from 38.0 to 82.0

### Test API Endpoint
```bash
# Start backend
cd backend && uvicorn app.main:app --reload --port 8000

# Test endpoint
curl "http://localhost:8000/api/races/vulnerability?limit=5" | jq .
```

### Frontend Testing
- Dashboard loads VulnerabilityPanel automatically
- Displays top 20 vulnerable races
- Scores calculated server-side
- UI unchanged

## Next Steps

1. Review the implementation
2. Test with real election data
3. Monitor scores for accuracy
4. Use in strategy/planning
5. Consider future enhancements (see VULNERABILITY_SCORING.md)

## Design Decisions

**Why multi-factor scoring?**

Single factors miss critical context:
- Margin alone: Ignores electorate volatility
- Turnout alone: Ignores outcome likelihood
- Composite: Captures full picture

**Why these weights?**

- 40% Margin: Most predictive for outcome
- 30% Swing: Secondary predictor
- 20% Turnout: Affects volatility
- 10% Category: Strategic classification

**Why emphasis boost for <5%?**

Election research shows 5% is the "true toss-up" threshold. Anything tighter deserves special attention.

**Why turnout-based volatility?**

County election literature shows:
- Small races more sensitive to weather, organization, turnout variance
- Larger races more stable and predictable

## Limitations & Future Work

See VULNERABILITY_SCORING.md for:
- Known limitations
- Enhancement suggestions
- Potential integrations (fusion voting, incumbency, demographics)
- Trend analysis possibilities

## Questions?

Refer to:
- `VULNERABILITY_SCORING.md` - Methodology details
- `IMPLEMENTATION_SUMMARY.md` - Quick reference
- `backend/test_vulnerability_logic.py` - Code examples
