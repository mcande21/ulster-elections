import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { FilterOptions } from '../types';

export const useFilterOptions = () => {
  return useQuery({
    queryKey: ['filterOptions'],
    queryFn: async () => {
      const { data } = await api.get<FilterOptions>('/api/filters');
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - filter options don't change often
  });
};
