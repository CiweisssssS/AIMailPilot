import { Mail, Calendar, Bookmark, RefreshCw, AlertCircle, Clock } from "lucide-react";
import type { AnalyzedEmail } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";
import { groupTasksByBucket, parseDeadline, type TimeBucket } from "@/lib/date-utils";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { ANALYZED_EMAILS_CACHE_KEY } from "@/hooks/use-emails";

interface TaskScheduleProps {
  analyzedEmails: AnalyzedEmail[];
  onFlaggedClick: () => void;
  onRefreshClick: () => void;
  onInboxReminderClick?: () => void;
  onTaskClick?: (emailId: string, taskIndex: number) => void;
  selectedTaskId?: { emailId: string; taskIndex: number };
}

interface TaskWithEmail {
  email: AnalyzedEmail;
  taskIndex: number;
  due: string | null;
}

export default function TaskSchedule({ analyzedEmails, onFlaggedClick, onRefreshClick, onInboxReminderClick, onTaskClick, selectedTaskId }: TaskScheduleProps) {
  // Flatten all tasks with their email context, filter for P1 and P2 only
  const allTasks: TaskWithEmail[] = analyzedEmails
    .filter(email => email.priority?.label === 'P1' || email.priority?.label === 'P2')
    .flatMap(email =>
      email.tasks.map((task, index) => ({
        email,
        taskIndex: index,
        due: task.due
      }))
    );

  // Group tasks by time bucket
  const groupedTasks = groupTasksByBucket(allTasks);

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

      {/* Chronological Timeline */}
      <div className="space-y-8 pb-24">
        {/* TBD Tasks - Pinned at Top */}
        {groupedTasks.tbd.length > 0 && (
          <TimelineBucket
            title="Tasks Pending Deadline Confirmation"
            tasks={groupedTasks.tbd}
            bucket="tbd"
            color="destructive"
            onTaskClick={onTaskClick}
            selectedTaskId={selectedTaskId}
          />
        )}

        {/* Today (includes overdue) */}
        {(groupedTasks.today.length > 0 || groupedTasks.overdue.length > 0) && (
          <TimelineBucket
            title="Today"
            tasks={[...groupedTasks.overdue, ...groupedTasks.today]}
            bucket="today"
            color="primary"
            onTaskClick={onTaskClick}
            selectedTaskId={selectedTaskId}
          />
        )}

        {/* This Week */}
        {groupedTasks.this_week.length > 0 && (
          <TimelineBucket
            title="This Week"
            tasks={groupedTasks.this_week}
            bucket="this_week"
            color="primary"
            onTaskClick={onTaskClick}
            selectedTaskId={selectedTaskId}
          />
        )}

        {/* This Month */}
        {groupedTasks.this_month.length > 0 && (
          <TimelineBucket
            title="This Month"
            tasks={groupedTasks.this_month}
            bucket="this_month"
            color="muted"
            onTaskClick={onTaskClick}
            selectedTaskId={selectedTaskId}
          />
        )}

        {/* Later */}
        {groupedTasks.later.length > 0 && (
          <TimelineBucket
            title="Later"
            tasks={groupedTasks.later}
            bucket="later"
            color="muted"
            onTaskClick={onTaskClick}
            selectedTaskId={selectedTaskId}
          />
        )}

        {/* No tasks message */}
        {allTasks.length === 0 && (
          <div className="text-center text-muted-foreground p-8">
            No tasks extracted yet
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

interface TimelineBucketProps {
  title: string;
  tasks: TaskWithEmail[];
  bucket: TimeBucket;
  color: "primary" | "destructive" | "muted";
  onTaskClick?: (emailId: string, taskIndex: number) => void;
  selectedTaskId?: { emailId: string; taskIndex: number };
}

function TimelineBucket({ title, tasks, bucket, color, onTaskClick, selectedTaskId }: TimelineBucketProps) {
  const nodeColor = {
    primary: "bg-primary",
    destructive: "bg-destructive",
    muted: "bg-muted-foreground/40"
  }[color];

  const titleColor = {
    primary: "text-primary",
    destructive: "text-destructive",
    muted: "text-muted-foreground"
  }[color];

  return (
    <div className="mb-8">
      {/* Bucket Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className={`w-3 h-3 rounded-full ${nodeColor}`} />
        <h3 className={`text-xl font-bold ${titleColor}`}>{title}</h3>
      </div>

      {/* Timeline Items */}
      <div className="ml-6 border-l-2 border-border pl-6 space-y-6">
        {tasks.map((task, index) => (
          <TimelineItem
            key={`${task.email.id}-${task.taskIndex}`}
            task={task}
            showOverdueBadge={bucket === "today" && parseDeadline(task.due).bucket === "overdue"}
            onTaskClick={onTaskClick}
            selectedTaskId={selectedTaskId}
          />
        ))}
      </div>
    </div>
  );
}

interface TimelineItemProps {
  task: TaskWithEmail;
  showOverdueBadge?: boolean;
  onTaskClick?: (emailId: string, taskIndex: number) => void;
  selectedTaskId?: { emailId: string; taskIndex: number };
}

function TimelineItem({ task, showOverdueBadge = false, onTaskClick, selectedTaskId }: TimelineItemProps) {
  const { toast } = useToast();
  const [isEditingDeadline, setIsEditingDeadline] = useState(false);
  const [newDeadline, setNewDeadline] = useState("");

  const deadline = parseDeadline(task.due);
  const isTBD = deadline.bucket === "tbd";

  // Get task title (use task_extracted or subject)
  const taskTitle = task.email.task_extracted && task.email.task_extracted !== "None"
    ? task.email.task_extracted.replace(/^\[|\]$/g, '').trim()
    : task.email.subject;

  // Check if this task is selected
  const isSelected = selectedTaskId?.emailId === task.email.id && selectedTaskId?.taskIndex === task.taskIndex;

  // Handle task click - open email and highlight card
  const handleClick = () => {
    onTaskClick?.(task.email.id, task.taskIndex);
  };

  // Format time display: "Time: Oct 5, 10:00 AM"
  const formatTimeDisplay = (dueString: string | null) => {
    if (!dueString || dueString === "TBD") return "TBD";
    
    try {
      // Parse "Mon DD, YYYY, HH:mm" format
      const parts = dueString.split(', ');
      if (parts.length >= 3) {
        const monthDay = parts[0]; // "Oct 27"
        const year = parts[1]; // "2025"
        const time = parts[2]; // "10:00"
        
        // Convert 24h to 12h format
        const [hours, minutes] = time.split(':').map(Number);
        const period = hours >= 12 ? 'PM' : 'AM';
        const displayHours = hours % 12 || 12;
        
        return `${monthDay}, ${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;
      }
    } catch (e) {
      // Fallback to original
    }
    return dueString;
  };

  const handleAddToCalendar = () => {
    if (isTBD) {
      return; // Disabled for TBD
    }
    toast({
      title: "Add to Calendar",
      description: "Calendar integration coming soon!",
    });
  };

  const handleSetDeadline = async () => {
    if (!newDeadline) return;

    try {
      // Convert datetime-local format (YYYY-MM-DDTHH:mm) to "Mon DD, YYYY, HH:mm"
      const date = new Date(newDeadline);
      const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const formatted = `${monthNames[date.getMonth()]} ${date.getDate().toString().padStart(2, '0')}, ${date.getFullYear()}, ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
      
      // Save to database via deadline override API
      await apiRequest("POST", "/api/deadline-overrides", {
        email_id: task.email.id,
        task_index: task.taskIndex,
        original_deadline: task.due || "TBD",
        override_deadline: formatted
      });

      // Update React Query cache
      queryClient.setQueryData(ANALYZED_EMAILS_CACHE_KEY, (oldData: AnalyzedEmail[] | undefined) => {
        if (!oldData) return oldData;
        
        return oldData.map((email) => {
          if (email.id === task.email.id) {
            const updatedTasks = [...email.tasks];
            updatedTasks[task.taskIndex] = {
              ...updatedTasks[task.taskIndex],
              due: formatted
            };
            return { ...email, tasks: updatedTasks };
          }
          return email;
        });
      });

      setIsEditingDeadline(false);
      setNewDeadline("");
      
      toast({
        title: "Deadline Updated",
        description: "Task deadline has been saved to database.",
      });
    } catch (error) {
      console.error("Deadline update failed:", error);
      toast({
        title: "Error",
        description: "Failed to update deadline. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div 
      className={`relative rounded-lg p-3 transition-all cursor-pointer ${
        isSelected 
          ? 'bg-primary/20 ring-2 ring-primary/30' 
          : 'hover:bg-accent/30'
      }`}
      onClick={handleClick}
      data-testid={`timeline-item-${task.email.id}-${task.taskIndex}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Time Line */}
          <div className="text-sm text-muted-foreground mb-1">
            Time: {formatTimeDisplay(task.due)}
            {showOverdueBadge && (
              <Badge variant="destructive" className="text-xs px-2 py-0 ml-2">
                Overdue
              </Badge>
            )}
          </div>

          {/* Task Line */}
          <div className="text-sm font-semibold text-foreground line-clamp-2 leading-relaxed">
            Task: {taskTitle}
          </div>

          {/* TBD Warning */}
          {isTBD && !isEditingDeadline && (
            <div className="flex items-center gap-2 text-destructive text-xs mt-2">
              <AlertCircle className="w-4 h-4" />
              <span>Please set deadline manually</span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsEditingDeadline(true)}
                className="ml-auto h-7 text-xs"
                data-testid={`button-set-deadline-${task.email.id}-${task.taskIndex}`}
              >
                Set Deadline
              </Button>
            </div>
          )}

          {/* Deadline Picker */}
          {isEditingDeadline && (
            <div className="mt-2 flex items-center gap-2">
              <input
                type="datetime-local"
                value={newDeadline}
                onChange={(e) => setNewDeadline(e.target.value)}
                className="text-xs border rounded px-2 py-1 bg-background"
                data-testid={`input-deadline-${task.email.id}-${task.taskIndex}`}
              />
              <Button
                size="sm"
                onClick={handleSetDeadline}
                className="h-7 text-xs"
                data-testid={`button-save-deadline-${task.email.id}-${task.taskIndex}`}
              >
                Save
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setIsEditingDeadline(false);
                  setNewDeadline("");
                }}
                className="h-7 text-xs"
              >
                Cancel
              </Button>
            </div>
          )}
        </div>

        {/* Calendar Icon */}
        <button 
          onClick={handleAddToCalendar}
          disabled={isTBD}
          className={`flex-shrink-0 p-2 rounded-lg transition-colors ${
            isTBD 
              ? 'opacity-30 cursor-not-allowed' 
              : 'hover:bg-primary/10 cursor-pointer'
          }`}
          data-testid={`button-add-calendar-${task.email.id}-${task.taskIndex}`}
        >
          <Calendar className={`w-5 h-5 ${isTBD ? 'text-muted-foreground' : 'text-primary'}`} />
        </button>
      </div>
    </div>
  );
}
