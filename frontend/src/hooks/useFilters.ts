import { useState, useEffect } from 'react';

const parseFiltersFromURL = (): Record<string, string> => {
  const params = new URLSearchParams(window.location.search);
  const filters: Record<string, string> = {};
  const dangerousKeys = ['__proto__', 'constructor', 'prototype'];

  params.forEach((value, key) => {
    if (value && !dangerousKeys.includes(key)) {
      filters[key] = value;
    }
  });

  return filters;
};

const syncFiltersToURL = (filters: Record<string, string>) => {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });

  const newURL = params.toString()
    ? `${window.location.pathname}?${params.toString()}`
    : window.location.pathname;

  window.history.replaceState({}, '', newURL);
};

export const useFilters = () => {
  const [filters, setFilters] = useState<Record<string, string>>(() => parseFiltersFromURL());

  useEffect(() => {
    syncFiltersToURL(filters);
  }, [filters]);

  const updateFilter = (key: string, value: string) => {
    setFilters((prev) => {
      if (!value) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { [key]: _, ...rest } = prev;
        return rest;
      }
      return {
        ...prev,
        [key]: value,
      };
    });
  };

  const clearFilters = () => {
    setFilters({});
  };

  return { filters, updateFilter, clearFilters };
};
