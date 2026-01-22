"""PostgreSQL database query service."""

from typing import List, Optional, Dict, Any
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ..models.schemas import RaceData, StatsResponse, FilterOptions
from ..config import DATABASE_URL


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
