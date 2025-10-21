import { Mail, Calendar, Bookmark, RefreshCw } from "lucide-react";

interface TaskScheduleProps {
  onFlaggedClick: () => void;
  onRefreshClick: () => void;
  onInboxReminderClick?: () => void;
}

export default function TaskSchedule({ onFlaggedClick, onRefreshClick, onInboxReminderClick }: TaskScheduleProps) {
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
          You have 21 unread emails.
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
        {/* Today Section */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-3 h-3 rounded-full bg-primary" />
            <h3 className="text-lg font-semibold text-primary">Today</h3>
          </div>
          <div className="ml-6 border-l-2 border-border pl-6 space-y-4">
            <TimelineItem
              time="Oct 5, 10:00 AM"
              subject="Team Sync Meeting - Agenda Attached"
            />
            <TimelineItem
              time="Oct 5, 9:00 PM"
              subject="Contract Signature Required"
            />
          </div>
        </div>

        {/* This Week Section */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-3 h-3 rounded-full bg-primary/60" />
            <h3 className="text-lg font-semibold text-primary/80">This Week</h3>
          </div>
          <div className="ml-6 border-l-2 border-border pl-6 space-y-4">
            <TimelineItem
              time="Oct 8, 1:00 PM"
              subject="Budget Review with Finance Team"
            />
            <TimelineItem
              time="Oct 9, 9:30 AM"
              subject="Product Demo with GlobalTech"
            />
          </div>
        </div>

        {/* In One Month Section */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-3 h-3 rounded-full bg-primary/40" />
            <h3 className="text-lg font-semibold text-primary/60">In one month</h3>
          </div>
          <div className="ml-6 border-l-2 border-border pl-6 space-y-4">
            <TimelineItem
              time="Oct 14, 3:00 PM"
              subject="Q4 Strategy Planning Session"
            />
            <TimelineItem
              time="Oct 28, 1:00 PM"
              subject="Budget Review with Finance Team"
            />
          </div>
        </div>
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
  time: string;
  subject: string;
}

function TimelineItem({ time, subject }: TimelineItemProps) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-card transition-colors">
      <div className="flex-1">
        <p className="text-sm font-medium text-foreground mb-1">Time: {time}</p>
        <p className="text-sm text-foreground">Subject: {subject}</p>
      </div>
      <button className="p-2 hover:bg-primary/10 rounded-lg" data-testid="button-add-calendar">
        <Calendar className="w-5 h-5 text-primary" />
      </button>
    </div>
  );
}
