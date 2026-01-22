"""PostgreSQL database query service."""

from typing import List, Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ..models.schemas import RaceData, StatsResponse, FilterOptions
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
    # How many votes in dispute (both sides of margin)
    # More contested votes = more vulnerable
    swing_potential = min(100, (margin_pct / 5) * 100)  # Max at 5% margin

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


def get_vulnerability_scores(limit: int = 20) -> List[dict]:
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

            query = """
            SELECT
                r.id,
                r.race_title,
                r.county,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.party_coalition END) as winner_party,
                r.total_votes_cast,
                r.under_votes,
                r.total_ballots_cast,
                MAX(CASE WHEN c.is_winner = TRUE THEN c.total_votes END) as winner_votes,
                MAX(CASE WHEN c.is_winner = FALSE THEN c.total_votes END) as runnerup_votes
            FROM races r
            JOIN candidates c ON r.id = c.race_id
            GROUP BY r.id
            HAVING MAX(CASE WHEN c.is_winner = TRUE THEN c.total_votes END) IS NOT NULL
                AND MAX(CASE WHEN c.is_winner = FALSE THEN c.total_votes END) IS NOT NULL
            """

            cursor.execute(query)
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
        winner_party = row['winner_party'] or ''

        # Normalize party using existing function
        normalized_party = normalize_party(winner_party)

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
            'margin_pct': round(margin, 1)
        })

    # Sort by vulnerability score descending (highest vulnerability first)
    results.sort(key=lambda x: x['vulnerability_score'], reverse=True)

    # Apply limit
    return results[:limit]


def get_race_fusion_metrics(race_id: int) -> Optional[dict]:
    """Get fusion voting metrics for a specific race."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:

            # Get race info with winner and runner-up votes
            cursor.execute("""
                SELECT r.id, r.race_title,
                       (SELECT c.total_votes FROM candidates c
                        WHERE c.race_id = r.id AND c.is_winner = TRUE) as winner_votes,
                       (SELECT c.total_votes FROM candidates c
                        WHERE c.race_id = r.id AND c.is_winner = FALSE
                        ORDER BY c.total_votes DESC LIMIT 1) as runner_up_votes
                FROM races r WHERE r.id = %s
            """, (race_id,))
            race = cursor.fetchone()

            if not race:
                return None

            margin = (race['winner_votes'] or 0) - (race['runner_up_votes'] or 0)

            # Get candidates with party lines
            cursor.execute("""
                SELECT c.id, c.name, c.party_coalition, c.total_votes, c.is_winner,
                       pl.party as party_line, pl.votes as party_line_votes
                FROM candidates c
                LEFT JOIN party_lines pl ON pl.candidate_id = c.id
                WHERE c.race_id = %s
                ORDER BY c.total_votes DESC, pl.votes DESC
            """, (race_id,))
            rows = cursor.fetchall()

    # Group by candidate
    candidates = {}
    for row in rows:
        cid = row['id']
        if cid not in candidates:
            candidates[cid] = {
                'name': row['name'],
                'party': row['party_coalition'],
                'votes': row['total_votes'],
                'is_winner': row['is_winner'],
                'party_lines': []
            }
        if row['party_line'] and row['party_line_votes']:
            candidates[cid]['party_lines'].append({
                'party': row['party_line'],
                'votes': row['party_line_votes']
            })

    def calc_metrics(candidate):
        total_votes = candidate['votes']
        party_lines = candidate['party_lines']

        # Calculate shares
        for pl in party_lines:
            pl['share_pct'] = round((pl['votes'] / total_votes * 100) if total_votes > 0 else 0, 2)

        main_votes = sum(pl['votes'] for pl in party_lines if pl['party'] in MAIN_PARTIES)
        minor_votes = sum(pl['votes'] for pl in party_lines if pl['party'] not in MAIN_PARTIES)

        return {
            'candidate_name': candidate['name'],
            'party_lines': party_lines,
            'main_party_votes': main_votes,
            'minor_party_votes': minor_votes,
            'minor_party_share': round((minor_votes / total_votes * 100) if total_votes > 0 else 0, 2)
        }

    # Find winner and runner-up
    winner = runner_up = None
    for c in candidates.values():
        if c['is_winner']:
            winner = c
        elif runner_up is None or c['votes'] > runner_up['votes']:
            runner_up = c

    if not winner:
        return None

    winner_metrics = calc_metrics(winner)
    runner_up_metrics = calc_metrics(runner_up) if runner_up else None

    # Calculate leverage
    winner_leverage = runner_up_leverage = None
    decisive_party = None

    if margin > 0:
        winner_leverage = round(winner_metrics['minor_party_votes'] / margin, 2) if winner_metrics['minor_party_votes'] > 0 else 0
        if runner_up_metrics:
            runner_up_leverage = round(runner_up_metrics['minor_party_votes'] / margin, 2) if runner_up_metrics['minor_party_votes'] > 0 else 0

        # Find decisive minor party (one whose votes alone exceed margin)
        for pl in winner_metrics['party_lines']:
            if pl['party'] not in MAIN_PARTIES and pl['votes'] > margin:
                decisive_party = pl['party']
                break

    return {
        'race_id': race['id'],
        'race_title': race['race_title'],
        'margin_of_victory': margin,
        'winner_metrics': winner_metrics,
        'runner_up_metrics': runner_up_metrics,
        'winner_leverage': winner_leverage,
        'runner_up_leverage': runner_up_leverage,
        'decisive_minor_party': decisive_party
    }
