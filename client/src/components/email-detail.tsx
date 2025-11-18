import { ArrowLeft, Reply, ReplyAll, Forward, Archive, Trash, Star, MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { format, parseISO } from "date-fns";
import type { AnalyzedEmail } from "@shared/schema";
import { processEmailHtml, textToHtml } from "@/lib/html";
import { useEffect, useState } from "react";

interface EmailDetailProps {
  email: AnalyzedEmail;
  onBack: () => void;
}

export default function EmailDetail({ email, onBack }: EmailDetailProps) {
  // Use from_name/from_email if available, otherwise parse from email field
  const fromName = email.from_name || 
    (email.from_email ? email.from_email.split("@")[0] : 
     (email.from.includes("<") ? email.from.split("<")[0].trim() : email.from.split("@")[0] || email.from));
  const fromEmail = email.from_email || 
    (email.from.includes("<") ? email.from.match(/<(.+)>/)?.[1] : email.from) || "";
  const fromInitial = fromName[0]?.toUpperCase() || "?";
  
  let formattedDate = "";
  try {
    const date = parseISO(email.date);
    formattedDate = format(date, "MMM d, yyyy 'at' HH:mm");
  } catch (e) {
    formattedDate = email.date;
  }

  // Process HTML body for safe rendering
  const [processedHtml, setProcessedHtml] = useState<string>("");
  
  useEffect(() => {
    if (email.body_html) {
      const processed = processEmailHtml(
        email.body_html,
        email.inline_images || {}
      );
      setProcessedHtml(processed);
    } else if (email.body_text) {
      const html = textToHtml(email.body_text);
      setProcessedHtml(html);
    } else {
      // Fallback to snippet
      setProcessedHtml(textToHtml(email.snippet || ""));
    }
  }, [email.body_html, email.body_text, email.snippet, email.inline_images]);

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
                <p className="font-medium text-sm text-foreground">{fromName || fromEmail || "Unknown"}</p>
                {fromEmail && (
                  <p className="text-xs text-muted-foreground truncate">{fromEmail}</p>
                )}
              </div>
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {formattedDate}
              </span>
            </div>
          </div>
        </div>

        {/* Email Body */}
        <div className="prose prose-sm max-w-none text-foreground">
          {processedHtml ? (
            <div 
              className="email-body"
              dangerouslySetInnerHTML={{ __html: processedHtml }}
            />
          ) : (
            <div className="text-muted-foreground">
              No content available
            </div>
          )}
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
