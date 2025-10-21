import { Mail, Bookmark, RefreshCw, Plus } from "lucide-react";
import type { AnalyzedEmail } from "@shared/schema";

interface InboxReminderProps {
  unreadCount: number;
  urgentCount: number;
  todoCount: number;
  fyiCount: number;
  analyzedEmails: AnalyzedEmail[];
  isAnalyzing?: boolean;
  onCategoryClick: (category: "urgent" | "todo" | "fyi") => void;
  onAddTagsClick: () => void;
  onFlaggedClick: () => void;
  onRefreshClick: () => void;
  onTaskScheduleClick?: () => void;
}

export default function InboxReminder({
  unreadCount,
  urgentCount,
  todoCount,
  fyiCount,
  analyzedEmails,
  isAnalyzing = false,
  onCategoryClick,
  onAddTagsClick,
  onFlaggedClick,
  onRefreshClick,
  onTaskScheduleClick
}: InboxReminderProps) {
  // Get latest email for each category
  const urgentEmails = analyzedEmails.filter(e => e.priority.label === "P1 - Urgent");
  const todoEmails = analyzedEmails.filter(e => e.priority.label === "P2 - To-do");
  const fyiEmails = analyzedEmails.filter(e => e.priority.label === "P3 - FYI");

  const latestUrgent = urgentEmails[0];
  const latestTodo = todoEmails[0];
  const latestFyi = fyiEmails[0];
  return (
    <div className="relative h-full">
      {/* Header */}
      <div className="bg-gradient-to-br from-card to-secondary rounded-3xl p-6 mb-6">
        <div className="flex items-center gap-2 mb-4 text-primary">
          <Mail className="w-5 h-5" />
          <span className="font-semibold">AIMailPilot</span>
        </div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Good morning, user!
        </h2>
        <p className="text-foreground/80">
          You have {unreadCount} unread emails.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-6 mb-6 border-b border-border">
        <button 
          className="pb-2 px-1 text-sm font-medium border-b-2 border-primary -mb-px flex items-center gap-2"
          data-testid="tab-inbox-reminder"
        >
          <Mail className="w-4 h-4" />
          Inbox Reminder
        </button>
        <button 
          onClick={onTaskScheduleClick}
          className="pb-2 px-1 text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-2"
          data-testid="tab-task-schedule"
        >
          <Mail className="w-4 h-4" />
          Task & Schedule
        </button>
      </div>

      {/* Category Cards */}
      <div className="space-y-4 mb-4">
        {/* Urgent Card */}
        <button
          onClick={() => onCategoryClick("urgent")}
          className="w-full bg-secondary hover:bg-secondary/80 rounded-2xl p-5 text-left transition-all hover:shadow-md"
          data-testid="card-urgent"
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-primary">Urgent</h3>
            <span className="text-5xl font-bold text-primary/60 opacity-70">{urgentCount}</span>
          </div>
          {latestUrgent ? (
            <>
              <p className="text-sm text-foreground font-medium mb-1 truncate">
                Latest: {latestUrgent.subject}
              </p>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {latestUrgent.summary}
              </p>
            </>
          ) : isAnalyzing ? (
            <p className="text-sm text-muted-foreground">Analyzing...</p>
          ) : (
            <p className="text-sm text-muted-foreground">No urgent emails</p>
          )}
        </button>

        {/* To-Do Card */}
        <button
          onClick={() => onCategoryClick("todo")}
          className="w-full bg-accent hover:bg-accent/80 rounded-2xl p-5 text-left transition-all hover:shadow-md"
          data-testid="card-todo"
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-primary">To-Do</h3>
            <span className="text-5xl font-bold text-primary/60 opacity-60">{todoCount}</span>
          </div>
          {latestTodo ? (
            <>
              <p className="text-sm text-foreground font-medium mb-1 truncate">
                Latest: {latestTodo.subject}
              </p>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {latestTodo.summary}
              </p>
            </>
          ) : isAnalyzing ? (
            <p className="text-sm text-muted-foreground">Analyzing...</p>
          ) : (
            <p className="text-sm text-muted-foreground">No to-do emails</p>
          )}
        </button>

        {/* FYI Card */}
        <button
          onClick={() => onCategoryClick("fyi")}
          className="w-full bg-secondary hover:bg-secondary/80 rounded-2xl p-5 text-left transition-all hover:shadow-md"
          data-testid="card-fyi"
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-primary">FYI</h3>
            <span className="text-5xl font-bold text-primary/60 opacity-50">{fyiCount}</span>
          </div>
          {latestFyi ? (
            <>
              <p className="text-sm text-foreground font-medium mb-1 truncate">
                Latest: {latestFyi.subject}
              </p>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {latestFyi.summary}
              </p>
            </>
          ) : isAnalyzing ? (
            <p className="text-sm text-muted-foreground">Analyzing...</p>
          ) : (
            <p className="text-sm text-muted-foreground">No FYI emails</p>
          )}
        </button>

        {/* Add More Tags Button */}
        <button
          onClick={onAddTagsClick}
          className="w-full bg-card hover:bg-accent rounded-2xl p-5 text-center transition-all hover:shadow-md border-2 border-dashed border-border"
          data-testid="button-add-tags"
        >
          <div className="flex items-center justify-center gap-2 text-muted-foreground">
            <Plus className="w-4 h-4" />
            <span className="text-sm font-medium">Click here to add more tags</span>
          </div>
        </button>
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
