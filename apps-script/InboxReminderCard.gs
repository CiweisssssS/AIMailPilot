/**
 * Layer 1 - Inbox Reminder Card
 * Shows categorized email counts and previews
 */

/**
 * Create Inbox Reminder Card (default view)
 * @param {Object} analysisResults - Map of threadId -> analysis
 * @param {string} displayMode - "new", "unresolved", or "all" (kept for compatibility)
 */
function createInboxReminderCard(analysisResults, displayMode) {
  const card = CardService.newCardBuilder();
  
  // Header
  card.setHeader(CardService.newCardHeader()
    .setTitle('📬 Inbox Reminder')
    .setSubtitle('AI-powered email insights'));
  
  // View navigation section
  const viewNav = CardService.newCardSection();
  viewNav.addWidget(CardService.newTextParagraph()
    .setText('<b>• 📧 Inbox View</b>'));
  
  const navButtonSet = CardService.newButtonSet()
    .addButton(CardService.newTextButton()
      .setText('📅 Tasks')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('showTaskScheduleView')))
    .addButton(CardService.newTextButton()
      .setText('🚩 Flagged')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('showFlaggedMails')));
  
  viewNav.addWidget(navButtonSet);
  card.addSection(viewNav);
  
  // Saved Tasks section
  const savedTasks = getSavedTasks();
  if (savedTasks.length > 0) {
    const savedSection = CardService.newCardSection();
    savedSection.addWidget(CardService.newTextParagraph()
      .setText(`<b>💾 Saved for Later</b> (${savedTasks.length})`));
    
    // Show first 2 saved tasks
    const previewCount = Math.min(2, savedTasks.length);
    for (let i = 0; i < previewCount; i++) {
      const task = savedTasks[i];
      const taskText = `• <b>${task.title.substring(0, 50)}</b>`;
      const deadlineText = task.deadline ? `<br><i>Due: ${task.deadline}</i>` : '';
      savedSection.addWidget(CardService.newTextParagraph()
        .setText(taskText + deadlineText));
    }
    
    savedSection.addWidget(CardService.newTextButton()
      .setText('View All Saved →')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('showTaskScheduleView')));
    
    card.addSection(savedSection);
  }
  
  // Categorize emails
  const categories = categorizeEmails(analysisResults);
  
  // Total count section
  const totalSection = CardService.newCardSection();
  totalSection.addWidget(CardService.newTextParagraph()
    .setText(`<b>Total: ${categories.total} emails</b>`));
  card.addSection(totalSection);
  
  // Category cards
  addCategoryCard(card, 'Urgent (P1)', categories.urgent, '#EA4335', analysisResults);
  addCategoryCard(card, 'To-do (P2)', categories.todo, '#FBBC04', analysisResults);
  addCategoryCard(card, 'FYI (P3)', categories.fyi, '#34A853', analysisResults);
  
  // User-defined categories from keywords
  const keywords = getUserKeywords();
  keywords.forEach(kw => {
    const customCategoryEmails = filterByKeyword(analysisResults, kw.term);
    if (customCategoryEmails.length > 0) {
      addCategoryCard(card, `${kw.term}`, customCategoryEmails, '#9E9E9E', analysisResults);
    }
  });
  
  // Action buttons section
  const actionsSection = CardService.newCardSection();
  actionsSection.addWidget(CardService.newButtonSet()
    .addButton(CardService.newTextButton()
      .setText('🔄 Refresh')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('refreshInbox')))
    .addButton(CardService.newTextButton()
      .setText('⚙️ Settings')
      .setOnClickAction(CardService.newAction()
        .setFunctionName('showKeywordSettings'))));
  
  card.addSection(actionsSection);
  
  return card.build();
}

/**
 * Categorize emails by priority
 */
function categorizeEmails(analysisResults) {
  const urgent = [];
  const todo = [];
  const fyi = [];
  
  Object.keys(analysisResults).forEach(threadId => {
    const analysis = analysisResults[threadId];
    const priority = analysis.priority ? analysis.priority.label : 'P3';
    
    if (priority === 'P1') {
      urgent.push(threadId);
    } else if (priority === 'P2') {
      todo.push(threadId);
    } else {
      fyi.push(threadId);
    }
  });
  
  return {
    total: Object.keys(analysisResults).length,
    urgent: urgent,
    todo: todo,
    fyi: fyi
  };
}

/**
 * Filter emails by keyword
 */
function filterByKeyword(analysisResults, keyword) {
  const filtered = [];
  const keywordLower = keyword.toLowerCase();
  
  Object.keys(analysisResults).forEach(threadId => {
    const analysis = analysisResults[threadId];
    const summary = (analysis.summary || '').toLowerCase();
    
    if (summary.includes(keywordLower)) {
      filtered.push(threadId);
    }
  });
  
  return filtered;
}

/**
 * Add a category card to the main card
 */
function addCategoryCard(cardBuilder, categoryName, threadIds, color, analysisResults) {
  const section = CardService.newCardSection();
  
  // Category header with count
  const header = `<font color="${color}"><b>${categoryName}</b></font> (${threadIds.length})`;
  section.addWidget(CardService.newTextParagraph().setText(header));
  
  // Show 1-2 preview items
  const previewCount = Math.min(2, threadIds.length);
  for (let i = 0; i < previewCount; i++) {
    const threadId = threadIds[i];
    const analysis = analysisResults[threadId];
    
    if (analysis) {
      const thread = GmailApp.getThreadById(threadId);
      const subject = thread ? thread.getFirstMessageSubject().substring(0, 50) : 'Unknown';
      const summary = analysis.summary ? analysis.summary.substring(0, 80) : '';
      
      section.addWidget(CardService.newTextParagraph()
        .setText(`• <b>${subject}</b><br><i>${summary}...</i>`));
    }
  }
  
  // "View more" button
  if (threadIds.length > 0) {
    // Store threadIds in cache to avoid parameter size limits
    const cacheKey = 'category_' + categoryName.replace(/[^a-zA-Z0-9]/g, '_');
    getCacheService().put(cacheKey, JSON.stringify(threadIds), 300); // 5 min TTL
    
    section.addWidget(CardService.newTextButton()
      .setText(`View ${categoryName} →`)
      .setOnClickAction(CardService.newAction()
        .setFunctionName('expandCategory')
        .setParameters({
          category: categoryName,
          cacheKey: cacheKey
        })));
  }
  
  cardBuilder.addSection(section);
}

/**
 * Show flagged mails (Layer 5)
 */
function showFlaggedMails(e) {
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .pushCard(createFlaggedMailCard()))
    .build();
}

/**
 * Expand category to Layer 2
 */
function expandCategory(e) {
  const category = e.parameters.category;
  const cacheKey = e.parameters.cacheKey;
  
  // Retrieve threadIds from cache
  const threadIdsJson = getCacheService().get(cacheKey);
  const threadIds = threadIdsJson ? JSON.parse(threadIdsJson) : [];
  
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .pushCard(createCategoryExpandedCard(category, threadIds)))
    .build();
}

/**
 * Show task & schedule view
 */
function showTaskScheduleView(e) {
  const threadIds = fetchCandidateThreads('all');
  const analysisResults = analyzeThreadsWithCache(threadIds);
  
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .updateCard(createTaskScheduleCard(analysisResults)))
    .build();
}
