import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Race } from '../types';

export const useRaces = (filters?: Record<string, string>) => {
  return useQuery({
    queryKey: ['races', filters],
    queryFn: async () => {
      const params = new URLSearchParams(filters);
      const { data } = await api.get<Race[]>(`/api/races?${params}`);
      return data;
    },
    placeholderData: keepPreviousData,
  });
};
