import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface EmailListItemProps {
  sender: string;
  subject: string;
  preview: string;
  time: string;
  unread?: boolean;
  avatar?: string;
}

export function EmailListItem({ sender, subject, preview, time, unread, avatar }: EmailListItemProps) {
  return (
    <button
      className={`
        w-full p-4 border-b border-border text-left transition-colors hover:bg-card
        ${unread ? "bg-card/50" : ""}
      `}
      data-testid="email-item"
    >
      <div className="flex items-start gap-3">
        <Avatar className="w-10 h-10 flex-shrink-0">
          <AvatarImage src={avatar} />
          <AvatarFallback className="bg-primary/10 text-primary text-sm">
            {sender.slice(0, 2).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline justify-between gap-2 mb-1">
            <span className={`text-sm truncate ${unread ? "font-semibold" : "font-medium"}`}>
              {sender}
            </span>
            <span className="text-xs text-muted-foreground flex-shrink-0">{time}</span>
          </div>
          <p className={`text-sm mb-1 truncate ${unread ? "font-semibold" : ""}`}>
            {subject}
          </p>
          <p className="text-sm text-muted-foreground line-clamp-2">
            {preview}
          </p>
        </div>
      </div>
    </button>
  );
}

export default function EmailList() {
  return (
    <>
      <EmailListItem
        sender="Google"
        subject="Google alert: Filo accessed your Google Account data."
        preview="Your Google Account was just accessed using a link from a Google Apps Script project..."
        time="11:50 PM"
        unread
      />
      <EmailListItem
        sender="Replit"
        subject="Your AIMailPilot project on Replit deployed successfully to https://ai-mail-..."
        preview="Congratulations! Your deployment is live..."
        time="10:42 PM"
        unread
      />
      <EmailListItem
        sender="Replit"
        subject="Your AIMailPilot deployment on Replit has failed."
        preview="We encountered an error while deploying your project..."
        time="10:11 PM"
        unread
      />
      <EmailListItem
        sender="Yuling Song"
        subject="Review new email banner designs in Figma by next week."
        preview="Hi team, please take a look at the new designs..."
        time="9:09 PM"
      />
      <EmailListItem
        sender="Yuling Song"
        subject="Rebecca needs your review of the pitch deck by EOD for tomorrow's meeting."
        preview="Rebecca has shared the pitch deck with you..."
        time="9:08 PM"
      />
      <EmailListItem
        sender="Yuling Song (via Goog..."
        subject="Yuling Song shared a Google Script 'V2' with you for editing."
        preview="You now have edit access to this script..."
        time="8:01 PM"
      />
      <EmailListItem
        sender="Ted Shelton via Link..."
        subject="LinkedIn newsletter: HR + IT in the Age of Agents by Ted Shelton."
        preview="In this edition, Ted discusses the future of work..."
        time="7:48 PM"
      />
      <EmailListItem
        sender="LinkedIn"
        subject="Your LinkedIn profile has new activity: 1 invitation, 3 messages, and 25 sea..."
        preview="You have pending connection requests and unread messages..."
        time="7:45 PM"
      />
    </>
  );
}
