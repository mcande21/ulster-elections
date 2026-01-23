import axios from 'axios';
import type { RaceFusionMetrics, VulnerabilityScore } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const api = axios.create({
  baseURL: API_BASE,
});

interface VulnerabilityFilters {
  county?: string | string[];
  party?: string | string[];
  competitiveness?: string | string[];
  raceType?: string | string[];
}

// Helper to normalize filter values (handles both string and string[])
function normalizeFilter(value?: string | string[]): string | undefined {
  if (!value) return undefined;
  if (Array.isArray(value)) return value.length ? value.join(',') : undefined;
  return value;
}

export async function getFusionMetrics(raceId: number): Promise<RaceFusionMetrics> {
  const response = await api.get(`/api/races/${raceId}/fusion`);
  return response.data;
}

export async function getVulnerabilityScores(
  limit: number = 20,
  filters?: VulnerabilityFilters
): Promise<VulnerabilityScore[]> {
  const params: Record<string, string | number> = { limit };

  const county = normalizeFilter(filters?.county);
  const party = normalizeFilter(filters?.party);
  const competitiveness = normalizeFilter(filters?.competitiveness);
  const raceType = normalizeFilter(filters?.raceType);

  if (county) params.county = county;
  if (party) params.party = party;
  if (competitiveness) params.competitiveness = competitiveness;
  if (raceType) params.raceType = raceType;

  const response = await api.get('/api/races/vulnerability', { params });
  return response.data;
}
