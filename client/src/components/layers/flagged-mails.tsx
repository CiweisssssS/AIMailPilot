import { ArrowLeft, Mail, ExternalLink, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AnalyzedEmail } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";
import { useQuery } from "@tanstack/react-query";

interface FlaggedMailsProps {
  analyzedEmails: AnalyzedEmail[];
  onBack: () => void;
  onChatbotClick: () => void;
}

// Format deadline - backend returns "Mon DD, YYYY, HH:mm" or "TBD"
function formatDeadline(dateStr: string | null | undefined): string {
  if (!dateStr || dateStr === "TBD" || dateStr === "null") {
    return "Deadline: TBD";
  }
  
  // Backend already returns formatted string "Mon DD, YYYY, HH:mm" - use it directly
  return dateStr;
}

// Remove brackets from task title
function cleanTaskTitle(title: string): string {
  return title.replace(/^\[|\]$/g, '').trim();
}

// Extract priority number from label (e.g., "P1 - Urgent" → 1)
function extractPriorityLevel(priorityLabel: string): number {
  const match = priorityLabel.match(/P(\d)/);
  return match ? parseInt(match[1]) : 999; // Unknown priority goes last
}

// Parse deadline into Date object (null for TBD)
function parseDeadline(dateStr: string | null | undefined): Date | null {
  if (!dateStr || dateStr === "TBD" || dateStr === "null") {
    return null;
  }
  
  // Backend returns "Mon DD, YYYY, HH:mm" format (e.g., "Nov 04, 2025, 20:31")
  // We need to parse this manually for cross-browser compatibility
  try {
    const monthMap: Record<string, number> = {
      Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
      Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11
    };
    
    // Split "Nov 04, 2025, 20:31" into parts
    const parts = dateStr.split(/[,\s:]+/).filter(p => p);
    if (parts.length < 5) return null;
    
    const monthStr = parts[0]; // "Nov"
    const day = parseInt(parts[1]); // 4
    const year = parseInt(parts[2]); // 2025
    const hour = parseInt(parts[3]); // 20
    const minute = parseInt(parts[4]); // 31
    
    const month = monthMap[monthStr];
    if (month === undefined || isNaN(day) || isNaN(year) || isNaN(hour) || isNaN(minute)) {
      return null;
    }
    
    const date = new Date(year, month, day, hour, minute);
    return isNaN(date.getTime()) ? null : date;
  } catch {
    return null;
  }
}

// Sort emails by priority (P1→P2→P3) then by deadline (earliest→latest, TBD last)
function sortFlaggedEmails(emails: AnalyzedEmail[]): AnalyzedEmail[] {
  return [...emails].sort((a, b) => {
    // 1. Sort by priority first
    const priorityA = extractPriorityLevel(a.priority.label);
    const priorityB = extractPriorityLevel(b.priority.label);
    
    if (priorityA !== priorityB) {
      return priorityA - priorityB; // Lower number (P1) comes first
    }
    
    // 2. Within same priority, sort by deadline
    const deadlineA = a.tasks?.[0]?.due;
    const deadlineB = b.tasks?.[0]?.due;
    
    const dateA = parseDeadline(deadlineA);
    const dateB = parseDeadline(deadlineB);
    
    // TBD goes last within the same priority group
    if (dateA === null && dateB === null) return 0;
    if (dateA === null) return 1;  // A is TBD, goes after B
    if (dateB === null) return -1; // B is TBD, A goes first
    
    // Both have real dates - earliest comes first
    return dateA.getTime() - dateB.getTime();
  });
}

export default function FlaggedMails({ analyzedEmails, onBack, onChatbotClick }: FlaggedMailsProps) {
  // Fetch flagged emails from database
  const { data: flaggedData, isLoading } = useQuery<{ flagged_emails: Array<{ email_id: string }> }>({
    queryKey: ["/api/flags"],
  });

  // Filter analyzed emails to only show flagged ones
  const flaggedEmailIds = new Set(flaggedData?.flagged_emails?.map(f => f.email_id) || []);
  const filteredEmails = analyzedEmails.filter(email => flaggedEmailIds.has(email.id));
  
  // Sort by priority (P1→P2→P3) then by deadline (earliest→latest, TBD last)
  const flaggedEmails = sortFlaggedEmails(filteredEmails);

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
        {isLoading ? (
          <div className="text-center text-muted-foreground p-8 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading flagged emails...
          </div>
        ) : flaggedEmails.length === 0 ? (
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
