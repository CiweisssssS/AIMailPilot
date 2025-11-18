import { QueryClient, QueryFunction } from "@tanstack/react-query";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const sessionId = getSessionId();
  
  // Add session_id as query param if available
  const urlWithSession = sessionId 
    ? `${url}${url.includes("?") ? "&" : "?"}session_id=${encodeURIComponent(sessionId)}`
    : url;
  
  const res = await fetch(urlWithSession, {
    method,
    headers: data ? { "Content-Type": "application/json" } : {},
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

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
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const url = queryKey.join("/") as string;
    const sessionId = getSessionId();
    
    // Add session_id as query param if available
    const urlWithSession = sessionId 
      ? `${url}${url.includes("?") ? "&" : "?"}session_id=${encodeURIComponent(sessionId)}`
      : url;
    
    const res = await fetch(urlWithSession, {
      credentials: "include",
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
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
