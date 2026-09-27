/** Production: empty string → same-origin via reverse proxy. Dev: local API default. */
export const API_BASE =
  import.meta.env.VITE_API_BASE ??
  (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');
