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
    
    // Action buttons - simplified to Save/Flag/Done
    const actionButtons = CardService.newButtonSet()
      .addButton(CardService.newTextButton()
        .setText('Open')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('openThreadAction')
          .setParameters({threadId: threadId})));
    
    // Add Save button if there are tasks
    if (analysis.tasks && analysis.tasks.length > 0) {
      const firstTask = analysis.tasks[0];
      actionButtons.addButton(CardService.newTextButton()
        .setText('💾 Save')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('onSaveTask')
          .setParameters({
            threadId: threadId,
            title: firstTask.title,
            deadline: firstTask.due || '',
            owner: firstTask.owner || ''
          })));
    }
    
    actionButtons.addButton(CardService.newTextButton()
      .setText('🚩 Flag')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('onFlagMail')
        .setParameters({
          threadId: threadId,
          subject: subject,
          tags: JSON.stringify([])
        })))
      .addButton(CardService.newTextButton()
        .setText('✓ Done')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('onMarkAsDone')
          .setParameters({threadId: threadId})));
    
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

