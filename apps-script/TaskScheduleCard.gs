/**
 * Layer 1 - Task & Schedule Card
 * Shows timeline-based view of tasks extracted from emails
 */

/**
 * Create Task & Schedule Card
 * @param {Object} analysisResults - Map of threadId -> analysis
 */
function createTaskScheduleCard(analysisResults) {
  const card = CardService.newCardBuilder();
  
  // Header
  card.setHeader(CardService.newCardHeader()
    .setTitle('📅 Task & Schedule')
    .setSubtitle('Time-based task view'));
  
  // View toggle (back to Inbox Reminder)
  const viewToggle = CardService.newCardSection();
  const viewButtonSet = CardService.newButtonSet()
    .addButton(CardService.newTextButton()
      .setText('📧 Inbox')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('showInboxReminderView')))
    .addButton(CardService.newTextButton()
      .setText('• 📅 Tasks'));
  
  viewToggle.addWidget(viewButtonSet);
  card.addSection(viewToggle);
  
  // Extract all tasks from analysis results
  const allTasks = extractAllTasks(analysisResults);
  
  // Group tasks by timeline buckets
  const timeline = groupTasksByTimeline(allTasks);
  
  // Add timeline sections
  addTimelineBucket(card, 'Overdue ⚠️', timeline.overdue, analysisResults, '#EA4335');
  addTimelineBucket(card, 'Today 📌', timeline.today, analysisResults, '#FBBC04');
  addTimelineBucket(card, 'This Week 📆', timeline.thisWeek, analysisResults, '#4285F4');
  addTimelineBucket(card, 'Later 🗓️', timeline.later, analysisResults, '#9E9E9E');
  
  // Action buttons
  const actionsSection = CardService.newCardSection();
  actionsSection.addWidget(CardService.newButtonSet()
    .addButton(CardService.newTextButton()
      .setText('🔄 Refresh')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('refreshTaskSchedule')))
    .addButton(CardService.newTextButton()
      .setText('⚙️ Settings')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('showKeywordSettings'))));
  
  card.addSection(actionsSection);
  
  return card.build();
}

/**
 * Extract all tasks from analysis results
 */
function extractAllTasks(analysisResults) {
  const allTasks = [];
  
  Object.keys(analysisResults).forEach(threadId => {
    const analysis = analysisResults[threadId];
    
    if (analysis.tasks && analysis.tasks.length > 0) {
      analysis.tasks.forEach(task => {
        allTasks.push({
          threadId: threadId,
          task: task,
          subject: getThreadSubject(threadId)
        });
      });
    }
  });
  
  return allTasks;
}

/**
 * Get thread subject
 */
function getThreadSubject(threadId) {
  try {
    const thread = GmailApp.getThreadById(threadId);
    return thread ? thread.getFirstMessageSubject() : 'Unknown';
  } catch (error) {
    return 'Unknown';
  }
}

/**
 * Group tasks by timeline buckets
 */
function groupTasksByTimeline(allTasks) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const nextWeek = new Date(today);
  nextWeek.setDate(nextWeek.getDate() + 7);
  
  const timeline = {
    overdue: [],
    today: [],
    thisWeek: [],
    later: []
  };
  
  allTasks.forEach(item => {
    const task = item.task;
    
    if (task.due) {
      const dueDate = new Date(task.due);
      
      if (dueDate < today) {
        timeline.overdue.push(item);
      } else if (dueDate < tomorrow) {
        timeline.today.push(item);
      } else if (dueDate < nextWeek) {
        timeline.thisWeek.push(item);
      } else {
        timeline.later.push(item);
      }
    } else {
      timeline.later.push(item);
    }
  });
  
  return timeline;
}

/**
 * Add timeline bucket to card
 */
function addTimelineBucket(cardBuilder, bucketName, tasks, analysisResults, color) {
  if (tasks.length === 0) return;
  
  const section = CardService.newCardSection();
  
  // Bucket header
  const header = `<font color="${color}"><b>${bucketName}</b></font> (${tasks.length})`;
  section.addWidget(CardService.newTextParagraph().setText(header));
  
  // Show first 3 tasks
  const previewCount = Math.min(3, tasks.length);
  for (let i = 0; i < previewCount; i++) {
    const item = tasks[i];
    const task = item.task;
    const threadId = item.threadId;
    
    const dueText = task.due ? formatDueDate(task.due) : 'No date';
    const taskText = `• ${task.title.substring(0, 50)}<br><i>${dueText} • ${item.subject.substring(0, 40)}</i>`;
    
    section.addWidget(CardService.newTextParagraph().setText(taskText));
    
    // Action buttons for each task
    const taskButtons = CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('Open')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('openThreadFromTask')
          .setParameters({threadId: threadId})))
      .addButton(CardService.newTextButton()
        .setText('Add to Calendar')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('addTaskToCalendar')
          .setParameters({
            title: task.title,
            due: task.due || '',
            threadId: threadId
          })));
    
    section.addWidget(taskButtons);
  }
  
  cardBuilder.addSection(section);
}

/**
 * Format due date for display
 */
function formatDueDate(dueIso) {
  try {
    const due = new Date(dueIso);
    const now = new Date();
    const diffHours = (due - now) / (1000 * 60 * 60);
    
    if (diffHours < 0) {
      return '⚠️ Overdue';
    } else if (diffHours < 24) {
      return `⏰ ${Math.floor(diffHours)}h left`;
    } else {
      const diffDays = Math.floor(diffHours / 24);
      return `📅 in ${diffDays}d`;
    }
  } catch (error) {
    return 'No date';
  }
}

/**
 * Add task to calendar
 */
function addTaskToCalendar(e) {
  const title = e.parameters.title;
  const dueIso = e.parameters.due;
  const threadId = e.parameters.threadId;
  
  try {
    const calendar = CalendarApp.getDefaultCalendar();
    
    if (dueIso) {
      const dueDate = new Date(dueIso);
      const event = calendar.createAllDayEvent(title, dueDate);
      event.setDescription(`From Gmail thread: https://mail.google.com/mail/u/0/#inbox/${threadId}`);
      
      return CardService.newActionResponseBuilder()
        .setNotification(CardService.newNotification()
          .setText('✅ Added to calendar'))
        .build();
    } else {
      return CardService.newActionResponseBuilder()
        .setNotification(CardService.newNotification()
          .setText('❌ No due date found'))
        .build();
    }
  } catch (error) {
    console.error('Error adding to calendar:', error);
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('❌ Failed to add to calendar'))
      .build();
  }
}

/**
 * Open thread from task
 */
function openThreadFromTask(e) {
  const threadId = e.parameters.threadId;
  const url = `https://mail.google.com/mail/u/0/#inbox/${threadId}`;
  
  return CardService.newActionResponseBuilder()
    .setOpenLink(CardService.newOpenLink()
      .setUrl(url)
      .setOpenAs(CardService.OpenAs.FULL_SIZE)
      .setOnClose(CardService.OnClose.NOTHING))
    .build();
}

/**
 * Show inbox reminder view
 */
function showInboxReminderView(e) {
  const threadIds = fetchCandidateThreads('all');
  const analysisResults = analyzeThreadsWithCache(threadIds);
  
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .updateCard(createInboxReminderCard(analysisResults, 'all')))
    .build();
}

/**
 * Refresh task schedule
 */
function refreshTaskSchedule(e) {
  const threadIds = fetchCandidateThreads('all');
  const analysisResults = analyzeThreadsWithCache(threadIds);
  
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .updateCard(createTaskScheduleCard(analysisResults)))
    .build();
}
