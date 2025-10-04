/**
 * Layer 2 - Category Expanded Card
 * Shows filtered list of emails in a category with actions
 */

/**
 * Create Category Expanded Card
 * @param {string} categoryName
 * @param {Array} threadIds - Array of thread IDs in this category
 */
function createCategoryExpandedCard(categoryName, threadIds) {
  const card = CardService.newCardBuilder();
  
  // Header
  card.setHeader(CardService.newCardHeader()
    .setTitle(categoryName)
    .setSubtitle(`${threadIds.length} emails`));
  
  // Get analysis results
  const analysisResults = analyzeThreadsWithCache(threadIds);
  
  // Show up to 10 emails
  const displayCount = Math.min(10, threadIds.length);
  
  for (let i = 0; i < displayCount; i++) {
    const threadId = threadIds[i];
    const analysis = analysisResults[threadId];
    
    if (!analysis) continue;
    
    const thread = GmailApp.getThreadById(threadId);
    if (!thread) continue;
    
    const section = CardService.newCardSection();
    
    // Email subject
    const subject = thread.getFirstMessageSubject();
    section.addWidget(CardService.newTextParagraph()
      .setText(`<b>${subject}</b>`));
    
    // Summary
    const summary = analysis.summary || 'No summary available';
    section.addWidget(CardService.newTextParagraph()
      .setText(`<i>${summary}</i>`));
    
    // Priority and timestamp
    const priority = analysis.priority ? analysis.priority.label : 'P3';
    const messages = thread.getMessages();
    const lastMessage = messages[messages.length - 1];
    const date = lastMessage.getDate();
    const timeAgo = getTimeAgo(date);
    
    section.addWidget(CardService.newTextParagraph()
      .setText(`Priority: ${priority} • ${timeAgo}`));
    
    // Tasks (if any)
    if (analysis.tasks && analysis.tasks.length > 0) {
      analysis.tasks.forEach(task => {
        const dueText = task.due ? formatDueDate(task.due) : '';
        section.addWidget(CardService.newTextParagraph()
          .setText(`📌 ${task.title.substring(0, 60)} ${dueText}`));
        
        if (task.due) {
          section.addWidget(CardService.newTextButton()
            .setText('Add to Calendar')
            .setOnClickAction(CardService.newAction()
              .setFunctionName('addTaskToCalendar')
              .setParameters({
                title: task.title,
                due: task.due,
                threadId: threadId
              })));
        }
      });
    }
    
    // Store threadIds in cache to avoid parameter size limits
    const cacheKey = 'expand_' + categoryName.replace(/[^a-zA-Z0-9]/g, '_') + '_' + Date.now();
    getCacheService().put(cacheKey, JSON.stringify(threadIds), 300);
    
    // Action buttons
    const actionButtons = CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('Open')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('openThreadAction')
          .setParameters({threadId: threadId})))
      .addButton(CardService.newTextButton()
        .setText('Done')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('markThreadDone')
          .setParameters({
            threadId: threadId,
            categoryName: categoryName,
            cacheKey: cacheKey
          })))
      .addButton(CardService.newTextButton()
        .setText('Snooze')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('snoozeThreadAction')
          .setParameters({
            threadId: threadId,
            categoryName: categoryName,
            cacheKey: cacheKey
          })))
      .addButton(CardService.newTextButton()
        .setText('Dismiss')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('dismissThreadAction')
          .setParameters({
            threadId: threadId,
            categoryName: categoryName,
            cacheKey: cacheKey
          })));
    
    section.addWidget(actionButtons);
    section.addWidget(CardService.newDivider());
    
    card.addSection(section);
  }
  
  // "Load more" if there are more emails
  if (threadIds.length > displayCount) {
    const moreSection = CardService.newCardSection();
    moreSection.addWidget(CardService.newTextParagraph()
      .setText(`... and ${threadIds.length - displayCount} more`));
    card.addSection(moreSection);
  }
  
  // Footer section with "Ask Assistant" button
  const footerSection = CardService.newCardSection();
  
  // Store context in cache
  const chatCacheKey = 'chat_' + categoryName.replace(/[^a-zA-Z0-9]/g, '_');
  getCacheService().put(chatCacheKey, JSON.stringify({
    category: categoryName,
    threadIds: threadIds
  }), 300);
  
  footerSection.addWidget(CardService.newTextButton()
    .setText('💬 Ask Assistant')
    .setOnClickAction(CardService.newAction()
      .setFunctionName('showChatbot')
      .setParameters({
        contextKey: chatCacheKey
      })));
  
  card.addSection(footerSection);
  
  return card.build();
}

