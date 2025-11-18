import { ArrowLeft, Reply, ReplyAll, Forward, Archive, Trash, Star, MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { format, parseISO } from "date-fns";
import type { AnalyzedEmail } from "@shared/schema";

interface EmailDetailProps {
  email: AnalyzedEmail;
  onBack: () => void;
}

export default function EmailDetail({ email, onBack }: EmailDetailProps) {
  const fromName = email.from.includes("<") 
    ? email.from.split("<")[0].trim() 
    : email.from;
  const fromEmail = email.from.includes("<")
    ? email.from.match(/<(.+)>/)?.[1] || email.from
    : email.from;
  const fromInitial = fromName[0]?.toUpperCase() || "?";
  
  let formattedDate = "";
  try {
    const date = parseISO(email.date);
    formattedDate = format(date, "MMM d, yyyy 'at' HH:mm");
  } catch (e) {
    formattedDate = email.date;
  }

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header with Back Button and Actions */}
      <div className="border-b border-border px-4 py-3 flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          data-testid="button-back-to-list"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        
        <div className="flex-1" />
        
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" data-testid="button-archive">
            <Archive className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" data-testid="button-delete">
            <Trash className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" data-testid="button-star">
            <Star className="w-5 h-5" />
          </Button>
          <Button variant="ghost" size="icon" data-testid="button-more">
            <MoreVertical className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Email Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* Subject */}
        <h1 className="text-2xl font-semibold mb-4 text-foreground">
          {email.subject}
        </h1>

        {/* Sender Info */}
        <div className="flex items-start gap-3 mb-6">
          <Avatar className="w-10 h-10 flex-shrink-0">
            <AvatarFallback className="bg-primary/10 text-primary font-medium">
              {fromInitial}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm text-foreground">{fromName}</p>
                <p className="text-xs text-muted-foreground truncate">{fromEmail}</p>
              </div>
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {formattedDate}
              </span>
            </div>
            
            <div className="text-xs text-muted-foreground mt-1">
              {email.summary && (
                <div className="text-xs text-muted-foreground mb-2">
                  Summary: {email.summary}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Email Body */}
        <div className="prose prose-sm max-w-none text-foreground">
          <div className="whitespace-pre-wrap break-words">
            {email.summary || email.snippet}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="border-t border-border px-6 py-4 flex gap-2">
        <Button variant="default" className="gap-2" data-testid="button-reply">
          <Reply className="w-4 h-4" />
          Reply
        </Button>
        <Button variant="outline" className="gap-2" data-testid="button-reply-all">
          <ReplyAll className="w-4 h-4" />
          Reply All
        </Button>
        <Button variant="outline" className="gap-2" data-testid="button-forward">
          <Forward className="w-4 h-4" />
          Forward
        </Button>
      </div>
    </div>
  );
}
