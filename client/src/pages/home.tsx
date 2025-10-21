import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Sparkles } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";
import MailLayout from "@/components/mail-layout";
import EmailList from "@/components/email-list";
import { useGmailEmails, useAnalyzeEmails, useRefreshEmails } from "@/hooks/use-emails";
import { useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import type { GmailEmail, AnalyzedEmail } from "@shared/schema";

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
    queryKey: ["/api/auth/status"],
  });

  // State hooks
  const [selectedEmailId, setSelectedEmailId] = useState<string | undefined>();
  const [analyzedEmails, setAnalyzedEmails] = useState<AnalyzedEmail[]>([]);
  const { toast } = useToast();

  // Fetch Gmail emails (only if authenticated)
  const { data: gmailData, isLoading: emailsLoading, error: emailsError, refetch } = useGmailEmails(50);
  
  // Mutations
  const logoutMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("POST", "/api/auth/logout");
    },
    onSuccess: () => {
      refetchAuth();
    }
  });
  
  const analyzeMutation = useAnalyzeEmails();
  const refreshMutation = useRefreshEmails();

  // Auto-analyze emails when they are loaded (only if authenticated)
  useEffect(() => {
    if (authStatus?.authenticated && gmailData?.emails && gmailData.emails.length > 0 && analyzedEmails.length === 0 && !analyzeMutation.isPending) {
      analyzeMutation.mutate(gmailData.emails, {
        onSuccess: (data) => {
          setAnalyzedEmails(data.analyzed_emails);
        },
      });
    }
  }, [gmailData?.emails, authStatus?.authenticated]);

  // Event handlers
  const handleEmailClick = (email: GmailEmail) => {
    setSelectedEmailId(email.id);
  };

  const handleRefresh = async () => {
    try {
      setAnalyzedEmails([]);
      await refetch();
      toast({
        title: "Refreshed",
        description: "Emails refreshed successfully",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to refresh emails",
        variant: "destructive",
      });
    }
  };

  // Calculate summary statistics
  const summary = analyzedEmails.length > 0 ? {
    total: analyzedEmails.length,
    urgent: analyzedEmails.filter(e => e.priority.label === "P1 - Urgent").length,
    todo: analyzedEmails.filter(e => e.priority.label === "P2 - To-do").length,
    fyi: analyzedEmails.filter(e => e.priority.label === "P3 - FYI").length,
  } : { total: 0, urgent: 0, todo: 0, fyi: 0 };

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
                onClick={() => window.location.href = "/auth/google"}
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
      isAnalyzing={analyzeMutation.isPending}
    >
      <EmailList 
        emails={gmailData?.emails || []}
        selectedEmailId={selectedEmailId}
        onEmailClick={handleEmailClick}
        isLoading={emailsLoading}
        error={emailsError?.message || null}
      />
    </MailLayout>
  );
}
