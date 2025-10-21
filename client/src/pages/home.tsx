import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Mail, AlertCircle, CheckCircle2, Clock, Inbox, Sparkles } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

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

export default function Home() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzedEmails, setAnalyzedEmails] = useState<AnalyzedEmail[]>([]);
  const { toast } = useToast();

  const fetchEmailsMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/fetch-gmail-emails?maxResults=5");
      if (!response.ok) throw new Error("Failed to fetch emails");
      return response.json();
    },
    onSuccess: async (data) => {
      if (data.success && data.emails?.length > 0) {
        setIsAnalyzing(true);
        
        const analyzeResponse = await fetch("/api/analyze-emails", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ emails: data.emails })
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
        description: error.message || "Failed to fetch or analyze emails",
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

  if (analyzedEmails.length === 0 && !fetchEmailsMutation.isPending && !isAnalyzing) {
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
                  Connecting to Gmail...
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
