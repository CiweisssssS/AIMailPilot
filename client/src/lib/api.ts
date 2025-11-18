/**
 * Central API configuration
 * Uses NEXT_PUBLIC_API_BASE environment variable for backend URL
 */
export const API_BASE = import.meta.env.NEXT_PUBLIC_API_BASE || "";

/**
 * Build absolute API URL from relative path
 * @param path - Relative API path (e.g., "/api/auth/status")
 * @returns Absolute URL (e.g., "https://aimailpilot-api.onrender.com/api/auth/status")
 */
export function apiUrl(path: string): string {
  // Remove leading slash if present to avoid double slashes
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  
  if (API_BASE) {
    // Ensure API_BASE doesn't end with slash
    const base = API_BASE.endsWith("/") ? API_BASE.slice(0, -1) : API_BASE;
    return `${base}/${cleanPath}`;
  }
  
  // Fallback to relative path if API_BASE not set (for local dev)
  return `/${cleanPath}`;
}

