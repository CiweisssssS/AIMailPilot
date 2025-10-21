import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import type { FetchGmailResponse, TriageResponse, GmailEmail } from "@shared/schema";

// Fetch Gmail emails
export function useGmailEmails(maxResults = 50, options?: { enabled?: boolean }) {
  return useQuery<FetchGmailResponse>({
    queryKey: ["/api/fetch-gmail-emails", maxResults],
    refetchInterval: 60000, // Refetch every 60 seconds
    retry: 1,
    enabled: options?.enabled ?? true, // Default to enabled if not specified
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
    onSuccess: () => {
      // Invalidate and refetch
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
