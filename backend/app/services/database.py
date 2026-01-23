"""PostgreSQL database query service."""

from typing import List, Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ..models.schemas import RaceData, StatsResponse, FilterOptions, RaceFusionMetrics, CandidateFusionMetrics, PartyLineBreakdown
from ..config import DATABASE_URL


# Party classification for fusion voting analysis
MAIN_PARTIES = {"Democratic", "Republican"}
D_ALIGNED_MINOR = {"Working Families"}
R_ALIGNED_MINOR = {"Conservative"}


# Connection pool (initialized by app lifespan)
_pool: Optional[ConnectionPool] = None


def init_pool():
    """Initialize the connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=10)


def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_pool() -> ConnectionPool:
    """Get the connection pool."""
    if _pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return _pool


def extract_race_type(race_title: str) -> str:
    """Extract race type from title (Supervisor, Council, Legislature, etc.)."""
    race_title_lower = race_title.lower()

    if "supervisor" in race_title_lower:
        return "Supervisor"
    elif "council" in race_title_lower:
        return "Council"
    elif "legislat" in race_title_lower:
        return "Legislature"
    elif "clerk" in race_title_lower:
        return "Clerk"
    elif "highway" in race_title_lower:
        return "Highway"
    elif "justice" in race_title_lower:
        return "Justice"
    elif "tax" in race_title_lower:
        return "Tax Collector"
    else:
        return "Other"


def determine_competitiveness_band(margin_pct: float) -> str:
    """Determine competitiveness band based on margin percentage."""
    if margin_pct < 5:
        return "Thin"
    elif margin_pct < 10:
        return "Lean"
    elif margin_pct < 20:
        return "Likely"
    else:
        return "Safe"


def normalize_party(party_str: Optional[str]) -> str:
    """Normalize party coalition to D, R, or Other."""
    if not party_str:
        return "Other"

    party_upper = party_str.upper().strip()

    # Database already stores normalized values (D, R, Other)
    # But handle both normalized and raw formats
    if party_upper == "D" or "DEM" in party_upper or "WOR" in party_upper:
        return "D"
    elif party_upper == "R" or "REP" in party_upper or "CON" in party_upper:
        return "R"
    else:
        return "Other"


def build_where_clause(
    county: Optional[List[str]] = None,
    competitiveness: Optional[List[str]] = None,
    party: Optional[List[str]] = None,
    race_type: Optional[List[str]] = None,
) -> tuple[str, List[Any]]:
    """Build WHERE clause and parameters for filtering."""
    conditions = []
    params = []

    if county:
        placeholders = ", ".join(["%s"] * len(county))
        conditions.append(f"r.county IN ({placeholders})")
        params.extend(county)

    if party:
        # Party filter applies to winner_party (will be normalized later)
        placeholders = ", ".join(["%s"] * len(party))
        conditions.append(f"winner_party_raw IN ({placeholders})")
        params.extend(party)

    # Competitiveness and race_type are applied after query (calculated fields)

    where_clause = " AND " + " AND ".join(conditions) if conditions else ""
    return where_clause, params


def get_races(
    county: Optional[List[str]] = None,
    competitiveness: Optional[List[str]] = None,
    party: Optional[List[str]] = None,
    race_type: Optional[List[str]] = None,
    sort: str = "margin_pct",
    order: str = "asc",
) -> List[RaceData]:
    """Query races from database with filtering and sorting."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:

            where_clause, params = build_where_clause(county, party=party)

            query = f"""
            SELECT
                r.id,
                r.county,
                r.race_title,
                r.total_votes_cast,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.total_votes END) as winner_votes,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.name END) as winner_name,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.party_coalition END) as winner_party_raw,
                MAX(CASE WHEN c.is_winner = FALSE THEN c.total_votes END) as runnerup_votes,
                MAX(CASE WHEN c.is_winner = FALSE THEN c.name END) as runnerup_name,
                MAX(CASE WHEN c.is_winner = FALSE THEN c.party_coalition END) as runnerup_party_raw
            FROM races r
            JOIN candidates c ON r.id = c.race_id
            {where_clause}
            GROUP BY r.id
            HAVING MAX(CASE WHEN c.is_winner = TRUE THEN c.total_votes END) IS NOT NULL
                AND MAX(CASE WHEN c.is_winner = FALSE THEN c.total_votes END) IS NOT NULL
            """

            cursor.execute(query, params)
            rows = cursor.fetchall()

    races = []
    for row in rows:
        total_votes = row["total_votes_cast"] or 0
        winner_votes = row["winner_votes"] or 0
        runnerup_votes = row["runnerup_votes"] or 0

        if total_votes == 0:
            continue

        vote_diff = winner_votes - runnerup_votes
        margin_pct = (vote_diff / total_votes) * 100

        race_data = RaceData(
            id=row["id"],
            county=row["county"],
            race_title=row["race_title"],
            race_type=extract_race_type(row["race_title"]),
            winner_name=row["winner_name"],
            winner_party=normalize_party(row["winner_party_raw"]),
            winner_votes=winner_votes,
            runner_up_name=row["runnerup_name"],
            runner_up_party=normalize_party(row["runnerup_party_raw"]),
            runner_up_votes=runnerup_votes,
            total_votes=total_votes,
            margin_pct=round(margin_pct, 2),
            vote_diff=vote_diff,
            competitiveness_band=determine_competitiveness_band(margin_pct)
        )

        races.append(race_data)

    # Apply post-query filters (calculated fields)
    if competitiveness:
        races = [r for r in races if r.competitiveness_band in competitiveness]

    if race_type:
        races = [r for r in races if r.race_type in race_type]

    # Sort
    reverse = (order.lower() == "desc")
    if sort == "margin_pct":
        races.sort(key=lambda x: x.margin_pct, reverse=reverse)
    elif sort == "county":
        races.sort(key=lambda x: x.county, reverse=reverse)
    elif sort == "race_type":
        races.sort(key=lambda x: x.race_type, reverse=reverse)

    return races


