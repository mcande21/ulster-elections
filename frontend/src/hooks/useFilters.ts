import { useState } from 'react';

export const useFilters = () => {
  const [filters, setFilters] = useState<Record<string, string>>({});

  const updateFilter = (key: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const clearFilters = () => {
    setFilters({});
  };

  return { filters, updateFilter, clearFilters };
};
