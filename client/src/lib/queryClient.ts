import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { apiUrl } from "./api";
import { ENDPOINTS } from "./endpoints";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    const error = new Error(`${res.status}: ${text}`);
    console.warn('API request failed:', res.status, text);
    throw error;
  }
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const sessionId = getSessionId();
  
  // Convert relative URL to absolute using API_BASE
  const absoluteUrl = apiUrl(url);
  
  // Add session_id as query param if available
  const urlWithSession = sessionId 
    ? `${absoluteUrl}${absoluteUrl.includes("?") ? "&" : "?"}session_id=${encodeURIComponent(sessionId)}`
    : absoluteUrl;
  
  const res = await fetch(urlWithSession, {
    method,
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  if (res.status === 401) {
    // Redirect to login on 401
    window.location.href = '/auth/google';
    throw new Error('Unauthorized');
  }

  await throwIfResNotOk(res);
  return res;
}

// Store session_id in localStorage for cross-origin support
const SESSION_ID_KEY = "session_id";

export function getSessionId(): string | null {
  // First check URL params (from OAuth redirect)
  const urlParams = new URLSearchParams(window.location.search);
  const sessionIdFromUrl = urlParams.get("session_id");
  if (sessionIdFromUrl) {
    // Store it in localStorage and clean up URL
    localStorage.setItem(SESSION_ID_KEY, sessionIdFromUrl);
    window.history.replaceState({}, "", window.location.pathname);
    return sessionIdFromUrl;
  }
  // Otherwise get from localStorage
  return localStorage.getItem(SESSION_ID_KEY);
}

export function clearSessionId(): void {
  localStorage.removeItem(SESSION_ID_KEY);
}

type UnauthorizedBehavior = "returnNull" | "throw";

// Check if queryKey represents a triage request
function isTriageRequest(queryKey: unknown[]): boolean {
  return queryKey.length >= 2 && 
         queryKey[0] === 'emails' && 
         typeof queryKey[1] === 'object' && 
         queryKey[1] !== null &&
         'label' in (queryKey[1] as Record<string, unknown>);
}

export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const sessionId = getSessionId();
    
    // Handle triage endpoint (POST /triage - NO /api prefix per backend)
    if (isTriageRequest(queryKey)) {
      const params = queryKey[1] as { label: string; pageToken?: string };
      const triageUrl = apiUrl(ENDPOINTS.triage);
      const urlWithSession = sessionId 
        ? `${triageUrl}${triageUrl.includes("?") ? "&" : "?"}session_id=${encodeURIComponent(sessionId)}`
        : triageUrl;
      
      const res = await fetch(urlWithSession, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          label: params.label,
          pageToken: params.pageToken,
        }),
        credentials: "include",
      });

      if (res.status === 401) {
        if (unauthorizedBehavior === "returnNull") {
          return null;
        }
        // Redirect to login on 401
        window.location.href = '/auth/google';
        throw new Error('Unauthorized');
      }

      await throwIfResNotOk(res);
      return await res.json();
    }
    
    // Default: GET request for other endpoints
    // Query key can be array like ["/api/auth/status"] or [ENDPOINTS.authStatus]
    // If first element is a string starting with '/', treat as path; otherwise join
    const relativeUrl = typeof queryKey[0] === 'string' && queryKey[0].startsWith('/')
      ? queryKey[0]
      : queryKey.join("/") as string;
    const absoluteUrl = apiUrl(relativeUrl);
    
    // Add session_id as query param if available
    const urlWithSession = sessionId 
      ? `${absoluteUrl}${absoluteUrl.includes("?") ? "&" : "?"}session_id=${encodeURIComponent(sessionId)}`
      : absoluteUrl;
    
    const res = await fetch(urlWithSession, {
      credentials: "include",
    });

    if (res.status === 401) {
      if (unauthorizedBehavior === "returnNull") {
        return null;
      }
      // Redirect to login on 401
      window.location.href = '/auth/google';
      throw new Error('Unauthorized');
    }

    await throwIfResNotOk(res);
    return await res.json();
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});
