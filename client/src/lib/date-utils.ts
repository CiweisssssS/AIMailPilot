/**
 * Date utilities for task timeline organization
 */

import { parse, isToday, isThisWeek, isThisMonth, isBefore, startOfDay } from "date-fns";

export type TimeBucket = "overdue" | "today" | "this_week" | "this_month" | "later" | "tbd";

export interface ParsedDeadline {
  date: Date | null;
  isValid: boolean;
  bucket: TimeBucket;
  displayText: string;
}

/**
 * Parse deadline string in format "Mon DD, YYYY, HH:mm" or "TBD"
 * 
 * @param deadline - Deadline string from backend
 * @returns Parsed deadline information
 */
export function parseDeadline(deadline: string | null): ParsedDeadline {
  if (!deadline || deadline === "TBD") {
    return {
      date: null,
      isValid: false,
      bucket: "tbd",
      displayText: "TBD"
    };
  }

  try {
    // Parse format: "Oct 21, 2023, 17:00"
    const date = parse(deadline, "MMM dd, yyyy, HH:mm", new Date());
    
    if (isNaN(date.getTime())) {
      return {
        date: null,
        isValid: false,
        bucket: "tbd",
        displayText: "TBD"
      };
    }

    const now = new Date();
    const bucket = getTimeBucket(date, now);
    const displayText = formatDeadlineDisplay(date, bucket);

    return {
      date,
      isValid: true,
      bucket,
      displayText
    };
  } catch (error) {
    return {
      date: null,
      isValid: false,
      bucket: "tbd",
      displayText: "TBD"
    };
  }
}

/**
 * Determine which time bucket a date falls into
 */
function getTimeBucket(date: Date, now: Date): TimeBucket {
  // Check if overdue
  if (isBefore(date, startOfDay(now))) {
    return "overdue";
  }

  // Check if today
  if (isToday(date)) {
    return "today";
  }

  // Check if this week (ISO week: Monday to Sunday)
  if (isThisWeek(date, { weekStartsOn: 1 })) {
    return "this_week";
  }

  // Check if this month
  if (isThisMonth(date)) {
    return "this_month";
  }

  // Everything else is later
  return "later";
}

/**
 * Format deadline for display based on time bucket
 */
function formatDeadlineDisplay(date: Date, bucket: TimeBucket): string {
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const time = `${hours}:${minutes}`;

  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const month = monthNames[date.getMonth()];
  const day = date.getDate();

  // Only show "Today" for items actually due today
  if (bucket === "today") {
    return `Today, ${time}`;
  }

  // Overdue and all other buckets show actual date
  return `${month} ${day}, ${time}`;
}

/**
 * Sort tasks by deadline within their bucket
 */
export function sortTasksByDeadline<T extends { due: string | null }>(tasks: T[]): T[] {
  return [...tasks].sort((a, b) => {
    const aDeadline = parseDeadline(a.due);
    const bDeadline = parseDeadline(b.due);

    // TBD tasks go last
    if (!aDeadline.isValid && !bDeadline.isValid) return 0;
    if (!aDeadline.isValid) return 1;
    if (!bDeadline.isValid) return -1;

    // Sort by date
    return aDeadline.date!.getTime() - bDeadline.date!.getTime();
  });
}

/**
 * Group tasks by time bucket
 */
export function groupTasksByBucket<T extends { due: string | null }>(tasks: T[]): Record<TimeBucket, T[]> {
  const groups: Record<TimeBucket, T[]> = {
    overdue: [],
    today: [],
    this_week: [],
    this_month: [],
    later: [],
    tbd: []
  };

  tasks.forEach(task => {
    const parsed = parseDeadline(task.due);
    groups[parsed.bucket].push(task);
  });

  // Sort tasks within each bucket
  Object.keys(groups).forEach(key => {
    groups[key as TimeBucket] = sortTasksByDeadline(groups[key as TimeBucket]);
  });

  return groups;
}
