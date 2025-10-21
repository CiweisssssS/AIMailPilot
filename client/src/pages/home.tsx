import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Mail, AlertCircle, CheckCircle2, Clock, Inbox, Sparkles, LogOut } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

interface Email {
  id: string;
  subject: string;
  from_: string;
  to: string[];
  date: string;
  snippet: string;
  body: string;
}

interface Task {
  title: string;
  owner: string;
  due: string | null;
  type: string;
}

interface AnalyzedEmail extends Email {
  priority: {
    label: string;
    score: number;
    reasons: string[];
  };
  summary: string;
  tasks: Task[];
}

interface AuthStatus {
  authenticated: boolean;
  user?: {
    email: string;
    name: string;
    picture?: string;
  };
}

export default function Home() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzedEmails, setAnalyzedEmails] = useState<AnalyzedEmail[]>([]);
  const { toast } = useToast();

  // Check authentication status
  const { data: authStatus, isLoading: authLoading, refetch: refetchAuth } = useQuery<AuthStatus>({
    queryKey: ["/api/auth/status"],
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("POST", "/api/auth/logout");
    },
    onSuccess: () => {
      refetchAuth();
      setAnalyzedEmails([]);
      toast({
        title: "Logged out",
        description: "You have been logged out successfully",
      });
    }
  });

  const fetchEmailsMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/fetch-gmail-emails?maxResults=5", {
        credentials: "include"
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to fetch emails");
      }
      return response.json();
    },
    onSuccess: async (data) => {
      if (data.success && data.emails?.length > 0) {
        setIsAnalyzing(true);
        
        const analyzeResponse = await fetch("/api/analyze-emails", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ emails: data.emails }),
          credentials: "include"
        });

        if (!analyzeResponse.ok) throw new Error("Failed to analyze emails");
        
        const analyzed = await analyzeResponse.json();
        const emailsWithAnalysis = data.emails.map((email: Email, index: number) => ({
          ...email,
          priority: analyzed.priorities?.[index] || { label: "P3", score: 0.25, reasons: ["Classification unavailable"] },
          summary: analyzed.summaries?.[index] || "Summary unavailable",
          tasks: analyzed.tasks?.[index] || []
        }));

        setAnalyzedEmails(emailsWithAnalysis);
        setIsAnalyzing(false);
        
        toast({
          title: "Analysis complete",
          description: `Analyzed ${data.emails.length} emails from your inbox`,
        });
      } else {
        toast({
          title: "No emails found",
          description: "Your inbox appears to be empty",
          variant: "destructive"
        });
      }
    },
    onError: (error: Error) => {
      setIsAnalyzing(false);
      toast({
        title: "Error",
        description: error.message || "Failed to fetch or analyze emails. Please make sure you're logged in.",
        variant: "destructive"
      });
    }
  });

  const getPriorityConfig = (label: string) => {
    switch (label) {
      case "P1":
        return {
          variant: "destructive" as const,
          icon: AlertCircle,
          text: "P1 Urgent",
          description: "Requires immediate action",
          bgClass: "bg-destructive/10 border-l-4 border-destructive"
        };
      case "P2":
        return {
          variant: "secondary" as const,
          icon: Clock,
          text: "P2 To-do",
          description: "Needs attention",
          bgClass: "bg-yellow-500/10 border-l-4 border-yellow-500"
        };
      default:
        return {
          variant: "outline" as const,
          icon: CheckCircle2,
          text: "P3 FYI",
          description: "For information",
          bgClass: "bg-muted/30 border-l-4 border-muted-foreground/30"
        };
    }
  };

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
            <CardTitle className="text-3xl font-bold">AI Email Intelligence</CardTitle>
            <CardDescription className="text-base">
              Analyze your Gmail inbox with GPT-4o-mini for priority classification, summaries, and task extraction
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
              <div className="text-center space-y-2">
                <div className="mx-auto w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <AlertCircle className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-semibold text-sm">Priority Detection</h3>
                <p className="text-xs text-muted-foreground">P1/P2/P3 classification</p>
              </div>
              <div className="text-center space-y-2">
                <div className="mx-auto w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <Mail className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-semibold text-sm">Smart Summaries</h3>
                <p className="text-xs text-muted-foreground">One-sentence overviews</p>
              </div>
              <div className="text-center space-y-2">
                <div className="mx-auto w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-semibold text-sm">Task Extraction</h3>
                <p className="text-xs text-muted-foreground">[verb + object + owner + due]</p>
              </div>
            </div>
            
            <div className="bg-muted/50 p-4 rounded-lg border">
              <p className="text-sm text-center mb-4">
                Sign in with Google to access your Gmail and start analyzing
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

            <div className="text-center space-y-2">
              <p className="text-xs text-muted-foreground">
                We'll request read-only access to your Gmail to fetch and analyze your inbox emails
              </p>
              <a 
                href="/setup-help" 
                className="text-xs text-primary hover:underline inline-flex items-center gap-1"
                data-testid="link-setup-help"
              >
                Need help setting up OAuth? View setup guide →
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (analyzedEmails.length === 0 && !fetchEmailsMutation.isPending && !isAnalyzing) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-primary/5 to-purple-500/5 flex items-center justify-center p-6">
        <Card className="w-full max-w-2xl">
          <CardHeader className="text-center space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex-1" />
              <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-primary" />
              </div>
              <div className="flex-1 flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => logoutMutation.mutate()}
                  disabled={logoutMutation.isPending}
                  data-testid="button-logout"
                >
                  <LogOut className="h-4 w-4 mr-2" />
                  Logout
                </Button>
              </div>
            </div>
            <CardTitle className="text-3xl font-bold">Welcome, {authStatus.user?.name}!</CardTitle>
            <CardDescription className="text-base">
              Ready to analyze your Gmail inbox with AI
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <Button 
              className="w-full" 
              size="lg"
              onClick={() => fetchEmailsMutation.mutate()}
              disabled={fetchEmailsMutation.isPending}
              data-testid="button-analyze-inbox"
            >
              {fetchEmailsMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Fetching emails...
                </>
              ) : (
                <>
                  <Inbox className="mr-2 h-5 w-5" />
                  Analyze My Inbox
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isAnalyzing) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center space-y-4">
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <div className="text-center">
                <h3 className="font-semibold">Analyzing emails...</h3>
                <p className="text-sm text-muted-foreground">GPT-4o-mini is processing your inbox</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Sparkles className="h-6 w-6 text-primary" />
            <h1 className="font-bold text-xl">Email Intelligence</h1>
          </div>
          <div className="flex items-center gap-2">
            {authStatus.user && (
              <span className="text-sm text-muted-foreground mr-2">
                {authStatus.user.email}
              </span>
            )}
            <Button 
              variant="outline" 
              onClick={() => {
                setAnalyzedEmails([]);
                fetchEmailsMutation.mutate();
              }}
              data-testid="button-new-analysis"
            >
              <Inbox className="mr-2 h-4 w-4" />
              New Analysis
            </Button>
            <Button
              variant="ghost"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
              data-testid="button-logout"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="container max-w-5xl px-6 py-8 space-y-6">
        {analyzedEmails.map((email) => {
          const priorityConfig = getPriorityConfig(email.priority.label);
          const PriorityIcon = priorityConfig.icon;

          return (
            <Card key={email.id} className="overflow-hidden" data-testid={`card-email-${email.id}`}>
              <div className={`p-6 ${priorityConfig.bgClass}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant={priorityConfig.variant} className="flex items-center gap-1" data-testid={`badge-priority-${email.priority.label}`}>
                        <PriorityIcon className="h-3 w-3" />
                        {priorityConfig.text}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {priorityConfig.description}
                      </span>
                    </div>
                    <h2 className="font-semibold text-lg truncate" data-testid="text-email-subject">{email.subject}</h2>
                    <p className="text-sm text-muted-foreground">
                      From: {email.from_} • {new Date(email.date).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-primary">{Math.round(email.priority.score * 100)}%</div>
                    <div className="text-xs text-muted-foreground">Confidence</div>
                  </div>
                </div>
                {email.priority.reasons.length > 0 && (
                  <div className="mt-3 text-sm text-muted-foreground">
                    <span className="font-medium">Reason:</span> {email.priority.reasons[0]}
                  </div>
                )}
              </div>

              <CardContent className="p-6 space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <h3 className="font-semibold">Summary</h3>
                    </div>
                    <p className="text-sm leading-relaxed" data-testid="text-email-summary">
                      {email.summary}
                    </p>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center gap-2 justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                        <h3 className="font-semibold">Tasks</h3>
                      </div>
                      {email.tasks.length > 0 && (
                        <Badge variant="secondary" data-testid="badge-task-count">
                          {email.tasks.length} {email.tasks.length === 1 ? 'task' : 'tasks'}
                        </Badge>
                      )}
                    </div>
                    
                    {email.tasks.length > 0 ? (
                      <ul className="space-y-2">
                        {email.tasks.map((task, index) => (
                          <li 
                            key={index} 
                            className="text-sm p-3 rounded-lg bg-muted/50 hover-elevate"
                            data-testid={`task-item-${index}`}
                          >
                            <div className="font-medium mb-1">{task.title}</div>
                            <div className="flex items-center gap-3 text-xs text-muted-foreground">
                              <span>Owner: {task.owner}</span>
                              {task.due && (
                                <span>Due: {new Date(task.due).toLocaleDateString()}</span>
                              )}
                              <Badge variant="outline" className="text-xs">
                                {task.type}
                              </Badge>
                            </div>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="text-sm text-muted-foreground italic p-3 bg-muted/30 rounded-lg">
                        No actionable tasks detected
                      </div>
                    )}
                  </div>
                </div>

                <details className="group">
                  <summary className="cursor-pointer text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                    View full email
                  </summary>
                  <div className="mt-3 p-4 bg-muted/30 rounded-lg text-sm max-h-64 overflow-y-auto">
                    <pre className="whitespace-pre-wrap font-sans">{email.snippet}</pre>
                  </div>
                </details>
              </CardContent>
            </Card>
          );
        })}
      </main>
    </div>
  );
}
