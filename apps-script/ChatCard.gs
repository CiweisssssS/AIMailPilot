/**
 * Chat/QA interface card
 */

function showChatCard(e) {
  const thread = JSON.parse(e.parameters.thread);
  
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('Ask Questions')
      .setSubtitle('Chat about this email thread'));
  
  // Question input
  const section = CardService.newCardSection()
    .addWidget(CardService.newTextInput()
      .setFieldName('question')
      .setTitle('Your Question')
      .setHint('e.g., What do I need to deliver?'));
  
  // Submit button
  const submitAction = CardService.newAction()
    .setFunctionName('handleQuestionSubmit')
    .setParameters({thread: JSON.stringify(thread)});
  
  section.addWidget(CardService.newTextButton()
    .setText('Ask')
    .setOnClickAction(submitAction)
    .setTextButtonStyle(CardService.TextButtonStyle.FILLED));
  
  card.addSection(section);
  
  // Back button
  const backAction = CardService.newAction()
    .setFunctionName('goBackToMain');
  
  card.setFixedFooter(CardService.newFixedFooter()
    .setPrimaryButton(CardService.newTextButton()
      .setText('← Back')
      .setOnClickAction(backAction)));
  
  return CardService.newNavigation().pushCard(card.build());
}

/**
 * Handle question submission
 */
function handleQuestionSubmit(e) {
  const question = e.formInput.question;
  const thread = JSON.parse(e.parameters.thread);
  
  if (!question || question.trim() === '') {
    return createNotification('Please enter a question');
  }
  
  // Call backend
  const result = askQuestion(question, thread);
  
  if (!result) {
    return createNotification('Failed to get answer. Check backend connection.');
  }
  
  // Create result card
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('Answer')
      .setSubtitle('Q: ' + truncateText(question, 40)));
  
  const section = CardService.newCardSection()
    .addWidget(CardService.newTextParagraph()
      .setText('<b>Answer:</b><br>' + result.answer));
  
  if (result.sources && result.sources.length > 0) {
    section.addWidget(CardService.newTextParagraph()
      .setText('<br><b>Sources:</b> ' + result.sources.join(', ')));
  }
  
  card.addSection(section);
  
  // Ask another question button
  const askAnotherAction = CardService.newAction()
    .setFunctionName('showChatCard')
    .setParameters({thread: JSON.stringify(thread)});
  
  section.addWidget(CardService.newTextButton()
    .setText('Ask Another Question')
    .setOnClickAction(askAnotherAction));
  
  // Back button
  const backAction = CardService.newAction()
    .setFunctionName('goBackToMain');
  
  card.setFixedFooter(CardService.newFixedFooter()
    .setPrimaryButton(CardService.newTextButton()
      .setText('← Back to Analysis')
      .setOnClickAction(backAction)));
  
  return CardService.newNavigation().pushCard(card.build());
}

/**
 * Go back to main card
 */
function goBackToMain(e) {
  return CardService.newNavigation().popToRoot();
}

/**
 * Create notification
 */
function createNotification(message) {
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText(message))
    .build();
}
