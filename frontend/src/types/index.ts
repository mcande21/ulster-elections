export interface Race {
  id: number;
  county: string;
  race_title: string;
  winner_name: string;
  winner_party: string;
  winner_votes: number;
  runner_up_name: string;
  runner_up_party: string;
  runner_up_votes: number;
  margin_pct: number;
  vote_diff: number;
  total_votes: number;
  competitiveness_band: string;
  race_type: string;
}

export interface Stats {
  total: number;
  flipOpportunities: number;
  retentionRisks: number;
  closestMargin: number | null;
}

export interface FilterOptions {
  counties: string[];
  raceTypes: string[];
  parties: string[];
  competitivenessLevels: string[];
}

export interface PartyLineBreakdown {
  party: string;
  votes: number;
  share_pct: number;
}

export interface CandidateFusionMetrics {
  candidate_name: string;
  party_lines: PartyLineBreakdown[];
  main_party_votes: number;
  minor_party_votes: number;
  minor_party_share: number;
}

export interface RaceFusionMetrics {
  race_id: number;
  race_title: string;
  margin_of_victory: number;
  winner_metrics: CandidateFusionMetrics;
  runner_up_metrics: CandidateFusionMetrics | null;
  winner_leverage: number | null;
  runner_up_leverage: number | null;
  decisive_minor_party: string | null;
}

export interface VulnerabilityScore {
  id: number;
  vulnerability_score: number;
  category: string;
  race_title: string;
  county: string;
  margin_pct: number;
}
