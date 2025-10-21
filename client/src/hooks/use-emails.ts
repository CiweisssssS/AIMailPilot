import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import type { FetchGmailResponse, TriageResponse, GmailEmail, AnalyzedEmail } from "@shared/schema";

// Cache key for analyzed emails
export const ANALYZED_EMAILS_CACHE_KEY = ["/api/analyzed-emails"];

// Fetch Gmail emails
export function useGmailEmails(maxResults = 50, options?: { enabled?: boolean }) {
  return useQuery<FetchGmailResponse>({
    queryKey: ["/api/fetch-gmail-emails", maxResults],
    refetchInterval: 60000, // Refetch every 60 seconds
    retry: 1,
    enabled: options?.enabled ?? true, // Default to enabled if not specified
  });
}

// Get analyzed emails from cache
export function useAnalyzedEmails() {
  return useQuery<AnalyzedEmail[]>({
    queryKey: ANALYZED_EMAILS_CACHE_KEY,
    initialData: [],
    staleTime: Infinity, // Don't auto-refetch, only update via mutations
  });
}

// Analyze emails with AI
export function useAnalyzeEmails() {
  return useMutation({
    mutationFn: async (emails: GmailEmail[]) => {
      const response = await apiRequest("POST", "/api/analyze-emails", { emails });
      const data = await response.json();
      return data as TriageResponse;
    },
    onSuccess: (data) => {
      // Store analyzed emails in cache
      queryClient.setQueryData(ANALYZED_EMAILS_CACHE_KEY, data.analyzed_emails);
      // Invalidate and refetch Gmail emails
      queryClient.invalidateQueries({ queryKey: ["/api/fetch-gmail-emails"] });
    },
  });
}

// Manually refresh emails
export function useRefreshEmails() {
  return useMutation({
    mutationFn: async () => {
      await queryClient.invalidateQueries({ queryKey: ["/api/fetch-gmail-emails"] });
      return { success: true };
    },
  });
}
