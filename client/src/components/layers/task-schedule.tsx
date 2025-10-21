import { Mail, Calendar, Bookmark, RefreshCw, AlertCircle, Clock } from "lucide-react";
import type { AnalyzedEmail } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";
import { groupTasksByBucket, parseDeadline, type TimeBucket } from "@/lib/date-utils";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiRequest, queryClient } from "@/lib/queryClient";

interface TaskScheduleProps {
  analyzedEmails: AnalyzedEmail[];
  onFlaggedClick: () => void;
  onRefreshClick: () => void;
  onInboxReminderClick?: () => void;
}

interface TaskWithEmail {
  email: AnalyzedEmail;
  taskIndex: number;
  due: string | null;
}

export default function TaskSchedule({ analyzedEmails, onFlaggedClick, onRefreshClick, onInboxReminderClick }: TaskScheduleProps) {
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
      <div className="space-y-6 pb-24">
        {/* TBD Tasks - Pinned at Top */}
        {groupedTasks.tbd.length > 0 && (
          <TimelineBucket
            title="Tasks Pending Deadline Confirmation"
            tasks={groupedTasks.tbd}
            bucket="tbd"
            color="destructive"
          />
        )}

        {/* Today (includes overdue) */}
        {(groupedTasks.today.length > 0 || groupedTasks.overdue.length > 0) && (
          <TimelineBucket
            title="Today"
            tasks={[...groupedTasks.overdue, ...groupedTasks.today]}
            bucket="today"
            color="primary"
          />
        )}

        {/* This Week */}
        {groupedTasks.this_week.length > 0 && (
          <TimelineBucket
            title="This Week"
            tasks={groupedTasks.this_week}
            bucket="this_week"
            color="primary"
          />
        )}

        {/* This Month */}
        {groupedTasks.this_month.length > 0 && (
          <TimelineBucket
            title="This Month"
            tasks={groupedTasks.this_month}
            bucket="this_month"
            color="muted"
          />
        )}

        {/* Later */}
        {groupedTasks.later.length > 0 && (
          <TimelineBucket
            title="Later"
            tasks={groupedTasks.later}
            bucket="later"
            color="muted"
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
}

function TimelineBucket({ title, tasks, bucket, color }: TimelineBucketProps) {
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
    <div>
      {/* Bucket Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-3 h-3 rounded-full ${nodeColor}`} />
        <h3 className={`text-lg font-semibold ${titleColor}`}>{title}</h3>
      </div>

      {/* Timeline Items */}
      <div className="ml-6 border-l-2 border-border pl-6 space-y-3">
        {tasks.map((task, index) => (
          <TimelineItem
            key={`${task.email.id}-${task.taskIndex}`}
            task={task}
            showOverdueBadge={bucket === "today" && parseDeadline(task.due).bucket === "overdue"}
          />
        ))}
      </div>
    </div>
  );
}

interface TimelineItemProps {
  task: TaskWithEmail;
  showOverdueBadge?: boolean;
}

function TimelineItem({ task, showOverdueBadge = false }: TimelineItemProps) {
  const { toast } = useToast();
  const [isEditingDeadline, setIsEditingDeadline] = useState(false);
  const [newDeadline, setNewDeadline] = useState("");

  const deadline = parseDeadline(task.due);
  const isTBD = deadline.bucket === "tbd";

  // Get task title (use task_extracted or subject)
  const taskTitle = task.email.task_extracted && task.email.task_extracted !== "None"
    ? task.email.task_extracted.replace(/^\[|\]$/g, '').trim()
    : task.email.subject;

  // Get priority badge color
  const priorityColor = {
    P1: "bg-destructive/10 text-destructive",
    P2: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-500",
    P3: "bg-muted text-muted-foreground"
  }[task.email.priority.label] || "bg-muted text-muted-foreground";

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
      
      await apiRequest("PATCH", `/api/tasks/${task.email.id}/${task.taskIndex}`, { due: formatted });

      // Update local cache
      queryClient.setQueryData(['/api/analyze-emails'], (oldData: any) => {
        if (!oldData) return oldData;
        
        return {
          ...oldData,
          analyzed_emails: oldData.analyzed_emails.map((email: any) => {
            if (email.id === task.email.id) {
              const updatedTasks = [...email.tasks];
              updatedTasks[task.taskIndex] = {
                ...updatedTasks[task.taskIndex],
                due: formatted
              };
              return { ...email, tasks: updatedTasks };
            }
            return email;
          })
        };
      });

      setIsEditingDeadline(false);
      setNewDeadline("");
      
      toast({
        title: "Deadline Updated",
        description: "Task deadline has been set successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update deadline. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div 
      className={`rounded-lg p-4 ${isTBD ? 'bg-destructive/5 border-2 border-destructive/20' : 'bg-card hover:bg-accent/50'} transition-colors`}
      data-testid={`timeline-item-${task.email.id}-${task.taskIndex}`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1">
          {/* Time & Priority */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-foreground flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {deadline.displayText}
            </span>
            {showOverdueBadge && (
              <Badge variant="destructive" className="text-xs px-2 py-0">
                Overdue
              </Badge>
            )}
            <Badge className={`text-xs px-2 py-0 ${priorityColor}`}>
              {task.email.priority.label}
            </Badge>
          </div>

          {/* Subject */}
          <p className="text-sm font-semibold text-foreground mb-1 line-clamp-1">
            Subject: {taskTitle}
          </p>

          {/* TBD Warning */}
          {isTBD && !isEditingDeadline && (
            <div className="flex items-center gap-2 text-destructive text-xs mt-2">
              <AlertCircle className="w-4 h-4" />
              <span>Deadline: TBD — please set manually</span>
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

        {/* Calendar Button */}
        <button 
          onClick={handleAddToCalendar}
          disabled={isTBD}
          className={`p-2 rounded-lg transition-colors ${
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