def get_stats(
    county: Optional[List[str]] = None,
    competitiveness: Optional[List[str]] = None,
    party: Optional[List[str]] = None,
    race_type: Optional[List[str]] = None,
) -> StatsResponse:
    """Calculate summary statistics with filtering."""
    races = get_races(county, competitiveness, party, race_type)

    total = len(races)
    flip_opportunities = sum(1 for r in races if r.winner_party == "R" and r.margin_pct < 10)
    retention_risks = sum(1 for r in races if r.winner_party == "D" and r.margin_pct < 10)
    closest_margin = min((r.margin_pct for r in races), default=None)

    return StatsResponse(
        total=total,
        flipOpportunities=flip_opportunities,
        retentionRisks=retention_risks,
        closestMargin=closest_margin
    )


def get_filter_options() -> FilterOptions:
    """Get available filter options from database."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:

            # Get all races to extract unique values
            query = """
            SELECT DISTINCT r.county, r.race_title,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.party_coalition END) as winner_party
            FROM races r
            JOIN candidates c ON r.id = c.race_id
            GROUP BY r.id
            """

            cursor.execute(query)
            rows = cursor.fetchall()

    counties = sorted(set(row["county"] for row in rows))
    race_types = sorted(set(extract_race_type(row["race_title"]) for row in rows))
    parties = sorted(set(normalize_party(row["winner_party"]) for row in rows))
    competitiveness_levels = ["Thin", "Lean", "Likely", "Safe"]

    return FilterOptions(
        counties=counties,
        raceTypes=race_types,
        parties=parties,
        competitivenessLevels=competitiveness_levels
    )


def calculate_vulnerability_score(
    margin_pct: float,
    total_votes: int,
    winner_party: str,
    county: str,
    under_votes: Optional[int] = None,
    total_ballots_cast: Optional[int] = None
) -> float:
    """Calculate strategic vulnerability score for a race.

    Hybrid score factors (0-100 scale):
    1. Margin tightness (35% weight) - tighter margins = higher vulnerability
    2. Swing potential (25% weight) - how many votes could change outcome
    3. Turnout factor (15% weight) - smaller electorates = more volatile
    4. Undervote factor (15% weight) - high undervotes indicate voter ambivalence
    5. Category multiplier (10% weight) - flip opportunity vs retention risk

    Args:
        margin_pct: Vote margin as percentage
        total_votes: Total votes cast in race
        winner_party: Winning candidate's party (D, R, or Other)
        county: County name
        under_votes: Ballots cast but left blank (optional)
        total_ballots_cast: Total ballots in the race (optional)

    Returns:
        Vulnerability score (0-100, higher = more vulnerable)
    """
    # Normalize party
    normalized_party = normalize_party(winner_party)

    # 1. Margin tightness (35% weight)
    # Inverted sigmoid: tight margins get high scores
    # 0% margin = 100, 50% margin = ~0
    if margin_pct <= 0:
        margin_component = 100.0
    elif margin_pct >= 50:
        margin_component = 0.0
    else:
        # Non-linear: emphasize very tight races (< 5%)
        margin_component = max(0, 100 * (1 - (margin_pct / 50)))
        # Apply curve to emphasize tighter races
        if margin_pct < 5:
            margin_component = min(100, margin_component * 1.3)

    # 2. Swing potential (25% weight)
    # Tighter margins = higher swing potential (more vulnerable)
    # Inverted: 0% margin = 100, 5%+ margin = 0
    swing_potential = max(0, 100 - (margin_pct / 5) * 100)

    # 3. Turnout factor (15% weight)
    # Smaller electorates are more volatile
    # Benchmark: county-level races typically 5k-50k votes
    # <5k votes = vulnerable to small swings
    # >50k votes = more stable
    if total_votes < 5000:
        turnout_component = 80.0
    elif total_votes < 10000:
        turnout_component = 60.0
    elif total_votes < 25000:
        turnout_component = 40.0
    elif total_votes < 50000:
        turnout_component = 20.0
    else:
        turnout_component = 10.0

    # 4. Undervote factor (15% weight)
    # High undervotes = voter ambivalence = persuadable voters
    # Cap at 20% undervote for max score
    undervote_component = 0.0
    if under_votes is not None and total_ballots_cast is not None and total_ballots_cast > 0:
        undervote_pct = (under_votes / total_ballots_cast) * 100
        undervote_component = min(100, undervote_pct * 5)

    # 5. Category multiplier (10% weight)
    # Flip opportunities and retention risks warrant different weight
    # These are explicitly vulnerable categories
    if normalized_party == 'R':  # flip_opportunity
        category_multiplier = 1.0
    elif normalized_party == 'D':  # retention_risk
        category_multiplier = 1.0
    else:  # other
        category_multiplier = 0.7

    # Weighted composite score
    composite = (
        margin_component * 0.35 +
        swing_potential * 0.25 +
        turnout_component * 0.15 +
        undervote_component * 0.15
    )

    # Apply category multiplier to overall score
    final_score = composite * category_multiplier

    return round(min(100, max(0, final_score)), 1)


def get_vulnerability_scores(
    limit: int = 20,
    county: Optional[List[str]] = None,
    competitiveness: Optional[List[str]] = None,
    party: Optional[List[str]] = None,
    race_type: Optional[List[str]] = None,
) -> List[dict]:
    """Get races ranked by vulnerability score.

    Strategic vulnerability scoring for political analysis.
    Categories:
    - flip_opportunity: R winner with margin < 10%
    - retention_risk: D winner with margin < 10%

    Hybrid scoring factors:
    - Margin tightness (35%): how close the race was
    - Swing potential (25%): votes in dispute relative to margin
    - Turnout (15%): smaller electorates are more volatile
    - Undervote factor (15%): high undervotes indicate voter ambivalence
    - Category (10%): explicit vulnerability categories get full weight
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:

            # Build WHERE clause for SQL-filterable fields
            where_clause, params = build_where_clause(county=county, party=party)

            query = f"""
            SELECT
                r.id,
                r.race_title,
                r.county,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.party_coalition END) as winner_party_raw,
                r.total_votes_cast,
                r.under_votes,
                r.total_ballots_cast,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.total_votes END) as winner_votes,
                MAX(CASE WHEN c.is_winner = FALSE THEN c.total_votes END) as runnerup_votes
            FROM races r
            JOIN candidates c ON r.id = c.race_id
            {where_clause}
            GROUP BY r.id
            HAVING MAX(CASE WHEN c.is_winner = TRUE THEN c.total_votes END) IS NOT NULL
                AND MAX(CASE WHEN c.is_winner = FALSE THEN c.total_votes END) IS NOT NULL
            """

            cursor.execute(query, params)
            rows = cursor.fetchall()

    results = []
    for row in rows:
        total_votes = row['total_votes_cast'] or 0
        winner_votes = row['winner_votes'] or 0
        runnerup_votes = row['runnerup_votes'] or 0

        if total_votes == 0:
            continue

        vote_diff = winner_votes - runnerup_votes
        margin = (vote_diff / total_votes) * 100
        winner_party_raw = row['winner_party_raw'] or ''

        # Normalize party using existing function
        normalized_party = normalize_party(winner_party_raw)

        # Extract race type for filtering
        race_type_str = extract_race_type(row['race_title'])

        # Determine competitiveness band for filtering
        competitiveness_band = determine_competitiveness_band(margin)

        # Determine category based on winner party
        if normalized_party == 'R':
            category = 'flip_opportunity'
        elif normalized_party == 'D':
            category = 'retention_risk'
        else:
            category = 'other'

        # Calculate strategic vulnerability score with undervote data
        vuln_score = calculate_vulnerability_score(
            margin_pct=margin,
            total_votes=total_votes,
            winner_party=normalized_party,
            county=row['county'],
            under_votes=row['under_votes'],
            total_ballots_cast=row['total_ballots_cast']
        )

        results.append({
            'id': row['id'],
            'vulnerability_score': vuln_score,
            'category': category,
            'race_title': row['race_title'],
            'county': row['county'],
            'margin_pct': round(margin, 1),
            'race_type': race_type_str,
            'competitiveness_band': competitiveness_band,
        })

    # Apply post-query filters (calculated fields)
    if competitiveness:
        results = [r for r in results if r['competitiveness_band'] in competitiveness]

    if race_type:
        results = [r for r in results if r['race_type'] in race_type]

    # Sort by vulnerability score descending (highest vulnerability first)
    results.sort(key=lambda x: x['vulnerability_score'], reverse=True)

    # Apply limit
    return results[:limit]


