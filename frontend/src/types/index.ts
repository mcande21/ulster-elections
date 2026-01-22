export interface Race {
  id: number;
  county: string;
  race_title: string;
  winner_name: string;
  winner_party: string;
  runner_up_name: string;
  runner_up_party: string;
  margin_pct: number;
  vote_diff: number;
  competitiveness_band: string;
  race_type: string;
}

export interface Stats {
  total: number;
  flipOpportunities: number;
  retentionRisks: number;
  closestMargin: number;
}

export interface FilterOptions {
  counties: string[];
  raceTypes: string[];
  parties: string[];
  competitivenessLevels: string[];
}
