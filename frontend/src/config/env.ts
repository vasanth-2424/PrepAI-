const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '';
const apiBaseUrl = rawApiBaseUrl.trim().replace(/\/+$/, '');

export const env = {
  apiBaseUrl,
  isDev: import.meta.env.DEV,
} as const;
