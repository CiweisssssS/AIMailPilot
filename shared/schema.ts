import { z } from "zod";

export const emailMessageSchema = z.object({
  id: z.string(),
  thread_id: z.string(),
  date: z.string(),
  from: z.string(),
  to: z.array(z.string()),
  cc: z.array(z.string()).optional(),
  subject: z.string(),
  body: z.string(),
});

export const keywordSchema = z.object({
  term: z.string(),
  weight: z.number(),
  scope: z.string(),
});

export const processThreadRequestSchema = z.object({
  user_id: z.string(),
  personalized_keywords: z.array(keywordSchema).optional(),
  messages: z.array(emailMessageSchema),
});

export const normalizedMessageSchema = z.object({
  id: z.string(),
  clean_body: z.string(),
});

export const timelineEntrySchema = z.object({
  id: z.string(),
  date: z.string(),
  subject: z.string(),
});

export const threadResponseSchema = z.object({
  thread_id: z.string(),
  participants: z.array(z.string()),
  timeline: z.array(timelineEntrySchema),
  normalized_messages: z.array(normalizedMessageSchema),
});

export const taskSchema = z.object({
  title: z.string(),
  owner: z.string().nullable(),
  due: z.string().nullable(),
  source_message_id: z.string(),
  type: z.string(),
});

export const prioritySchema = z.object({
  label: z.string(),
  score: z.number(),
  reasons: z.array(z.string()),
});

export const processThreadResponseSchema = z.object({
  thread: threadResponseSchema,
  summary: z.string(),
  tasks: z.array(taskSchema),
  priority: prioritySchema,
});

export const chatbotQARequestSchema = z.object({
  question: z.string(),
  thread: threadResponseSchema,
});

export const chatbotQAResponseSchema = z.object({
  answer: z.string(),
  sources: z.array(z.string()),
});

// Gmail API schemas
export const gmailEmailSchema = z.object({
  id: z.string(),
  threadId: z.string(),
  subject: z.string(),
  from_: z.string(),
  to: z.array(z.string()),
  date: z.string(),
  snippet: z.string(),
  body: z.string(),
  clean_body: z.string(),
});

export const fetchGmailResponseSchema = z.object({
  success: z.boolean(),
  emails: z.array(gmailEmailSchema),
});

// Triage (batch analysis) schemas
export const triageMessageSchema = z.object({
  id: z.string(),
  threadId: z.string(),
  subject: z.string(),
  from_: z.string(),
  to: z.array(z.string()),
  date: z.string(),
  body: z.string(),
});

export const analyzedEmailSchema = z.object({
  id: z.string(),
  threadId: z.string(),
  subject: z.string(),
  from: z.string(),
  snippet: z.string(),
  date: z.string(),
  summary: z.string(),
  priority: prioritySchema,
  tasks: z.array(taskSchema),
  task_extracted: z.string().nullable().optional(),
});

export const triageResponseSchema = z.object({
  analyzed_emails: z.array(analyzedEmailSchema),
  summary: z.object({
    total: z.number(),
    urgent: z.number(),
    todo: z.number(),
    fyi: z.number(),
  }),
});

export type EmailMessage = z.infer<typeof emailMessageSchema>;
export type Keyword = z.infer<typeof keywordSchema>;
export type ProcessThreadRequest = z.infer<typeof processThreadRequestSchema>;
export type NormalizedMessage = z.infer<typeof normalizedMessageSchema>;
export type TimelineEntry = z.infer<typeof timelineEntrySchema>;
export type ThreadResponse = z.infer<typeof threadResponseSchema>;
export type Task = z.infer<typeof taskSchema>;
export type Priority = z.infer<typeof prioritySchema>;
export type ProcessThreadResponse = z.infer<typeof processThreadResponseSchema>;
export type ChatbotQARequest = z.infer<typeof chatbotQARequestSchema>;
export type ChatbotQAResponse = z.infer<typeof chatbotQAResponseSchema>;
export type GmailEmail = z.infer<typeof gmailEmailSchema>;
export type FetchGmailResponse = z.infer<typeof fetchGmailResponseSchema>;
export type TriageMessage = z.infer<typeof triageMessageSchema>;
export type AnalyzedEmail = z.infer<typeof analyzedEmailSchema>;
export type TriageResponse = z.infer<typeof triageResponseSchema>;
