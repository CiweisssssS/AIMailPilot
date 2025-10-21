import { ArrowLeft, Mail, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface FlaggedMailsProps {
  onBack: () => void;
  onChatbotClick: () => void;
}

export default function FlaggedMails({ onBack, onChatbotClick }: FlaggedMailsProps) {
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

      {/* Title */}
      <div className="bg-[#D4C4E0] rounded-2xl p-6 mb-6">
        <h2 className="text-2xl font-bold text-[#5B2C6F] mb-2">Flagged Mails</h2>
        <p className="text-[#5B2C6F]/80">You have 2 flagged mails now.</p>
      </div>

      {/* Flagged Items */}
      <div className="flex-1 space-y-4 overflow-y-auto">
        <FlaggedItem
          task="Project Alpha - Final Report Due"
          summary="Please review the attached report before Friday's meeting..."
          category="To-do"
          flaggedDate="Oct 3, 2025"
        />
        <FlaggedItem
          task="Client Feedback Summary"
          summary="Attached are the key points from yesterday's client call..."
          category="FYI"
          flaggedDate="Sep 29, 2025"
        />
      </div>

      {/* Chatbot Button */}
      <button
        onClick={onChatbotClick}
        className="mt-6 w-full bg-card hover:bg-accent rounded-2xl p-4 text-center transition-all border border-border"
        data-testid="button-chatbot"
      >
        <span className="text-sm text-muted-foreground">Talk with our chatbot?</span>
      </button>
    </div>
  );
}

interface FlaggedItemProps {
  task: string;
  summary: string;
  category: string;
  flaggedDate: string;
}

function FlaggedItem({ task, summary, category, flaggedDate }: FlaggedItemProps) {
  return (
    <div className="p-4 border-l-4 border-primary/30 bg-card rounded-r-lg space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-semibold text-foreground mb-2">Task: {task}</h3>
          <p className="text-sm text-muted-foreground mb-3">Summary: {summary}</p>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="text-xs text-muted-foreground">
              Category: <Badge variant="secondary" className="ml-1">{category}</Badge>
            </div>
            <div className="text-xs text-muted-foreground">
              Flagged on: {flaggedDate}
            </div>
          </div>
        </div>
        <button className="p-1 hover:bg-primary/10 rounded" data-testid="button-open-mail">
          <ExternalLink className="w-5 h-5 text-muted-foreground" />
        </button>
      </div>
    </div>
  );
}
