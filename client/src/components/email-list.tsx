import { format, parseISO } from "date-fns";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { GmailEmail } from "@shared/schema";

interface EmailListItemProps {
  email: GmailEmail;
  active?: boolean;
  onClick?: () => void;
}

function EmailListItem({ email, active, onClick }: EmailListItemProps) {
  const fromName = email.from_.includes("<") 
    ? email.from_.split("<")[0].trim() 
    : email.from_;
  const fromInitial = fromName[0]?.toUpperCase() || "?";
  
  let formattedDate = "";
  try {
    const date = parseISO(email.date);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
      formattedDate = format(date, "HH:mm");
    } else if (diffInHours < 168) {
      formattedDate = format(date, "EEE");
    } else {
      formattedDate = format(date, "MMM d");
    }
  } catch (e) {
    formattedDate = email.date.slice(0, 10);
  }

  return (
    <div
      onClick={onClick}
      className={`
        flex gap-3 px-4 py-3 border-b border-border cursor-pointer hover-elevate transition-colors
        ${active ? "bg-accent" : ""}
      `}
      data-testid={`email-item-${email.id}`}
    >
      <Avatar className="w-10 h-10 flex-shrink-0">
        <AvatarFallback className="bg-primary/10 text-primary font-medium">
          {fromInitial}
        </AvatarFallback>
      </Avatar>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2 mb-1">
          <h3 className="font-medium text-sm truncate">{fromName}</h3>
          <span className="text-xs text-muted-foreground flex-shrink-0">
            {formattedDate}
          </span>
        </div>
        <p className="text-sm font-medium truncate mb-1">{email.subject}</p>
        <p className="text-xs text-muted-foreground line-clamp-2">
          {email.snippet}
        </p>
      </div>
    </div>
  );
}

interface EmailListProps {
  emails: GmailEmail[];
  selectedEmailId?: string;
  onEmailClick?: (email: GmailEmail) => void;
  isLoading?: boolean;
  error?: string | null;
}

export default function EmailList({ 
  emails, 
  selectedEmailId, 
  onEmailClick,
  isLoading,
  error 
}: EmailListProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm text-muted-foreground">Loading emails...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <p className="text-sm text-destructive mb-2">Failed to load emails</p>
        <p className="text-xs text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (emails.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <p className="text-sm text-muted-foreground">No emails found</p>
      </div>
    );
  }

  return (
    <div>
      {emails.map((email) => (
        <EmailListItem
          key={email.id}
          email={email}
          active={selectedEmailId === email.id}
          onClick={() => onEmailClick?.(email)}
        />
      ))}
    </div>
  );
}
