"""Pydantic models for request/response validation."""

from typing import List, Optional
from pydantic import BaseModel


class RaceData(BaseModel):
    """Race data model matching frontend expectations."""
    id: int
    county: str
    race_title: str
    race_type: str
    winner_name: str
    winner_party: str
    winner_votes: int
    runner_up_name: str
    runner_up_party: str
    runner_up_votes: int
    total_votes: int
    margin_pct: float
    vote_diff: int
    competitiveness_band: str


class StatsResponse(BaseModel):
    """Summary statistics response."""
    total: int
    flipOpportunities: int
    retentionRisks: int
    closestMargin: Optional[float]


class FilterOptions(BaseModel):
    """Available filter options."""
    counties: List[str]
    raceTypes: List[str]
    parties: List[str]
    competitivenessLevels: List[str]


class UploadResponse(BaseModel):
    """PDF upload processing response."""
    success: bool
    message: str
    racesProcessed: Optional[int] = None
    errors: Optional[List[str]] = None


class PartyLineBreakdown(BaseModel):
    """Party line vote breakdown for a candidate."""
    party: str
    votes: int
    share_pct: float


class CandidateFusionMetrics(BaseModel):
    """Fusion voting metrics for a single candidate."""
    candidate_name: str
    party_lines: List[PartyLineBreakdown]
    main_party_votes: int
    minor_party_votes: int
    minor_party_share: float


class RaceFusionMetrics(BaseModel):
    """Fusion voting analysis for a race."""
    race_id: int
    race_title: str
    margin_of_victory: int
    winner_metrics: CandidateFusionMetrics
    runner_up_metrics: Optional[CandidateFusionMetrics] = None
    winner_leverage: Optional[float] = None
    runner_up_leverage: Optional[float] = None
    decisive_minor_party: Optional[str] = None


class VulnerabilityScore(BaseModel):
    """Race vulnerability scoring for strategic analysis."""
    id: int
    vulnerability_score: float
    category: str
    race_title: str
    county: str
    margin_pct: float