/**
 * Get time ago text
 */
function getTimeAgo(date) {
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffMins < 60) {
    return `${diffMins}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else {
    return `${diffDays}d ago`;
  }
}

/**
 * Open thread action
 */
function openThreadAction(e) {
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
 * Mark thread as done
 */
function markThreadDone(e) {
  const threadId = e.parameters.threadId;
  const categoryName = e.parameters.categoryName;
  const cacheKey = e.parameters.cacheKey;
  
  // Get remainingIds from cache
  const remainingIdsJson = getCacheService().get(cacheKey);
  const remainingIds = remainingIdsJson ? JSON.parse(remainingIdsJson) : [];
  
  // Remove from unresolved pool
  removeUnresolvedThreadId(threadId);
  
  // Clear cache
  clearThreadCache(threadId);
  
  // Optionally add Gmail label
  try {
    const thread = GmailApp.getThreadById(threadId);
    const label = GmailApp.getUserLabelByName('AI/Processed') || GmailApp.createLabel('AI/Processed');
    thread.addLabel(label);
  } catch (error) {
    console.error('Error adding label:', error);
  }
  
  // Update the category view
  const updatedIds = remainingIds.filter(id => id !== threadId);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('✅ Marked as done'))
    .setNavigation(CardService.newNavigation()
      .updateCard(createCategoryExpandedCard(categoryName, updatedIds)))
    .build();
}

/**
 * Snooze thread action
 */
function snoozeThreadAction(e) {
  const threadId = e.parameters.threadId;
  const categoryName = e.parameters.categoryName;
  const cacheKey = e.parameters.cacheKey;
  
  // Show snooze options card (pass cacheKey instead of remainingIds)
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .pushCard(createSnoozeOptionsCard(threadId, categoryName, cacheKey)))
    .build();
}

/**
 * Create snooze options card
 */
function createSnoozeOptionsCard(threadId, categoryName, cacheKey) {
  const card = CardService.newCardBuilder();
  
  card.setHeader(CardService.newCardHeader()
    .setTitle('Snooze Until'));
  
  const section = CardService.newCardSection();
  
  // Snooze options
  const options = [
    {label: '1 hour', hours: 1},
    {label: '3 hours', hours: 3},
    {label: 'Tomorrow', hours: 24},
    {label: 'Next week', hours: 168}
  ];
  
  options.forEach(option => {
    const now = new Date();
    const snoozeUntil = new Date(now.getTime() + option.hours * 60 * 60 * 1000);
    
    section.addWidget(CardService.newTextButton()
      .setText(option.label)
      .setOnClickAction(CardService.newAction()
        .setFunctionName('confirmSnooze')
        .setParameters({
          threadId: threadId,
          untilIso: snoozeUntil.toISOString(),
          categoryName: categoryName,
          cacheKey: cacheKey
        })));
  });
  
  card.addSection(section);
  
  return card.build();
}

/**
 * Confirm snooze
 */
function confirmSnooze(e) {
  const threadId = e.parameters.threadId;
  const untilIso = e.parameters.untilIso;
  const categoryName = e.parameters.categoryName;
  const cacheKey = e.parameters.cacheKey;
  
  // Get remainingIds from cache
  const remainingIdsJson = getCacheService().get(cacheKey);
  const remainingIds = remainingIdsJson ? JSON.parse(remainingIdsJson) : [];
  
  // Snooze the thread
  snoozeThread(threadId, untilIso);
  
  // Update the category view
  const updatedIds = remainingIds.filter(id => id !== threadId);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('⏰ Snoozed'))
    .setNavigation(CardService.newNavigation()
      .popToRoot()
      .updateCard(createCategoryExpandedCard(categoryName, updatedIds)))
    .build();
}

/**
 * Dismiss thread action
 */
function dismissThreadAction(e) {
  const threadId = e.parameters.threadId;
  const categoryName = e.parameters.categoryName;
  const cacheKey = e.parameters.cacheKey;
  
  // Get remainingIds from cache
  const remainingIdsJson = getCacheService().get(cacheKey);
  const remainingIds = remainingIdsJson ? JSON.parse(remainingIdsJson) : [];
  
  // Dismiss the thread
  dismissThread(threadId);
  
  // Clear cache
  clearThreadCache(threadId);
  
  // Update the category view
  const updatedIds = remainingIds.filter(id => id !== threadId);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('🚫 Dismissed'))
    .setNavigation(CardService.newNavigation()
      .updateCard(createCategoryExpandedCard(categoryName, updatedIds)))
    .build();
}
