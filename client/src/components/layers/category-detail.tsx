import { ArrowLeft, Mail, Calendar, Bookmark, CheckSquare } from "lucide-react";
import type { AnalyzedEmail } from "@shared/schema";

interface CategoryDetailProps {
  category: "urgent" | "todo" | "fyi";
  analyzedEmails: AnalyzedEmail[];
  onBack: () => void;
  onChatbotClick: () => void;
}

export default function CategoryDetail({ category, analyzedEmails, onBack, onChatbotClick }: CategoryDetailProps) {
  const categoryConfig = {
    urgent: {
      title: "Urgent Mails",
      subtitle: "You have 2 urgent mails now.",
      bgClass: "bg-accent"
    },
    todo: {
      title: "To-Do Mails",
      subtitle: "You have 2 to-do mails now.",
      bgClass: "bg-accent"
    },
    fyi: {
      title: "FYI Mails",
      subtitle: "You have 2 FYI mails now.",
      bgClass: "bg-accent"
    }
  };

  const config = categoryConfig[category];

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

      {/* Category Title */}
      <div className={`${config.bgClass} rounded-2xl p-6 mb-6`}>
        <h2 className="text-2xl font-bold text-primary mb-2">{config.title}</h2>
        <p className="text-foreground/80">{config.subtitle}</p>
      </div>

      {/* Email Items */}
      <div className="flex-1 space-y-4 overflow-y-auto">
        <EmailItem
          task="Contract Signature Required"
          summary="Please review and sign the updated contract before the end of the day."
          time="Oct 5, 9:00 PM"
        />
        <EmailItem
          task="Marketing Report Draft - Feedback Needed"
          summary="The draft for Q3 marketing performance is attached. Please share your comments ASAP."
          time=""
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

interface EmailItemProps {
  task: string;
  summary: string;
  time: string;
}

function EmailItem({ task, summary, time }: EmailItemProps) {
  return (
    <div className="p-4 border-l-4 border-primary/30 bg-card rounded-r-lg">
      <div className="flex items-start gap-3 mb-3">
        <button className="mt-1 p-1 hover:bg-primary/10 rounded" data-testid="checkbox-done">
          <CheckSquare className="w-5 h-5 text-muted-foreground" />
        </button>
        <div className="flex-1">
          <h3 className="font-semibold text-foreground mb-2">Task: {task}</h3>
          <p className="text-sm text-muted-foreground mb-3">Summary: {summary}</p>
          {time && <p className="text-sm text-muted-foreground">Time: {time}</p>}
        </div>
        <button className="p-1 hover:bg-primary/10 rounded" data-testid="button-flag">
          <Bookmark className="w-5 h-5 text-primary" />
        </button>
      </div>
      {time && (
        <button className="text-sm text-primary hover:underline flex items-center gap-2" data-testid="button-add-to-calendar">
          <Calendar className="w-4 h-4" />
          Add to Calendar
        </button>
      )}
    </div>
  );
}
