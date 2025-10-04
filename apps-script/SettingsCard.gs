/**
 * Layer 4 - Settings card for managing personalized keywords
 */

function showSettingsCard(e) {
  return showKeywordSettings(e);
}

function showKeywordSettings(e) {
  const card = buildKeywordSettingsCard();
  
  // Wrap in ActionResponse for onClick handlers
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .pushCard(card))
    .build();
}

/**
 * Build keyword settings card
 */
function buildKeywordSettingsCard() {
  const keywords = getUserKeywords();
  
  const card = CardService.newCardBuilder()
    .setHeader(CardService.newCardHeader()
      .setTitle('⚙️ Keyword Settings')
      .setSubtitle('Customize priority keywords'));
  
  // Current keywords section
  const currentSection = CardService.newCardSection()
    .setHeader('Current Keywords');
  
  if (keywords.length > 0) {
    keywords.forEach(function(keyword, index) {
      const weight = keyword.weight || 'Medium';
      currentSection.addWidget(CardService.newTextParagraph()
        .setText(`<b>${keyword.term}</b> • ${weight} • ${keyword.scope}`));
      
      // Delete button for each keyword
      currentSection.addWidget(CardService.newTextButton()
        .setText('Delete')
        .setOnClickAction(CardService.newAction()
          .setFunctionName('handleDeleteKeyword')
          .setParameters({term: keyword.term})));
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
      .setHint('e.g., urgent, deadline, recruiting'))
    .addWidget(CardService.newSelectionInput()
      .setFieldName('keyword_weight')
      .setTitle('Priority Weight')
      .setType(CardService.SelectionInputType.DROPDOWN)
      .addItem('High', 'High', false)
      .addItem('Medium', 'Medium', true)
      .addItem('Low', 'Low', false))
    .addWidget(CardService.newSelectionInput()
      .setFieldName('keyword_scope')
      .setTitle('Search In')
      .setType(CardService.SelectionInputType.DROPDOWN)
      .addItem('Subject only', 'subject', true)
      .addItem('Body only', 'body', false)
      .addItem('Subject or Body', 'subject|body', false)
      .addItem('Everywhere', 'subject|body|sender', false));
  
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
  
  return card.build();
}

/**
 * Handle add keyword
 */
function handleAddKeyword(e) {
  const term = e.formInput.keyword_term;
  const weight = e.formInput.keyword_weight || 'Medium';
  const scope = e.formInput.keyword_scope || 'subject|body';
  
  if (!term || term.trim() === '') {
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('Please enter a keyword'))
      .build();
  }
  
  // Add keyword using StateManager
  addKeyword(term.trim(), weight, scope);
  
  // Update backend
  updateUserSettings([{
    term: term.trim(),
    weight: weight,
    scope: scope
  }], []);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('✅ Keyword added: ' + term))
    .setNavigation(CardService.newNavigation().updateCard(
      buildKeywordSettingsCard()))
    .build();
}

/**
 * Handle delete keyword
 */
function handleDeleteKeyword(e) {
  const term = e.parameters.term;
  
  // Remove keyword using StateManager
  removeKeyword(term);
  
  // Update backend
  updateUserSettings([], [term]);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('🗑️ Keyword deleted: ' + term))
    .setNavigation(CardService.newNavigation().updateCard(
      buildKeywordSettingsCard()))
    .build();
}

/**
 * Handle clear all keywords
 */
function handleClearKeywords(e) {
  const keywords = getUserKeywords();
  const terms = keywords.map(kw => kw.term);
  
  // Clear locally using StateManager
  setUserKeywords([]);
  
  // Update backend
  updateUserSettings([], terms);
  
  return CardService.newActionResponseBuilder()
    .setNotification(CardService.newNotification()
      .setText('🗑️ All keywords cleared'))
    .setNavigation(CardService.newNavigation().updateCard(
      buildKeywordSettingsCard()))
    .build();
}
