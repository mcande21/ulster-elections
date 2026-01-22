"""Race data API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import RaceData, StatsResponse, FilterOptions, RaceFusionMetrics, VulnerabilityScore
from ..services.database import get_races, get_stats, get_filter_options, get_race_fusion_metrics, get_vulnerability_scores


router = APIRouter(prefix="/api", tags=["races"])


@router.get("/races", response_model=List[RaceData])
async def list_races(
    county: Optional[str] = Query(None, description="Comma-separated counties"),
    competitiveness: Optional[str] = Query(None, description="Comma-separated competitiveness levels"),
    party: Optional[str] = Query(None, description="Comma-separated parties"),
    raceType: Optional[str] = Query(None, description="Comma-separated race types"),
    sort: str = Query("margin_pct", description="Sort field"),
    order: str = Query("asc", description="Sort order (asc/desc)"),
):
    """Get race data with filtering and sorting.

    Multi-select parameters are comma-separated:
    - county: e.g., "Ulster,Dutchess"
    - competitiveness: e.g., "Thin,Lean"
    - party: e.g., "D,R"
    - raceType: e.g., "Supervisor,Council"
    """
    # Parse comma-separated query params
    county_list = county.split(",") if county else None
    comp_list = competitiveness.split(",") if competitiveness else None
    party_list = party.split(",") if party else None
    race_type_list = raceType.split(",") if raceType else None

    races = get_races(
        county=county_list,
        competitiveness=comp_list,
        party=party_list,
        race_type=race_type_list,
        sort=sort,
        order=order,
    )

    return races


@router.get("/stats", response_model=StatsResponse)
async def get_statistics(
    county: Optional[str] = Query(None, description="Comma-separated counties"),
    competitiveness: Optional[str] = Query(None, description="Comma-separated competitiveness levels"),
    party: Optional[str] = Query(None, description="Comma-separated parties"),
    raceType: Optional[str] = Query(None, description="Comma-separated race types"),
):
    """Get summary statistics with same filtering as races endpoint."""
    # Parse comma-separated query params
    county_list = county.split(",") if county else None
    comp_list = competitiveness.split(",") if competitiveness else None
    party_list = party.split(",") if party else None
    race_type_list = raceType.split(",") if raceType else None

    stats = get_stats(
        county=county_list,
        competitiveness=comp_list,
        party=party_list,
        race_type=race_type_list,
    )

    return stats


@router.get("/filters", response_model=FilterOptions)
async def get_filters():
    """Get available filter options."""
    return get_filter_options()


@router.get("/races/vulnerability", response_model=List[VulnerabilityScore])
async def get_vulnerability(
    limit: int = Query(20, description="Number of races to return"),
    county: Optional[str] = Query(None, description="Comma-separated counties"),
    competitiveness: Optional[str] = Query(None, description="Comma-separated competitiveness levels"),
    party: Optional[str] = Query(None, description="Comma-separated parties"),
    raceType: Optional[str] = Query(None, description="Comma-separated race types"),
):
    """Get races ranked by vulnerability score, with optional filters."""
    # Parse comma-separated query params
    county_list = county.split(",") if county else None
    comp_list = competitiveness.split(",") if competitiveness else None
    party_list = party.split(",") if party else None
    race_type_list = raceType.split(",") if raceType else None

    return get_vulnerability_scores(
        limit=limit,
        county=county_list,
        competitiveness=comp_list,
        party=party_list,
        race_type=race_type_list,
    )


@router.get("/races/{race_id}/fusion", response_model=RaceFusionMetrics)
async def get_fusion_metrics(race_id: int):
    """Get fusion voting metrics for a specific race."""
    metrics = get_race_fusion_metrics(race_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Race not found")
    return metrics
