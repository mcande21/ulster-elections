import axios from 'axios';
import type { RaceFusionMetrics } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
});

export async function getFusionMetrics(raceId: number): Promise<RaceFusionMetrics> {
  const response = await api.get(`/races/${raceId}/fusion`);
  return response.data;
}
