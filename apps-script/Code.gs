/**
 * Gmail Add-on Entry Point
 * This file contains the main triggers and entry points for the Gmail Add-on
 */

/**
 * Homepage trigger - shown when no message is selected
 */
function onHomepage(e) {
  return createWelcomeCard();
}

/**
 * Context trigger - shown when a message is selected
 */
function onGmailMessageSelected(e) {
  const messageId = e.gmail.messageId;
  const accessToken = e.gmail.accessToken;
  
  try {
    // Fetch the email thread
    const messages = getEmailThread(messageId, accessToken);
    
    if (!messages || messages.length === 0) {
      return createErrorCard('Failed to load email thread');
    }
    
    // Get user's keywords from properties
    const keywords = getUserKeywords();
    
    // Process thread through backend
    const result = processThread(messages, keywords);
    
    if (!result) {
      return createErrorCard('Failed to process email thread. Check backend connection.');
    }
    
    // Create and return the sidebar card
    return createSidebarCard(result);
    
  } catch (error) {
    console.error('Error in onGmailMessageSelected:', error);
    return createErrorCard('Error: ' + error.message);
  }
}

/**
 * Welcome card shown on homepage
 */
function createWelcomeCard() {
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('AI Email Assistant')
      .setSubtitle('Select an email to analyze'))
    .addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph()
        .setText('Open any email to see:<br>• AI Summary<br>• Priority Score<br>• Extracted Tasks<br>• Timeline')))
    .build();
  
  return [card];
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

/**
 * Get user's personalized keywords from properties
 */
function getUserKeywords() {
  const userProperties = PropertiesService.getUserProperties();
  const keywordsJson = userProperties.getProperty('keywords');
  
  if (keywordsJson) {
    return JSON.parse(keywordsJson);
  }
  
  return [];
}

/**
 * Save user's keywords to properties
 */
function saveUserKeywords(keywords) {
  const userProperties = PropertiesService.getUserProperties();
  userProperties.setProperty('keywords', JSON.stringify(keywords));
}
