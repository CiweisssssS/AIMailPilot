import { Mail, Bookmark, RefreshCw, Plus } from "lucide-react";

interface InboxReminderProps {
  unreadCount: number;
  onCategoryClick: (category: "urgent" | "todo" | "fyi") => void;
  onAddTagsClick: () => void;
  onFlaggedClick: () => void;
  onRefreshClick: () => void;
  onTaskScheduleClick?: () => void;
}

export default function InboxReminder({
  unreadCount,
  onCategoryClick,
  onAddTagsClick,
  onFlaggedClick,
  onRefreshClick,
  onTaskScheduleClick
}: InboxReminderProps) {
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
          className="pb-2 px-1 text-sm font-medium border-b-2 border-primary -mb-px"
          data-testid="tab-inbox-reminder"
        >
          📋 Inbox Reminder
        </button>
        <button 
          onClick={onTaskScheduleClick}
          className="pb-2 px-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          data-testid="tab-task-schedule"
        >
          ⏰ Task & Schedule
        </button>
      </div>

      {/* Category Cards */}
      <div className="space-y-4 mb-4">
        {/* Urgent Card */}
        <button
          onClick={() => onCategoryClick("urgent")}
          className="w-full bg-[#B8A0C7] hover:bg-[#A890B7] rounded-2xl p-5 text-left transition-all hover:shadow-md"
          data-testid="card-urgent"
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-[#5B2C6F]">Urgent</h3>
            <span className="text-5xl font-bold text-[#8B6B9E] opacity-70">2</span>
          </div>
          <p className="text-sm text-[#5B2C6F] font-medium mb-1">
            Latest: Contract Signature Required
          </p>
          <p className="text-sm text-[#5B2C6F]/70 line-clamp-2">
            "Please review and sign the updated contract before the end of the day."
          </p>
        </button>

        {/* To-Do Card */}
        <button
          onClick={() => onCategoryClick("todo")}
          className="w-full bg-[#D4C4E0] hover:bg-[#C4B4D0] rounded-2xl p-5 text-left transition-all hover:shadow-md"
          data-testid="card-todo"
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-[#5B2C6F]">To-Do</h3>
            <span className="text-5xl font-bold text-[#8B6B9E] opacity-60">6</span>
          </div>
          <p className="text-sm text-[#5B2C6F] font-medium mb-1">
            Latest: Budget review meeting follow-up
          </p>
          <p className="text-sm text-[#5B2C6F]/70 line-clamp-2">
            "Here are the action items assigned to you. Deadline: Oct 10..."
          </p>
        </button>

        {/* FYI Card */}
        <button
          onClick={() => onCategoryClick("fyi")}
          className="w-full bg-[#B8A0C7] hover:bg-[#A890B7] rounded-2xl p-5 text-left transition-all hover:shadow-md"
          data-testid="card-fyi"
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-[#5B2C6F]">FYI</h3>
            <span className="text-5xl font-bold text-[#8B6B9E] opacity-50">13</span>
          </div>
          <p className="text-sm text-[#5B2C6F] font-medium mb-1">
            Latest: Team offsite photos
          </p>
          <p className="text-sm text-[#5B2C6F]/70 line-clamp-2">
            "Sharing a link to the photos from last week's offsite..."
          </p>
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
          className="w-14 h-14 rounded-full bg-[#B8A0C7] hover:bg-[#A890B7] shadow-lg flex items-center justify-center transition-all hover:scale-105"
          data-testid="button-flagged"
        >
          <Bookmark className="w-6 h-6 text-white" />
        </button>
        <button
          onClick={onRefreshClick}
          className="w-14 h-14 rounded-full bg-[#B8A0C7] hover:bg-[#A890B7] shadow-lg flex items-center justify-center transition-all hover:scale-105"
          data-testid="button-refresh"
        >
          <RefreshCw className="w-6 h-6 text-white" />
        </button>
      </div>
    </div>
  );
}
