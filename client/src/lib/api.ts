/**
 * Central API configuration
 * Supports both VITE_API_BASE (Vite) and NEXT_PUBLIC_API_BASE (Next.js compatibility)
 */
const API_BASE =
  import.meta.env.VITE_API_BASE ||
  import.meta.env.NEXT_PUBLIC_API_BASE ||
  '';

/**
 * Build absolute API URL from relative path
 * @param path - Relative API path (e.g., "/api/auth/status")
 * @returns Absolute URL if API_BASE is set, otherwise returns path as-is (dev fallback)
 */
export function apiUrl(path: string): string {
  if (!API_BASE) return path; // dev fallback (relative)
  
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

/**
 * Supabase configuration
 * Supports both VITE_* (Vite) and NEXT_PUBLIC_* (Next.js compatibility)
 */
export const SUPABASE_URL =
  import.meta.env.VITE_SUPABASE_URL ||
  import.meta.env.NEXT_PUBLIC_SUPABASE_URL ||
  '';

export const SUPABASE_ANON_KEY =
  import.meta.env.VITE_SUPABASE_ANON_KEY ||
  import.meta.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  '';