def get_race_fusion_metrics(race_id: int) -> Optional[RaceFusionMetrics]:
    """Get fusion voting metrics for a specific race.

    Returns detailed party line breakdown and leverage analysis for winner and runner-up.
    Returns None if race not found.
    """
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:

            # Get race info and margin
            cursor.execute("""
                SELECT
                    r.id,
                    r.race_title,
                    MAX(CASE WHEN c.is_winner = TRUE THEN c.total_votes END) as winner_votes,
                    MAX(CASE WHEN c.is_winner = FALSE THEN c.total_votes END) as runnerup_votes
                FROM races r
                JOIN candidates c ON r.id = c.race_id
                WHERE r.id = %s
                GROUP BY r.id
            """, [race_id])

            race_row = cursor.fetchone()
            if not race_row:
                return None

            race_title = race_row["race_title"]
            winner_votes = race_row["winner_votes"] or 0
            runnerup_votes = race_row["runnerup_votes"] or 0
            margin_of_victory = winner_votes - runnerup_votes

            # Get all candidates with party line breakdowns
            cursor.execute("""
                SELECT
                    c.id as candidate_id,
                    c.name,
                    c.total_votes,
                    c.is_winner,
                    pl.party,
                    pl.votes
                FROM candidates c
                JOIN party_lines pl ON c.id = pl.candidate_id
                WHERE c.race_id = %s
                ORDER BY c.total_votes DESC, pl.votes DESC
            """, [race_id])

            candidate_rows = cursor.fetchall()

    if not candidate_rows:
        return None

    # Group party lines by candidate
    candidates_data = {}
    for row in candidate_rows:
        candidate_id = row["candidate_id"]
        if candidate_id not in candidates_data:
            candidates_data[candidate_id] = {
                "name": row["name"],
                "total_votes": row["total_votes"],
                "is_winner": row["is_winner"],
                "party_lines": []
            }
        candidates_data[candidate_id]["party_lines"].append({
            "party": row["party"],
            "votes": row["votes"]
        })

    # Process winner and runner-up
    candidates_list = list(candidates_data.values())
    if not candidates_list:
        return None

    winner_data = next((c for c in candidates_list if c["is_winner"]), None)
    runner_up_data = next((c for c in candidates_list if not c["is_winner"]), None)

    if not winner_data:
        return None

    def build_candidate_metrics(cand_data: Dict[str, Any]) -> CandidateFusionMetrics:
        """Build fusion metrics for a candidate."""
        total_votes = cand_data["total_votes"]
        party_lines = []
        main_party_votes = 0
        minor_party_votes = 0

        for pl in cand_data["party_lines"]:
            party = pl["party"]
            votes = pl["votes"]
            share_pct = (votes / total_votes * 100) if total_votes > 0 else 0.0

            party_lines.append(PartyLineBreakdown(
                party=party,
                votes=votes,
                share_pct=round(share_pct, 2)
            ))

            if party in MAIN_PARTIES:
                main_party_votes += votes
            else:
                minor_party_votes += votes

        minor_party_share = (minor_party_votes / total_votes) if total_votes > 0 else 0.0

        return CandidateFusionMetrics(
            candidate_name=cand_data["name"],
            party_lines=party_lines,
            main_party_votes=main_party_votes,
            minor_party_votes=minor_party_votes,
            minor_party_share=round(minor_party_share, 4)
        )

    winner_metrics = build_candidate_metrics(winner_data)
    runner_up_metrics = build_candidate_metrics(runner_up_data) if runner_up_data else None

    # Calculate leverage
    winner_leverage = None
    runner_up_leverage = None
    decisive_minor_party = None

    if margin_of_victory > 0:
        winner_leverage = winner_metrics.minor_party_votes / margin_of_victory
        if runner_up_metrics:
            runner_up_leverage = runner_up_metrics.minor_party_votes / margin_of_victory

        # Identify decisive minor party if leverage > 1.0
        if winner_leverage > 1.0:
            # Find the minor party that contributed most to winner
            minor_party_lines = [pl for pl in winner_metrics.party_lines if pl.party not in MAIN_PARTIES]
            if minor_party_lines:
                decisive_minor_party = max(minor_party_lines, key=lambda x: x.votes).party

    return RaceFusionMetrics(
        race_id=race_id,
        race_title=race_title,
        margin_of_victory=margin_of_victory,
        winner_metrics=winner_metrics,
        runner_up_metrics=runner_up_metrics,
        winner_leverage=round(winner_leverage, 4) if winner_leverage is not None else None,
        runner_up_leverage=round(runner_up_leverage, 4) if runner_up_leverage is not None else None,
        decisive_minor_party=decisive_minor_party
    )
