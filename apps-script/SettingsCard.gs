/**
 * Settings card for managing personalized keywords
 */

function showSettingsCard(e) {
  const keywords = getUserKeywords();
  
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('Keyword Settings')
      .setSubtitle('Manage priority keywords'));
  
  // Current keywords section
  const currentSection = CardService.newCardSection()
    .setHeader('Current Keywords');
  
  if (keywords.length > 0) {
    keywords.forEach(function(keyword) {
      currentSection.addWidget(CardService.newTextParagraph()
        .setText(`<b>${keyword.term}</b> (weight: ${keyword.weight}, scope: ${keyword.scope})`));
    });
  } else {
    currentSection.addWidget(CardService.newTextParagraph()
      .setText('<i>No keywords configured</i>'));
  }
  
  card.addSection(currentSection);
  
  // Add keyword section
  const addSection = CardService.newCardSection()
    .setHeader('Add New Keyword')
    .addWidget(CardService.newTextInput()
      .setFieldName('keyword_term')
      .setTitle('Keyword')
      .setHint('e.g., urgent, deadline'))
    .addWidget(CardService.newTextInput()
      .setFieldName('keyword_weight')
      .setTitle('Weight')
      .setValue('1.5')
      .setHint('Higher = more important'))
    .addWidget(CardService.newSelectionInput()
      .setFieldName('keyword_scope')
      .setTitle('Scope')
      .setType(CardService.SelectionInputType.DROPDOWN)
      .addItem('Subject only', 'subject', true)
      .addItem('Body only', 'body', false)
      .addItem('Subject or Body', 'subject|body', false));
  
  const addAction = CardService.newAction()
    .setFunctionName('handleAddKeyword');
  
  addSection.addWidget(CardService.newTextButton()
    .setText('Add Keyword')
    .setOnClickAction(addAction)
    .setTextButtonStyle(CardService.TextButtonStyle.FILLED));
  
  card.addSection(addSection);
  
  // Clear all button
  if (keywords.length > 0) {
    const clearAction = CardService.newAction()
      .setFunctionName('handleClearKeywords');
    
    card.addSection(CardService.newCardSection()
      .addWidget(CardService.newTextButton()
        .setText('Clear All Keywords')
        .setOnClickAction(clearAction)));
  }
  
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
 * Handle add keyword
 */
function handleAddKeyword(e) {
  const term = e.formInput.keyword_term;
  const weight = parseFloat(e.formInput.keyword_weight || '1.5');
  const scope = e.formInput.keyword_scope || 'subject|body';
  
  if (!term || term.trim() === '') {
    return createNotification('Please enter a keyword');
  }
  
  const keywords = getUserKeywords();
  
  // Add new keyword
  keywords.push({
    term: term.trim(),
    weight: weight,
    scope: scope
  });
  
  // Save locally
  saveUserKeywords(keywords);
  
  // Update backend
  updateUserSettings([{
    term: term.trim(),
    weight: weight,
    scope: scope
  }], []);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('Keyword added: ' + term))
    .setNavigation(CardService.newNavigation().updateCard(
      showSettingsCard(e).card()))
    .build();
}

/**
 * Handle clear all keywords
 */
function handleClearKeywords(e) {
  const keywords = getUserKeywords();
  
  // Clear locally
  saveUserKeywords([]);
  
  // Update backend
  updateUserSettings([], keywords);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('All keywords cleared'))
    .setNavigation(CardService.newNavigation().updateCard(
      showSettingsCard(e).card()))
    .build();
}
