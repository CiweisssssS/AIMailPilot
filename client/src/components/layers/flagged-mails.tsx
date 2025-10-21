import { ArrowLeft, Mail, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AnalyzedEmail } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";

interface FlaggedMailsProps {
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
    
    return `${month}/${day}/${year}, ${hours}:${minutes}`;
  } catch (e) {
    return "Deadline: TBD";
  }
}

// Remove brackets from task title
function cleanTaskTitle(title: string): string {
  return title.replace(/^\[|\]$/g, '').trim();
}

export default function FlaggedMails({ analyzedEmails, onBack, onChatbotClick }: FlaggedMailsProps) {
  // For now, treat P1 Urgent emails as "flagged" since we don't have explicit flagging yet
  const flaggedEmails = analyzedEmails.filter(email => email.priority.label.includes("P1"));

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
      <div className="bg-accent rounded-2xl p-6 mb-6">
        <h2 className="text-2xl font-bold text-primary mb-2">Flagged Mails</h2>
        <p className="text-foreground/80">
          You have {flaggedEmails.length} flagged mail{flaggedEmails.length !== 1 ? 's' : ''} now.
        </p>
      </div>

      {/* Flagged Items */}
      <div className="flex-1 space-y-4 overflow-y-auto">
        {flaggedEmails.length === 0 ? (
          <div className="text-center text-muted-foreground p-8">
            No flagged emails at the moment
          </div>
        ) : (
          flaggedEmails.map((email) => (
            <FlaggedItem
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

interface FlaggedItemProps {
  email: AnalyzedEmail;
}

function FlaggedItem({ email }: FlaggedItemProps) {
  const { toast } = useToast();
  
  const hasTask = email.task_extracted && email.task_extracted.trim() !== "" && email.task_extracted !== "None";
  const taskDisplay = hasTask ? cleanTaskTitle(email.task_extracted!) : email.subject;
  
  // Get deadline from first task if available
  const deadline = email.tasks && email.tasks.length > 0 ? email.tasks[0].due : null;
  const formattedDeadline = formatDeadline(deadline);
  
  const handleOpenMail = () => {
    toast({
      title: "Open in Gmail",
      description: "Opening email in Gmail...",
    });
    // In future: window.open(`https://mail.google.com/mail/u/0/#inbox/${email.id}`, '_blank');
  };
  
  return (
    <div className="p-4 border-l-4 border-primary/30 bg-card rounded-r-lg space-y-3">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h3 className="font-semibold text-foreground mb-2">
            {taskDisplay}
          </h3>
          <p className="text-sm text-muted-foreground mb-2">
            {email.summary}
          </p>
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <div className="text-xs text-muted-foreground">
              Category: <Badge variant="secondary" className="ml-1">{email.priority.label}</Badge>
            </div>
            <div className="text-xs text-muted-foreground">
              {formattedDeadline}
            </div>
          </div>
        </div>
        <button 
          onClick={handleOpenMail}
          className="p-1 hover:bg-primary/10 rounded transition-colors" 
          data-testid={`button-open-mail-${email.id}`}
        >
          <ExternalLink className="w-5 h-5 text-muted-foreground" />
        </button>
      </div>
    </div>
  );
}
