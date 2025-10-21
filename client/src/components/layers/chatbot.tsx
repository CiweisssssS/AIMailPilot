import { ArrowLeft, Mail, Send, User, Bot } from "lucide-react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import type { AnalyzedEmail } from "@shared/schema";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatbotProps {
  onBack: () => void;
  analyzedEmails?: AnalyzedEmail[];
}

export default function Chatbot({ onBack, analyzedEmails = [] }: ChatbotProps) {
  const [message, setMessage] = useState("");
  const [chatHistory, setChatHistory] = useState<Message[]>([]);

  // Prepare thread data from analyzed emails for API
  const prepareThreadData = () => {
    if (analyzedEmails.length === 0) {
      return {
        thread_id: "empty-thread",
        participants: [],
        timeline: [],
        normalized_messages: []
      };
    }

    const participants = new Set<string>();
    const timeline: any[] = [];
    const normalized_messages: any[] = [];

    analyzedEmails.forEach(email => {
      participants.add(email.from);
      email.tasks?.forEach(task => {
        if (task.owner) participants.add(task.owner);
      });

      timeline.push({
        id: email.id,
        date: email.date,
        subject: email.subject
      });

      normalized_messages.push({
        id: email.id,
        clean_body: email.snippet || email.summary
      });
    });

    return {
      thread_id: analyzedEmails[0]?.threadId || "chatbot-thread",
      participants: Array.from(participants),
      timeline,
      normalized_messages
    };
  };

  const chatMutation = useMutation({
    mutationFn: async (question: string) => {
      const threadData = prepareThreadData();
      const response = await apiRequest(
        "POST",
        "/api/chatbot-qa",
        {
          question,
          thread: threadData
        }
      );
      
      // Check if response is ok
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`API Error: ${text}`);
      }
      
      // Parse JSON response
      const data = await response.json();
      return data as { answer: string; sources: string[] };
    },
    onSuccess: (data) => {
      setChatHistory(prev => [...prev, {
        role: "assistant",
        content: data.answer
      }]);
    },
    onError: (error: any) => {
      console.error("Chatbot error:", error);
      setChatHistory(prev => [...prev, {
        role: "assistant",
        content: `Sorry, an error occurred: ${error.message || "Unable to process your request"}`
      }]);
    }
  });

  const handleSend = () => {
    if (!message.trim() || chatMutation.isPending) return;
    
    const userMessage = message.trim();
    
    // Add user message to history
    setChatHistory(prev => [...prev, {
      role: "user",
      content: userMessage
    }]);
    
    // Clear input
    setMessage("");
    
    // Call API
    chatMutation.mutate(userMessage);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-br from-primary/20 to-primary/10 p-4 flex items-center gap-3 mb-6 rounded-2xl">
        <button 
          onClick={onBack}
          className="p-2 hover:bg-primary/10 rounded-lg transition-colors"
          data-testid="button-back"
        >
          <ArrowLeft className="w-5 h-5 text-primary" />
        </button>
        <div className="flex items-center gap-2 text-primary">
          <Mail className="w-5 h-5" />
          <span className="font-semibold">AIMailPilot Chatbot</span>
        </div>
      </div>

      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 space-y-4">
        {chatHistory.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <h2 className="text-2xl font-bold text-foreground mb-4">Hello!</h2>
            <p className="text-base text-foreground/80 mb-6">
              How can I help you today?
            </p>
            
            <div className="space-y-2 text-sm text-muted-foreground max-w-md">
              <p>💡 Summarize emails in a category</p>
              <p>🔍 Search for emails by keyword</p>
              <p>📋 List top 3 urgent tasks</p>
            </div>
          </div>
        ) : (
          <>
            {chatHistory.map((msg, index) => (
              <div
                key={index}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] px-4 py-3 rounded-2xl ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-foreground"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                </div>
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <User className="w-5 h-5 text-primary" />
                  </div>
                )}
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="flex gap-3 justify-start">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-5 h-5 text-primary" />
                </div>
                <div className="bg-muted px-4 py-3 rounded-2xl">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 p-3 rounded-2xl border-2 border-primary/30 bg-background">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your question here..."
            className="flex-1 bg-transparent border-0 focus:outline-none text-sm"
            data-testid="input-chatbot"
            disabled={chatMutation.isPending}
          />
          <button 
            onClick={handleSend}
            disabled={!message.trim() || chatMutation.isPending}
            className="p-2 rounded-full bg-primary hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="button-send"
          >
            <Send className="w-4 h-4 text-primary-foreground" />
          </button>
        </div>
      </div>
    </div>
  );
}
