/**
 * Layer 5 - Flagged Mail Card
 * Shows all flagged emails with tags
 */

/**
 * Create Flagged Mail Card
 */
function createFlaggedMailCard() {
  const card = CardService.newCardBuilder();
  
  // Header
  card.setHeader(CardService.newCardHeader()
    .setTitle('🚩 Flagged Mails')
    .setSubtitle('Your important emails'));
  
  // Get flagged mails
  const flaggedMails = getFlaggedMails();
  
  if (flaggedMails.length === 0) {
    card.addSection(CardService.newCardSection()
      .addWidget(CardService.newTextParagraph()
        .setText('No flagged emails yet.\n\nFlag important emails to keep track of them here.')));
  } else {
    // Total count
    const countSection = CardService.newCardSection();
    countSection.addWidget(CardService.newTextParagraph()
      .setText(`<b>Total: ${flaggedMails.length} flagged emails</b>`));
    card.addSection(countSection);
    
    // Show flagged mails
    flaggedMails.forEach(mail => {
      const mailSection = CardService.newCardSection();
      
      // Subject
      mailSection.addWidget(CardService.newTextParagraph()
        .setText(`<b>${mail.subject}</b>`));
      
      // Tags
      if (mail.tags && mail.tags.length > 0) {
        mailSection.addWidget(CardService.newTextParagraph()
          .setText(`Tags: ${mail.tags.join(', ')}`));
      }
      
      // Flagged time
      const flaggedTime = new Date(mail.flaggedAt).toLocaleDateString();
      mailSection.addWidget(CardService.newTextParagraph()
        .setText(`<i>Flagged: ${flaggedTime}</i>`));
      
      // Actions
      mailSection.addWidget(CardService.newButtonSet()
        .addButton(CardService.newTextButton()
          .setText('Open')
          .setOpenLink(CardService.newOpenLink()
            .setUrl(`https://mail.google.com/mail/u/0/#inbox/${mail.threadId}`)))
        .addButton(CardService.newTextButton()
          .setText('Unflag')
          .setOnClickAction(CardService.newAction()
            .setFunctionName('onUnflagMail')
            .setParameters({threadId: mail.threadId}))));
      
      card.addSection(mailSection);
    });
  }
  
  // Back button
  const navSection = CardService.newCardSection();
  navSection.addWidget(CardService.newTextButton()
    .setText('← Back to Inbox')
    .setOnClickAction(CardService.newAction()
      .setFunctionName('backToInbox')));
  card.addSection(navSection);
  
  return card.build();
}

/**
 * Navigate back to inbox
 */
function backToInbox(e) {
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .popCard())
    .build();
}
