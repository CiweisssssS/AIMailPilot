import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { ENDPOINTS } from "@/lib/endpoints";
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

// Fetch Inbox Reminder tasks using GET /api/triage (returns { summary, items })
export function useGmailEmails(
  label?: GmailLabel, // Not used anymore, kept for backward compatibility
  pageToken?: string, // Not used anymore
  options?: { enabled?: boolean }
) {
  return useQuery<{ summary: { total: number; urgent: number; todo: number; fyi: number }; items: any[]; message?: string }>({
    queryKey: [ENDPOINTS.triage], // No params - backend doesn't use label/limit
    refetchInterval: 60000, // Refetch every 60 seconds
    retry: 1,
    enabled: options?.enabled ?? true,
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
// Note: This endpoint may not exist in backend - verify and remove if not needed
export function useAnalyzeEmails() {
  return useMutation({
    mutationFn: async (emails: GmailEmail[]) => {
      // Using triage endpoint with POST (standard method)
      const response = await apiRequest("POST", ENDPOINTS.triage, { 
        label: "IMPORTANT",
        emails 
      });
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

// Manually refresh emails - calls POST /api/refresh to sync
export function useRefreshEmails() {
  return useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", ENDPOINTS.refresh);
      const data = await response.json();
      return data;
    },
    onSuccess: () => {
      // Invalidate all email and task queries
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.triage] });
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.tasks] });
      queryClient.invalidateQueries({ queryKey: ["emails"] });
    },
  });
}

// Mark task as viewed
export function useMarkTaskViewed() {
  return useMutation({
    mutationFn: async (taskId: number) => {
      const response = await apiRequest("POST", ENDPOINTS.taskViewed(taskId));
      return await response.json();
    },
    onSuccess: () => {
      // Invalidate triage to remove from Inbox Reminder
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.triage] });
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.tasks] });
    },
  });
}

// Mark task as saved
export function useMarkTaskSaved() {
  return useMutation({
    mutationFn: async (taskId: number) => {
      const response = await apiRequest("POST", ENDPOINTS.taskSave(taskId));
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.tasks] });
    },
  });
}

// Mark task as done
export function useMarkTaskDone() {
  return useMutation({
    mutationFn: async (taskId: number) => {
      const response = await apiRequest("POST", ENDPOINTS.taskDone(taskId));
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.triage] });
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.tasks] });
    },
  });
}
