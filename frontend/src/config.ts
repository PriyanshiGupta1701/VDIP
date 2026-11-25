// Local development defaults; override via frontend/.env (VITE_API_BASE_URL, VITE_API_HOST)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
export const API_HOST = import.meta.env.VITE_API_HOST ?? "127.0.0.1:8000";
