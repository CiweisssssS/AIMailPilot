import { ArrowLeft, Mail, Send } from "lucide-react";
import { useState } from "react";

interface ChatbotProps {
  onBack: () => void;
}

export default function Chatbot({ onBack }: ChatbotProps) {
  const [message, setMessage] = useState("");

  const handleSend = () => {
    if (!message.trim()) return;
    // TODO: Implement chatbot API call
    console.log("Sending message:", message);
    setMessage("");
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
          <span className="font-semibold">AIMailPilot</span>
        </div>
      </div>

      {/* Welcome Message */}
      <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
        <h2 className="text-3xl font-bold text-foreground mb-4">Hello, user!</h2>
        <p className="text-base text-foreground/80 mb-8">
          Feel free to ask me any questions.
        </p>
        
        <div className="space-y-2 text-sm text-muted-foreground max-w-md">
          <p>- Summarize all items in a category</p>
          <p>- Search for emails or tasks by keyword</p>
          <p>- Ask me things like 'Top 3 urgent tasks'</p>
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 p-3 rounded-2xl border-2 border-primary/30 bg-background">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your question here."
            className="flex-1 bg-transparent border-0 focus:outline-none text-sm"
            data-testid="input-chatbot"
          />
          <button 
            onClick={handleSend}
            disabled={!message.trim()}
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
