import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import type { TriageResponse, GmailEmail, AnalyzedEmail } from "@shared/schema";

// Cache key for analyzed emails
export const ANALYZED_EMAILS_CACHE_KEY = ["/api/analyzed-emails"];

// Gmail label types
export type GmailLabel = "IMPORTANT" | "CATEGORY_UPDATES" | "CATEGORY_PROMOTIONS";

// Map UI tab names to Gmail labels
export const LABEL_MAP: Record<string, GmailLabel> = {
  "Important": "IMPORTANT",
  "Updates": "CATEGORY_UPDATES",
  "Promotions": "CATEGORY_PROMOTIONS",
};

// Fetch Gmail emails using POST /api/triage
export function useGmailEmails(
  label: GmailLabel = "IMPORTANT",
  pageToken?: string,
  options?: { enabled?: boolean }
) {
  return useQuery<TriageResponse>({
    queryKey: ["emails", { label, pageToken }],
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

// Analyze emails with AI (legacy - may not be needed if triage already analyzes)
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
      // Invalidate all email queries
      queryClient.invalidateQueries({ queryKey: ["emails"] });
    },
  });
}

// Manually refresh emails
export function useRefreshEmails() {
  return useMutation({
    mutationFn: async () => {
      await queryClient.invalidateQueries({ queryKey: ["emails"] });
      return { success: true };
    },
  });
}
