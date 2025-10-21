import { ArrowLeft, Mail, Calendar, Bookmark, CheckSquare } from "lucide-react";
import type { AnalyzedEmail } from "@shared/schema";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { limitWords } from "@/lib/text-utils";

interface CategoryDetailProps {
  category: "urgent" | "todo" | "fyi";
  analyzedEmails: AnalyzedEmail[];
  onBack: () => void;
  onChatbotClick: () => void;
}

// Format date to MM/DD/YYYY HH:mm (24-hour)
function formatDeadline(dateStr: string | null | undefined): string {
  if (!dateStr || dateStr === "TBD" || dateStr === "null") {
    return "Deadline: TBD";
  }
  
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return "Deadline: TBD";
    }
    
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    
    return `Time: ${month}/${day}/${year}, ${hours}:${minutes}`;
  } catch (e) {
    return "Deadline: TBD";
  }
}

// Remove brackets from task title
function cleanTaskTitle(title: string): string {
  return title.replace(/^\[|\]$/g, '').trim();
}

export default function CategoryDetail({ category, analyzedEmails, onBack, onChatbotClick }: CategoryDetailProps) {
  // Filter emails by category
  const filteredEmails = analyzedEmails.filter(email => {
    if (category === "urgent") return email.priority.label.includes("P1");
    if (category === "todo") return email.priority.label.includes("P2");
    if (category === "fyi") return email.priority.label.includes("P3");
    return false;
  });

  const categoryConfig = {
    urgent: {
      title: "Urgent Mails",
      subtitle: `You have ${filteredEmails.length} urgent mail${filteredEmails.length !== 1 ? 's' : ''} now.`,
      bgClass: "bg-accent"
    },
    todo: {
      title: "To-Do Mails",
      subtitle: `You have ${filteredEmails.length} to-do mail${filteredEmails.length !== 1 ? 's' : ''} now.`,
      bgClass: "bg-accent"
    },
    fyi: {
      title: "FYI Mails",
      subtitle: `You have ${filteredEmails.length} FYI mail${filteredEmails.length !== 1 ? 's' : ''} now.`,
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
        {filteredEmails.length === 0 ? (
          <div className="text-center text-muted-foreground p-8">
            No {category} emails at the moment
          </div>
        ) : (
          filteredEmails.map((email) => (
            <EmailItem
              key={email.id}
              email={email}
            />
          ))
        )}
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
  email: AnalyzedEmail;
}

function EmailItem({ email }: EmailItemProps) {
  const { toast } = useToast();
  const [isFlagged, setIsFlagged] = useState(false);
  
  const hasTask = email.task_extracted && email.task_extracted.trim() !== "" && email.task_extracted !== "None";
  const taskDisplay = hasTask ? cleanTaskTitle(email.task_extracted!) : email.subject;
  
  // Get deadline from first task if available
  const deadline = email.tasks && email.tasks.length > 0 ? email.tasks[0].due : null;
  const formattedDeadline = formatDeadline(deadline);
  
  const handleFlag = () => {
    setIsFlagged(!isFlagged);
    toast({
      title: isFlagged ? "Unflagged" : "Flagged",
      description: isFlagged ? "Email removed from flagged" : "Email added to flagged",
    });
  };
  
  const handleAddToCalendar = () => {
    toast({
      title: "Add to Calendar",
      description: "Calendar integration coming soon!",
    });
  };
  
  return (
    <div className="p-4 border-l-4 border-primary/30 bg-card rounded-r-lg">
      <div className="flex items-start gap-3 mb-3">
        <button 
          className="mt-1 p-1 hover:bg-primary/10 rounded transition-colors" 
          data-testid={`checkbox-done-${email.id}`}
          onClick={() => toast({ title: "Task completed", description: "Mark as done feature coming soon!" })}
        >
          <CheckSquare className="w-5 h-5 text-muted-foreground" />
        </button>
        <div className="flex-1">
          <h3 className="font-semibold text-foreground mb-2">
            {hasTask ? "" : "Subject: "}{taskDisplay}
          </h3>
          <p className="text-sm text-muted-foreground mb-2">
            Summary: {limitWords(email.summary, 20)}
          </p>
          <p className="text-xs text-muted-foreground mb-1">
            {formattedDeadline}
          </p>
        </div>
        <button 
          className="p-1 hover:bg-primary/10 rounded transition-colors" 
          data-testid={`button-flag-${email.id}`}
          onClick={handleFlag}
        >
          <Bookmark className={`w-5 h-5 ${isFlagged ? 'fill-primary text-primary' : 'text-primary'}`} />
        </button>
      </div>
      <button 
        onClick={handleAddToCalendar}
        className="text-sm bg-primary/10 hover:bg-primary/20 text-primary px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors" 
        data-testid={`button-add-to-calendar-${email.id}`}
      >
        <Calendar className="w-4 h-4" />
        Add to Calendar
      </button>
    </div>
  );
}
