import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Calendar, AlertTriangle } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface DeadlineEditorProps {
  emailId: string;
  taskIndex: number;
  currentDeadline: string | null;
  isTBD: boolean;
  onDeadlineUpdated?: (newDeadline: string) => void;
  className?: string;
}

export function DeadlineEditor({
  emailId,
  taskIndex,
  currentDeadline,
  isTBD,
  onDeadlineUpdated,
  className = ""
}: DeadlineEditorProps) {
  const { toast } = useToast();
  const [isEditing, setIsEditing] = useState(false);
  const [newDeadline, setNewDeadline] = useState("");

  const handleSetDeadline = async () => {
    if (!newDeadline) return;

    try {
      // Convert datetime-local format (YYYY-MM-DDTHH:mm) to "Mon DD, YYYY, HH:mm"
      const date = new Date(newDeadline);
      const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const formatted = `${monthNames[date.getMonth()]} ${date.getDate().toString().padStart(2, '0')}, ${date.getFullYear()}, ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
      
      // Save to database via deadline override API
      await apiRequest("POST", "/api/deadline-overrides", {
        email_id: emailId,
        task_index: taskIndex,
        original_deadline: currentDeadline || "TBD",
        override_deadline: formatted
      });

      // Update local state
      setIsEditing(false);
      setNewDeadline("");
      
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['/api/deadline-overrides'] });
      
      // Call callback if provided
      onDeadlineUpdated?.(formatted);

      toast({
        title: "Deadline Updated",
        description: `Deadline set to ${formatted}`,
      });
    } catch (error) {
      console.error("Failed to set deadline:", error);
      toast({
        title: "Error",
        description: "Failed to update deadline. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (!isEditing) {
    return isTBD ? (
      <button
        onClick={() => setIsEditing(true)}
        className={`text-xs bg-destructive/10 text-destructive px-2 py-1 rounded flex items-center gap-1 hover:bg-destructive/20 transition-colors ${className}`}
        data-testid={`button-set-deadline-${emailId}-${taskIndex}`}
      >
        <AlertTriangle className="w-3 h-3" />
        Set Deadline
      </button>
    ) : null;
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <input
        type="datetime-local"
        value={newDeadline}
        onChange={(e) => setNewDeadline(e.target.value)}
        className="text-xs border rounded px-2 py-1 bg-background"
        data-testid={`input-deadline-${emailId}-${taskIndex}`}
      />
      <Button
        size="sm"
        onClick={handleSetDeadline}
        className="h-7 text-xs"
        data-testid={`button-save-deadline-${emailId}-${taskIndex}`}
      >
        Save
      </Button>
      <Button
        size="sm"
        variant="ghost"
        onClick={() => {
          setIsEditing(false);
          setNewDeadline("");
        }}
        className="h-7 text-xs"
      >
        Cancel
      </Button>
    </div>
  );
}

interface AddToCalendarButtonProps {
  emailId: string;
  taskIndex: number;
  title: string;
  deadline: string | null;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export function AddToCalendarButton({
  emailId,
  taskIndex,
  title,
  deadline,
  description,
  disabled = false,
  className = ""
}: AddToCalendarButtonProps) {
  const { toast } = useToast();

  const createEventMutation = useMutation({
    mutationFn: async () => {
      if (!deadline || deadline === "TBD") {
        throw new Error("Cannot add TBD deadline to calendar");
      }

      return await apiRequest("POST", "/api/calendar/create-event", {
        title: title,
        description: description || "",
        startDateTime: deadline,
      });
    },
    onSuccess: (data: any) => {
      toast({
        title: "Added to Calendar",
        description: "Event created successfully in Google Calendar",
      });
      
      // Open the calendar event in a new tab
      if (data.eventLink) {
        window.open(data.eventLink, '_blank');
      }
    },
    onError: (error: any) => {
      console.error("Failed to create calendar event:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to create calendar event. Please try again.",
        variant: "destructive",
      });
    }
  });

  const handleAddToCalendar = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering parent click handlers
    
    if (disabled || !deadline || deadline === "TBD") {
      return;
    }
    
    createEventMutation.mutate();
  };

  return (
    <button
      onClick={handleAddToCalendar}
      disabled={disabled || createEventMutation.isPending}
      className={`flex items-center gap-2 transition-colors ${
        disabled 
          ? 'opacity-30 cursor-not-allowed' 
          : 'hover:bg-primary/10 cursor-pointer'
      } ${className}`}
      data-testid={`button-add-calendar-${emailId}-${taskIndex}`}
    >
      <Calendar className={`w-5 h-5 ${disabled ? 'text-muted-foreground' : 'text-primary'}`} />
      {createEventMutation.isPending && <span className="text-xs">Adding...</span>}
    </button>
  );
}
