/**
 * Gmail Add-on Entry Point
 * This file contains the main triggers and entry points for the Gmail Add-on
 */

/**
 * Homepage trigger - shown when sidebar opens
 * Implements inbox-level analysis with delta fetch + unresolved pool
 */
function onHomepage(e) {
  try {
    // Fetch candidate threads using delta + unresolved pool strategy
    const threadIds = fetchCandidateThreads('all');
    
    if (threadIds.length === 0) {
      return [createEmptyInboxCard()];
    }
    
    // Analyze threads with caching
    const analysisResults = analyzeThreadsWithCache(threadIds);
    
    // Create and return inbox reminder card (Layer 1 default view)
    return [createInboxReminderCard(analysisResults, 'all')];
    
  } catch (error) {
    console.error('Error in onHomepage:', error);
    return [createErrorCard('Error loading inbox: ' + error.message)];
  }
}

/**
 * Empty inbox card
 */
function createEmptyInboxCard() {
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('📬 Inbox Reminder')
      .setSubtitle('All caught up!'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph()
        .setText('No emails to analyze. Great job staying on top of things! 🎉')))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newButtonSet()
        .addButton(CardService.newTextButton()
          .setText('🔄 Refresh')
          .setOnClickAction(CardService.newAction()
            .setFunctionName('refreshInbox')))
        .addButton(CardService.newTextButton()
          .setText('⚙️ Settings')
          .setOnClickAction(CardService.newAction()
            .setFunctionName('showKeywordSettings')))))
    .build();
  
  return card;
}

/**
 * Error card
 */
function createErrorCard(message) {
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('Error'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph()
        .setText(message)))
    .build();
  
  return [card];
}

/**
 * Get email thread using Gmail API
 */
function getEmailThread(messageId, accessToken) {
  GmailApp.setCurrentMessageAccessToken(accessToken);
  const message = GmailApp.getMessageById(messageId);
  const thread = message.getThread();
  const threadMessages = thread.getMessages();
  
  const messages = [];
  
  for (let i = 0; i < threadMessages.length; i++) {
    const msg = threadMessages[i];
    
    messages.push({
      id: msg.getId(),
      thread_id: thread.getId(),
      date: msg.getDate().toISOString(),
      from: msg.getFrom(),
      to: [msg.getTo()],
      cc: msg.getCc() ? [msg.getCc()] : [],
      subject: msg.getSubject(),
      body: msg.getPlainBody()
    });
  }
  
  return messages;
}

