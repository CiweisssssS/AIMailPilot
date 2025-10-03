/**
 * Main sidebar card showing email analysis
 */

function createSidebarCard(result) {
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('AI Email Analysis')
      .setSubtitle('Powered by AI'));
  
  // Priority section
  card.addSection(createPrioritySection(result.priority));
  
  // Summary section
  card.addSection(createSummarySection(result.summary));
  
  // Tasks section
  if (result.tasks && result.tasks.length > 0) {
    card.addSection(createTasksSection(result.tasks));
  }
  
  // Timeline section
  if (result.thread && result.thread.timeline) {
    card.addSection(createTimelineSection(result.thread.timeline));
  }
  
  // Action buttons
  card.addSection(createActionsSection(result.thread));
  
  return [card.build()];
}

/**
 * Priority section with badge
 */
function createPrioritySection(priority) {
  const section = CardService.newCardSection()
    .setHeader('Priority Classification');
  
  const priorityColor = getPriorityColor(priority.label);
  const priorityText = `<b><font color="${priorityColor}">${priority.label}</font></b> (Score: ${priority.score.toFixed(2)})`;
  
  section.addWidget(CardService.newTextParagraph()
    .setText(priorityText));
  
  // Show reasons
  if (priority.reasons && priority.reasons.length > 0) {
    let reasonsText = '<b>Reasons:</b><br>';
    priority.reasons.forEach(function(reason) {
      reasonsText += '• ' + reason + '<br>';
    });
    
    section.addWidget(CardService.newTextParagraph()
      .setText(reasonsText));
  }
  
  return section;
}

/**
 * Summary section
 */
function createSummarySection(summary) {
  const section = CardService.newCardSection()
    .setHeader('Summary');
  
  section.addWidget(CardService.newTextParagraph()
    .setText(summary));
  
  return section;
}

/**
 * Tasks section
 */
function createTasksSection(tasks) {
  const section = CardService.newCardSection()
    .setHeader('Extracted Tasks (' + tasks.length + ')');
  
  tasks.forEach(function(task, index) {
    let taskText = '<b>' + truncateText(task.title, 100) + '</b><br>';
    
    if (task.owner) {
      taskText += '👤 ' + task.owner + '<br>';
    }
    
    if (task.due) {
      const dueDate = new Date(task.due);
      taskText += '📅 ' + formatDate(dueDate) + '<br>';
    }
    
    taskText += '<font color="#666">' + task.type + '</font>';
    
    section.addWidget(CardService.newTextParagraph()
      .setText(taskText));
    
    if (index < tasks.length - 1) {
      section.addWidget(CardService.newDivider());
    }
  });
  
  return section;
}

/**
 * Timeline section
 */
function createTimelineSection(timeline) {
  const section = CardService.newCardSection()
    .setHeader('Thread Timeline (' + timeline.length + ' messages)');
  
  timeline.forEach(function(entry, index) {
    const date = new Date(entry.date);
    const timelineText = '<b>' + formatDate(date) + '</b><br>' + 
                         '<font color="#666">' + truncateText(entry.subject, 60) + '</font>';
    
    section.addWidget(CardService.newTextParagraph()
      .setText(timelineText));
    
    if (index < timeline.length - 1) {
      section.addWidget(CardService.newDivider());
    }
  });
  
  return section;
}

/**
 * Actions section with buttons
 */
function createActionsSection(thread) {
  const section = CardService.newCardSection();
  
  // Chat button
  const chatAction = CardService.newAction()
    .setFunctionName('showChatCard')
    .setParameters({thread: JSON.stringify(thread)});
  
  section.addWidget(CardService.newTextButton()
    .setText('💬 Ask Questions')
    .setOnClickAction(chatAction)
    .setTextButtonStyle(CardService.TextButtonStyle.FILLED));
  
  // Settings button
  const settingsAction = CardService.newAction()
    .setFunctionName('showSettingsCard');
  
  section.addWidget(CardService.newTextButton()
    .setText('⚙️ Manage Keywords')
    .setOnClickAction(settingsAction));
  
  return section;
}

/**
 * Helper: Get priority color
 */
function getPriorityColor(label) {
  switch(label) {
    case 'P1': return '#dc2626';
    case 'P2': return '#f59e0b';
    case 'P3': return '#10b981';
    default: return '#6b7280';
  }
}

/**
 * Helper: Truncate text
 */
function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Helper: Format date
 */
function formatDate(date) {
  const options = { 
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
  };
  return date.toLocaleString('en-US', options);
}
