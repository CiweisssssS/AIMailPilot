import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Mail, MessageSquare, CheckCircle2, AlertCircle, Calendar, User } from "lucide-react";
import { processThreadRequestSchema, type ProcessThreadRequest, type ProcessThreadResponse, type ChatbotQAResponse, type ThreadResponse } from "@shared/schema";
import { format } from "date-fns";

export default function Home() {
  const { toast } = useToast();
  const [result, setResult] = useState<ProcessThreadResponse | null>(null);
  const [question, setQuestion] = useState("");

  const form = useForm<ProcessThreadRequest>({
    resolver: zodResolver(processThreadRequestSchema),
    defaultValues: {
      user_id: "demo_user",
      personalized_keywords: [],
      messages: [],
    },
  });

  const processMutation = useMutation({
    mutationFn: async (data: ProcessThreadRequest) => {
      const response = await fetch("http://localhost:8000/api/process-thread", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error("Failed to process thread");
      return response.json() as Promise<ProcessThreadResponse>;
    },
    onSuccess: (data) => {
      setResult(data);
      toast({
        title: "Thread processed successfully",
        description: `Priority: ${data.priority.label} (Score: ${data.priority.score.toFixed(2)})`,
      });
    },
    onError: (error) => {
      toast({
        title: "Error processing thread",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const qaMutation = useMutation({
    mutationFn: async ({ question, thread }: { question: string; thread: ThreadResponse }) => {
      const response = await fetch("http://localhost:8000/api/chatbot-qa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, thread }),
      });
      if (!response.ok) throw new Error("Failed to get answer");
      return response.json() as Promise<ChatbotQAResponse>;
    },
    onSuccess: (data) => {
      toast({
        title: "Answer received",
        description: `Sources: ${data.sources.join(", ")}`,
      });
    },
  });

  const onSubmit = (data: ProcessThreadRequest) => {
    processMutation.mutate(data);
  };

  const loadSampleData = () => {
    form.setValue("messages", [
      {
        id: "msg_001",
        thread_id: "thread_demo",
        date: "2025-10-01T10:45:00Z",
        from: "alice@company.com",
        to: ["you@company.com"],
        cc: ["team@company.com"],
        subject: "Project Kickoff - Action Required",
        body: "Hi team,\n\nPlease finalize the presentation slides by Thursday EOD. Bob will own the meeting agenda.\n\nBest regards,\nAlice",
      },
      {
        id: "msg_002",
        thread_id: "thread_demo",
        date: "2025-10-01T15:30:00Z",
        from: "bob@company.com",
        to: ["you@company.com"],
        cc: [],
        subject: "Re: Project Kickoff - Action Required",
        body: "Action items assigned:\n- Alice: Create timeline\n- You: Prepare metrics dashboard\n\nMeeting scheduled for Friday at 2pm in Conference Room A.",
      },
    ]);
    form.setValue("personalized_keywords", [
      { term: "metrics", weight: 1.5, scope: "subject|body" },
    ]);
  };

  const askQuestion = () => {
    if (question && result?.thread) {
      qaMutation.mutate({ question, thread: result.thread });
    }
  };

  const getPriorityColor = (label: string) => {
    switch (label) {
      case "P1": return "bg-red-500";
      case "P2": return "bg-yellow-500";
      case "P3": return "bg-green-500";
      default: return "bg-gray-500";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-6 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">AI Email Assistant</h1>
          <p className="text-muted-foreground">
            Process email threads with AI-powered summarization, task extraction, and priority scoring
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Mail className="w-5 h-5" />
                  Email Thread Input
                </CardTitle>
                <CardDescription>
                  Paste your email thread data as JSON or load sample data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                      control={form.control}
                      name="user_id"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>User ID</FormLabel>
                          <FormControl>
                            <Input {...field} data-testid="input-user-id" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="messages"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Email Messages (JSON)</FormLabel>
                          <FormControl>
                            <Textarea
                              {...field}
                              value={JSON.stringify(field.value, null, 2)}
                              onChange={(e) => {
                                try {
                                  field.onChange(JSON.parse(e.target.value));
                                } catch {
                                  // Invalid JSON, ignore
                                }
                              }}
                              placeholder="Paste email thread JSON here..."
                              className="font-mono text-sm min-h-[300px]"
                              data-testid="input-messages"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <div className="flex gap-2">
                      <Button
                        type="submit"
                        disabled={processMutation.isPending}
                        data-testid="button-process"
                        className="flex-1"
                      >
                        {processMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Process Thread
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={loadSampleData}
                        data-testid="button-sample"
                      >
                        Load Sample
                      </Button>
                    </div>
                  </form>
                </Form>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            {result && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>Priority Classification</span>
                      <Badge className={getPriorityColor(result.priority.label)} data-testid={`badge-priority-${result.priority.label}`}>
                        {result.priority.label}
                      </Badge>
                    </CardTitle>
                    <CardDescription>
                      Score: {result.priority.score.toFixed(2)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {result.priority.reasons.map((reason, i) => (
                        <div key={i} className="flex items-start gap-2 text-sm">
                          <AlertCircle className="w-4 h-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                          <span data-testid={`text-reason-${i}`}>{reason}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Summary</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm" data-testid="text-summary">{result.summary}</p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5" />
                      Extracted Tasks ({result.tasks.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {result.tasks.map((task, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-lg border bg-card hover-elevate"
                          data-testid={`card-task-${i}`}
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <p className="text-sm font-medium flex-1">{task.title}</p>
                            <Badge variant="outline" data-testid={`badge-type-${i}`}>
                              {task.type}
                            </Badge>
                          </div>
                          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                            {task.owner && (
                              <div className="flex items-center gap-1">
                                <User className="w-3 h-3" />
                                <span data-testid={`text-owner-${i}`}>{task.owner}</span>
                              </div>
                            )}
                            {task.due && (
                              <div className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                <span data-testid={`text-due-${i}`}>
                                  {format(new Date(task.due), "PPp")}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MessageSquare className="w-5 h-5" />
                      Ask Questions
                    </CardTitle>
                    <CardDescription>
                      Chat with the AI about this email thread
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex gap-2">
                        <Input
                          value={question}
                          onChange={(e) => setQuestion(e.target.value)}
                          placeholder="What do I need to deliver?"
                          onKeyDown={(e) => e.key === "Enter" && askQuestion()}
                          data-testid="input-question"
                        />
                        <Button
                          onClick={askQuestion}
                          disabled={qaMutation.isPending || !question}
                          data-testid="button-ask"
                        >
                          {qaMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                          Ask
                        </Button>
                      </div>

                      {qaMutation.data && (
                        <div className="p-4 rounded-lg bg-muted" data-testid="card-answer">
                          <p className="text-sm mb-2">{qaMutation.data.answer}</p>
                          <div className="flex gap-2 flex-wrap">
                            {qaMutation.data.sources.map((source, i) => (
                              <Badge key={i} variant="secondary" data-testid={`badge-source-${i}`}>
                                {source}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </>
            )}

            {!result && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center text-muted-foreground">
                    <Mail className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Process an email thread to see results</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
