import { Mail, Calendar, Bookmark, RefreshCw } from "lucide-react";
import type { AnalyzedEmail } from "@shared/schema";

interface TaskScheduleProps {
  analyzedEmails: AnalyzedEmail[];
  onFlaggedClick: () => void;
  onRefreshClick: () => void;
  onInboxReminderClick?: () => void;
}

export default function TaskSchedule({ analyzedEmails, onFlaggedClick, onRefreshClick, onInboxReminderClick }: TaskScheduleProps) {
  // Group all emails by priority (not just those with tasks)
  // This ensures high-priority emails are visible even without extracted tasks
  const urgentEmails = analyzedEmails.filter(e => e.priority.label.includes("P1"));
  const todoEmails = analyzedEmails.filter(e => e.priority.label.includes("P2"));
  const fyiEmails = analyzedEmails.filter(e => e.priority.label.includes("P3"));

  return (
    <div className="relative h-full">
      {/* Header */}
      <div className="bg-gradient-to-br from-primary/20 to-primary/10 rounded-3xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-4 text-primary">
          <Mail className="w-5 h-5" />
          <span className="font-semibold">AIMailPilot</span>
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Good morning, user!
        </h2>
        <p className="text-foreground/80">
          You have {analyzedEmails.length} analyzed email{analyzedEmails.length !== 1 ? 's' : ''}.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-6 mb-6 border-b border-border">
        <button 
          onClick={onInboxReminderClick}
          className="pb-2 px-1 text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          data-testid="tab-inbox-reminder"
        >
          <Mail className="w-4 h-4" />
          Inbox Reminder
        </button>
        <button 
          className="pb-2 px-1 text-sm font-medium border-b-2 border-primary -mb-px flex items-center gap-2"
          data-testid="tab-task-schedule"
        >
          <Calendar className="w-4 h-4" />
          Task & Schedule
        </button>
      </div>

      {/* Timeline */}
      <div className="space-y-6">
        {/* Urgent Emails */}
        {urgentEmails.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-3 h-3 rounded-full bg-primary" />
              <h3 className="text-lg font-semibold text-primary">Urgent</h3>
            </div>
            <div className="ml-6 border-l-2 border-border pl-6 space-y-4">
              {urgentEmails.map((email) => (
                <TimelineItem
                  key={email.id}
                  email={email}
                />
              ))}
            </div>
          </div>
        )}

        {/* To-Do Emails */}
        {todoEmails.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-3 h-3 rounded-full bg-primary/60" />
              <h3 className="text-lg font-semibold text-primary/80">To-Do</h3>
            </div>
            <div className="ml-6 border-l-2 border-border pl-6 space-y-4">
              {todoEmails.map((email) => (
                <TimelineItem
                  key={email.id}
                  email={email}
                />
              ))}
            </div>
          </div>
        )}

        {/* FYI Emails */}
        {fyiEmails.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-3 h-3 rounded-full bg-primary/40" />
              <h3 className="text-lg font-semibold text-primary/60">FYI</h3>
            </div>
            <div className="ml-6 border-l-2 border-border pl-6 space-y-4">
              {fyiEmails.map((email) => (
                <TimelineItem
                  key={email.id}
                  email={email}
                />
              ))}
            </div>
          </div>
        )}

        {/* No emails message */}
        {analyzedEmails.length === 0 && (
          <div className="text-center text-muted-foreground p-8">
            No analyzed emails yet
          </div>
        )}
      </div>

      {/* Floating Action Buttons */}
      <div className="fixed bottom-8 right-8 flex flex-col gap-3">
        <button
          onClick={onFlaggedClick}
          className="w-14 h-14 rounded-full bg-primary hover:bg-primary/90 shadow-lg flex items-center justify-center transition-all hover:scale-105"
          data-testid="button-flagged"
        >
          <Bookmark className="w-6 h-6 text-primary-foreground" />
        </button>
        <button
          onClick={onRefreshClick}
          className="w-14 h-14 rounded-full bg-primary hover:bg-primary/90 shadow-lg flex items-center justify-center transition-all hover:scale-105"
          data-testid="button-refresh"
        >
          <RefreshCw className="w-6 h-6 text-primary-foreground" />
        </button>
      </div>
    </div>
  );
}

interface TimelineItemProps {
  email: AnalyzedEmail;
}

function TimelineItem({ email }: TimelineItemProps) {
  // Handle null/empty task_extracted by falling back to subject
  const hasTask = email.task_extracted && email.task_extracted.trim() !== "" && email.task_extracted !== "None";
  const displayTitle = hasTask ? email.task_extracted : email.subject;
  
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-card transition-colors">
      <div className="flex-1">
        <p className="text-sm font-medium text-foreground mb-1">
          {hasTask ? "Task: " : "Subject: "}{displayTitle}
        </p>
        <p className="text-xs text-muted-foreground mb-1">
          {email.summary}
        </p>
        <p className="text-xs text-muted-foreground">
          From: {email.from}
        </p>
      </div>
      <button className="p-2 hover:bg-primary/10 rounded-lg" data-testid={`button-add-calendar-${email.id}`}>
        <Calendar className="w-5 h-5 text-primary" />
      </button>
    </div>
  );
}
