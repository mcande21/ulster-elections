import axios from 'axios';
import type { RaceFusionMetrics, VulnerabilityScore } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
});

interface VulnerabilityFilters {
  county?: string[];
  party?: string[];
  competitiveness?: string[];
  raceType?: string[];
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

  if (filters?.county?.length) params.county = filters.county.join(',');
  if (filters?.party?.length) params.party = filters.party.join(',');
  if (filters?.competitiveness?.length) params.competitiveness = filters.competitiveness.join(',');
  if (filters?.raceType?.length) params.raceType = filters.raceType.join(',');

  const response = await api.get('/api/races/vulnerability', { params });
  return response.data;
}
