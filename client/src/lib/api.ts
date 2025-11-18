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
 * 
 * Guards against numeric-only paths (e.g., "15") - they must be part of a full path.
 */
export function apiUrl(path: string): string {
  if (!API_BASE) return path; // dev fallback (relative)
  
  // Guard: if path is numeric-only, it's not a valid standalone path
  // This prevents paths like "15" from being treated as full URLs
  if (/^\d+$/.test(path)) {
    console.warn(`apiUrl: numeric-only path "${path}" detected. This should be part of a full API path.`);
    // Still return it, but log a warning
  }
  
  // Ensure path starts with /api/ if it doesn't already
  // This prevents numeric paths from being used directly
  if (!path.startsWith('/api/') && !path.startsWith('/oauth/') && !path.startsWith('/auth/') && !path.startsWith('/health')) {
    // If it's not a known API prefix and is numeric, it's likely an error
    if (/^\d+$/.test(path)) {
      throw new Error(`Invalid API path: "${path}". Numeric paths must be part of a full API endpoint.`);
    }
  }
  
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

