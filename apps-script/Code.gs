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
  
  return card;
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

// ==================== ACTION HANDLERS ====================

/**
 * Save a task for later
 */
function onSaveTask(e) {
  try {
    const params = e.parameters;
    const taskData = {
      threadId: params.threadId,
      title: params.title,
      deadline: params.deadline,
      owner: params.owner
    };
    
    const taskId = saveTask(taskData);
    
    const cards = onHomepage(e);
    const notification = CardService.newNotification()
      .setText('✅ Task saved for later');
    
    return CardService.newActionResponseBuilder()
      .setNotification(notification)
      .setNavigation(CardService.newNavigation()
        .updateCard(cards[0]))
      .build();
    
  } catch (error) {
    console.error('Error in onSaveTask:', error);
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('❌ Error saving task'))
      .build();
  }
}

/**
 * Flag a mail
 */
function onFlagMail(e) {
  try {
    const params = e.parameters;
    const mailData = {
      threadId: params.threadId,
      subject: params.subject,
      tags: params.tags ? JSON.parse(params.tags) : []
    };
    
    flagMail(mailData);
    
    const cards = onHomepage(e);
    const notification = CardService.newNotification()
      .setText('🚩 Mail flagged');
    
    return CardService.newActionResponseBuilder()
      .setNotification(notification)
      .setNavigation(CardService.newNavigation()
        .updateCard(cards[0]))
      .build();
    
  } catch (error) {
    console.error('Error in onFlagMail:', error);
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('❌ Error flagging mail'))
      .build();
  }
}

/**
 * Unflag a mail
 */
function onUnflagMail(e) {
  try {
    const threadId = e.parameters.threadId;
    unflagMail(threadId);
    
    const cards = onHomepage(e);
    const notification = CardService.newNotification()
      .setText('Mail unflagged');
    
    return CardService.newActionResponseBuilder()
      .setNotification(notification)
      .setNavigation(CardService.newNavigation()
        .updateCard(cards[0]))
      .build();
    
  } catch (error) {
    console.error('Error in onUnflagMail:', error);
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('❌ Error unflagging mail'))
      .build();
  }
}

/**
 * Mark thread as done (remove from unresolved pool)
 */
function onMarkAsDone(e) {
  try {
    const threadId = e.parameters.threadId;
    removeUnresolvedThreadId(threadId);
    
    const cards = onHomepage(e);
    const notification = CardService.newNotification()
      .setText('✓ Marked as done');
    
    return CardService.newActionResponseBuilder()
      .setNotification(notification)
      .setNavigation(CardService.newNavigation()
        .updateCard(cards[0]))
      .build();
    
  } catch (error) {
    console.error('Error in onMarkAsDone:', error);
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('❌ Error marking as done'))
      .build();
  }
}

/**
 * Refresh inbox - triggers new analysis
 */
function refreshInbox(e) {
  try {
    const cards = onHomepage(e);
    return CardService.newActionResponseBuilder()
      .setNavigation(CardService.newNavigation()
        .updateCard(cards[0]))
      .build();
    
  } catch (error) {
    console.error('Error in refreshInbox:', error);
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('❌ Error refreshing'))
      .build();
  }
}

