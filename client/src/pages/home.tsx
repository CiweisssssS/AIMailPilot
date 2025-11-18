import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Sparkles } from "lucide-react";
import { apiRequest, queryClient, clearSessionId, getSessionId } from "@/lib/queryClient";
import { ENDPOINTS } from "@/lib/endpoints";
import MailLayout from "@/components/mail-layout";
import EmailList from "@/components/email-list";
import EmailDetail from "@/components/email-detail";
import { useGmailEmails, useAnalyzeEmails, useRefreshEmails, useAnalyzedEmails, ANALYZED_EMAILS_CACHE_KEY, GmailLabel, LABEL_MAP, useMarkTaskViewed } from "@/hooks/use-emails";
import { useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import type { AnalyzedEmail } from "@shared/schema";

interface AuthStatus {
  authenticated: boolean;
  user?: {
    email: string;
    name: string;
    picture?: string;
  };
}

export default function Home() {
  // ALL HOOKS MUST BE AT THE TOP - React Rules of Hooks
  
  // Check authentication status
  const { data: authStatus, isLoading: authLoading, refetch: refetchAuth } = useQuery<AuthStatus>({
    queryKey: [ENDPOINTS.authStatus],
  });
  
  // Extract session_id from URL on mount (from OAuth callback) and refetch auth
  useEffect(() => {
    const sessionId = getSessionId(); // This will extract from URL and store in localStorage
    if (sessionId) {
      // If we got a session_id from URL, refetch auth status
      refetchAuth();
    }
  }, [refetchAuth]);

  // State hooks
  const [selectedEmailId, setSelectedEmailId] = useState<string | undefined>();
  const [selectedTaskId, setSelectedTaskId] = useState<{ emailId: string; taskIndex: number } | undefined>();
  const [currentLabel, setCurrentLabel] = useState<GmailLabel>("IMPORTANT");
  const { toast } = useToast();
  
  // Fetch Inbox Reminder tasks using GET /api/triage (returns { summary, items })
  const { data: triageData, isLoading: emailsLoading, error: emailsError, refetch: refetchTriage } = useGmailEmails(
    undefined, // label not used
    undefined, // pageToken not used
    {
      enabled: authStatus?.authenticated === true,
    }
  );

  // Extract items from triage response (new API contract)
  const triageItems = triageData?.items || [];
  
  // Convert items to AnalyzedEmail format for backward compatibility with components
  const analyzedEmails: AnalyzedEmail[] = triageItems.map((item: any) => ({
    id: item.message_id,
    threadId: item.thread_id,
    from_name: item.from_name,
    from_email: item.from_email,
    from: item.from_email,
    subject: item.subject,
    date: item.date,
    snippet: item.snippet,
    body_html: item.body_html,
    body_text: item.body_text,
    summary: item.snippet,
    priority: { 
      label: item.priority === "urgent" ? "P1" : item.priority === "todo" ? "P2" : "P3",
      score: 0.0,
      reasons: []
    },
    tasks: [{ title: item.title, type: "action" }],
    task_extracted: item.title,
    is_flagged: false,
    task_id: item.task_id
  }));
  
  // Mutations
  const logoutMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("POST", ENDPOINTS.logout);
    },
    onSuccess: () => {
      // Clear all data on logout
      queryClient.setQueryData(ANALYZED_EMAILS_CACHE_KEY, []);
      setSelectedEmailId(undefined);
      // Clear session from localStorage
      clearSessionId();
      refetchAuth();
    }
  });
  
  const analyzeMutation = useAnalyzeEmails();
  const refreshMutation = useRefreshEmails();

  // Triage endpoint already returns analyzed emails, so no need for separate analysis step
  // But we can still show loading/error states
  useEffect(() => {
    if (emailsError) {
      console.error("Failed to fetch emails:", emailsError);
      toast({
        title: "Failed to Load Emails",
        description: emailsError.message || "Failed to fetch emails. Please try refreshing.",
        variant: "destructive",
      });
    }
  }, [emailsError, toast]);

  // Log triage call after auth success for verification
  useEffect(() => {
    if (authStatus?.authenticated && !emailsLoading && triageData) {
      console.log(`[API] Triage call successful: ${triageData.analyzed_emails.length} emails loaded`);
    }
  }, [authStatus?.authenticated, emailsLoading, triageData]);

  // Task state mutations
  const markTaskViewedMutation = useMarkTaskViewed();

  // Event handlers
  const handleEmailClick = (email: AnalyzedEmail) => {
    setSelectedEmailId(email.id);
    
    // Mark task as viewed if task_id exists (fire-and-forget, optimistic UI)
    if ((email as any).task_id) {
      markTaskViewedMutation.mutate((email as any).task_id, {
        onError: (error) => {
          console.warn("Failed to mark task as viewed:", error);
          // Don't show error toast - this is fire-and-forget
        }
      });
    }
  };

  const handleBackToList = () => {
    setSelectedEmailId(undefined);
    setSelectedTaskId(undefined);
  };

  const handleTaskClick = (emailId: string, taskIndex: number) => {
    // Open the email in the middle column
    setSelectedEmailId(emailId);
    // Highlight the task card
    setSelectedTaskId({ emailId, taskIndex });
  };

  // Find selected email from analyzed emails
  const selectedEmail = selectedEmailId 
    ? analyzedEmails.find(e => e.id === selectedEmailId)
    : undefined;

  const handleRefresh = async () => {
    try {
      // Step 1: POST /api/refresh
      const refreshResponse = await apiRequest("POST", ENDPOINTS.refresh);
      if (!refreshResponse.ok) {
        const errorText = await refreshResponse.text();
        console.error(`[Refresh] POST /api/refresh failed: ${refreshResponse.status} | ${refreshResponse.url} | ${errorText}`);
        throw new Error(`Refresh failed: ${refreshResponse.status} ${errorText}`);
      }
      const refreshData = await refreshResponse.json();
      console.log(`[Refresh] Sync completed: mode=${refreshData.mode}, added_tasks=${refreshData.added_tasks}, total_new=${refreshData.total_new_count}`);
      
      // Step 2: GET /api/triage
      const triageResponse = await apiRequest("GET", ENDPOINTS.triage);
      if (!triageResponse.ok) {
        const errorText = await triageResponse.text();
        console.error(`[Refresh] GET /api/triage failed: ${triageResponse.status} | ${triageResponse.url} | ${errorText}`);
        throw new Error(`Triage fetch failed: ${triageResponse.status} ${errorText}`);
      }
      await refetchTriage();
      
      // Step 3: GET /api/tasks (optional, for Task & Schedule)
      try {
        const tasksResponse = await apiRequest("GET", `${ENDPOINTS.tasks}?state=open`);
        if (!tasksResponse.ok) {
          console.warn(`[Refresh] GET /api/tasks failed: ${tasksResponse.status}`);
        }
        queryClient.invalidateQueries({ queryKey: [ENDPOINTS.tasks] });
      } catch (tasksError) {
        console.warn("[Refresh] Failed to fetch tasks (non-critical):", tasksError);
      }
      
      toast({
        title: "Refreshed",
        description: `Synced ${refreshData.added_tasks} new tasks from ${refreshData.scanned_messages} emails`,
      });
    } catch (error: any) {
      console.error("[Refresh] Error:", error);
      const errorMessage = error?.message || "Failed to refresh emails";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  // Handle label/tab switching
  const handleLabelChange = (labelName: string) => {
    const label = LABEL_MAP[labelName];
    if (label) {
      setCurrentLabel(label);
      // Clear selected email when switching tabs
      setSelectedEmailId(undefined);
      setSelectedTaskId(undefined);
    }
  };

  // Use summary from triage response (new API contract)
  const summary = triageData?.summary || { total: 0, urgent: 0, todo: 0, fyi: 0 };

  // CONDITIONAL RENDERING - After all hooks
  // Show loading state while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Show login screen if not authenticated
  if (!authStatus?.authenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary/5 to-purple-500/5 flex items-center justify-center p-6">
        <Card className="w-full max-w-2xl">
          <CardHeader className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-primary" />
            </div>
            <CardTitle className="text-3xl font-bold">AIMailPilot</CardTitle>
            <CardDescription className="text-base">
              Your intelligent Gmail assistant with AI-powered email analysis
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="bg-muted/50 p-4 rounded-lg border">
              <p className="text-sm text-center mb-4">
                Sign in with Google to access your Gmail
              </p>
              <Button 
                className="w-full" 
                size="lg"
                onClick={() => {
                  // OAuth redirect goes through Vercel rewrites, so use relative path
                  window.location.href = "/auth/google";
                }}
                data-testid="button-google-login"
              >
                <svg className="mr-2 h-5 w-5" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Sign in with Google
              </Button>
            </div>

            <div className="text-center">
              <p className="text-xs text-muted-foreground">
                We'll request read-only access to your Gmail
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Show main application with three-column layout
  return (
    <MailLayout 
      userEmail={authStatus.user?.email}
      onLogout={() => logoutMutation.mutate()}
      onRefresh={handleRefresh}
      analyzedEmails={analyzedEmails}
      summary={summary}
      isAnalyzing={emailsLoading}
      onTaskClick={handleTaskClick}
      selectedTaskId={selectedTaskId}
      currentLabel={currentLabel}
      onLabelChange={handleLabelChange}
    >
      {selectedEmail ? (
        <EmailDetail 
          email={selectedEmail}
          onBack={handleBackToList}
        />
      ) : (
        <>
          {!emailsLoading && analyzedEmails.length === 0 && triageData?.message && (
            <div className="flex flex-col items-center justify-center h-full gap-4 px-4">
              <p className="text-sm text-muted-foreground text-center">
                {triageData.message}
              </p>
              <Button onClick={handleRefresh} variant="outline">
                Refresh
              </Button>
            </div>
          )}
          {(!triageData?.message || analyzedEmails.length > 0) && (
            <EmailList 
              emails={analyzedEmails}
              selectedEmailId={selectedEmailId}
              onEmailClick={handleEmailClick}
              isLoading={emailsLoading}
              error={emailsError?.message || null}
            />
          )}
        </>
      )}
    </MailLayout>
  );
}
