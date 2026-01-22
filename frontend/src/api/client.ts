import axios from 'axios';
import type { RaceFusionMetrics, VulnerabilityScore } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
});

export async function getFusionMetrics(raceId: number): Promise<RaceFusionMetrics> {
  const response = await api.get(`/api/races/${raceId}/fusion`);
  return response.data;
}

export async function getVulnerabilityScores(limit: number = 20): Promise<VulnerabilityScore[]> {
  const response = await api.get(`/api/races/vulnerability`, {
    params: { limit }
  });
  return response.data;
}
