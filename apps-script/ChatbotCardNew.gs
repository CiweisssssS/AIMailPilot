/**
 * Layer 3 - Chatbot Card
 * Simple Q&A interface using already-extracted data
 */

/**
 * Show chatbot interface
 * @param {Object} e - Event object with contextKey parameter
 */
function showChatbot(e) {
  let context = null;
  
  // Get context from cache if contextKey provided
  if (e.parameters.contextKey) {
    const contextJson = getCacheService().get(e.parameters.contextKey);
    context = contextJson ? JSON.parse(contextJson) : null;
  }
  
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .pushCard(createChatbotCard(context)))
    .build();
}

/**
 * Create chatbot card
 * @param {Object} context - Optional context (category, threadIds)
 */
function createChatbotCard(context) {
  const card = CardService.newCardBuilder();
  
  card.setHeader(CardService.newCardHeader()
    .setTitle('💬 Ask Assistant')
    .setSubtitle('Get insights from your emails'));
  
  // Context info (if any)
  if (context && context.category) {
    const infoSection = CardService.newCardSection();
    infoSection.addWidget(CardService.newTextParagraph()
      .setText(`<i>Context: ${context.category}</i>`));
    card.addSection(infoSection);
  }
  
  // Quick question buttons
  const quickSection = CardService.newCardSection();
  quickSection.addWidget(CardService.newTextParagraph()
    .setText('<b>Quick Questions:</b>'));
  
  const questions = [
    'What are my top 3 urgent tasks?',
    'Summarize all emails today',
    'Any deadlines this week?',
    'Show recruiting emails'
  ];
  
  questions.forEach(question => {
    quickSection.addWidget(CardService.newTextButton()
      .setText(`"${question}"`)
      .setOnClickAction(CardService.newAction()
        .setFunctionName('answerQuestion')
        .setParameters({
          question: question,
          context: context ? JSON.stringify(context) : ''
        })));
  });
  
  card.addSection(quickSection);
  
  // Custom question input
  const inputSection = CardService.newCardSection();
  inputSection.addWidget(CardService.newTextParagraph()
    .setText('<b>Or ask your own:</b>'));
  
  inputSection.addWidget(CardService.newTextInput()
    .setFieldName('custom_question')
    .setTitle('Your question')
    .setHint('e.g., What meetings do I have tomorrow?'));
  
  inputSection.addWidget(CardService.newTextButton()
    .setText('Ask')
    .setOnClickAction(CardService.newAction()
      .setFunctionName('answerCustomQuestion')
      .setParameters({
        context: context ? JSON.stringify(context) : ''
      })));
  
  card.addSection(inputSection);
  
  return card.build();
}

/**
 * Answer a question
 */
function answerQuestion(e) {
  const question = e.parameters.question;
  const context = e.parameters.context ? JSON.parse(e.parameters.context) : null;
  
  const answer = generateAnswer(question, context);
  
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .updateCard(createAnswerCard(question, answer, context)))
    .build();
}

/**
 * Answer custom question
 */
function answerCustomQuestion(e) {
  const question = e.formInput.custom_question;
  const context = e.parameters.context ? JSON.parse(e.parameters.context) : null;
  
  if (!question || question.trim() === '') {
    return CardService.newActionResponseBuilder()
      .setNotification(CardService.newNotification()
        .setText('Please enter a question'))
      .build();
  }
  
  const answer = generateAnswer(question, context);
  
  return CardService.newActionResponseBuilder()
    .setNavigation(CardService.newNavigation()
      .updateCard(createAnswerCard(question, answer, context)))
    .build();
}

/**
 * Generate answer using backend RAG pipeline
 */
function generateAnswer(question, context) {
  try {
    // Fetch candidate threads
    let threadIds = [];
    
    if (context && context.threadIds) {
      threadIds = context.threadIds.slice(0, 10); // Limit to 10 threads
    } else {
      threadIds = fetchCandidateThreads('all').slice(0, 10);
    }
    
    if (threadIds.length === 0) {
      return 'No emails found to answer your question.';
    }
    
    // Get thread details for backend
    const threadDetails = batchGetThreadDetails(threadIds);
    
    if (threadDetails.length === 0) {
      return 'Error retrieving email details.';
    }
    
    // Call backend /api/chatbot-qa using RAG pipeline
    const result = askQuestion(question, threadDetails);
    
    if (result && result.answer) {
      return result.answer;
    } else {
      // Fallback to rule-based if backend fails
      return generateFallbackAnswer(question, threadIds);
    }
    
  } catch (error) {
    console.error('Error generating answer:', error);
    return 'Sorry, I encountered an error. Please try again.';
  }
}

/**
 * Fallback answer generation using rules
 */
function generateFallbackAnswer(question, threadIds) {
  const questionLower = question.toLowerCase();
  const analysisResults = analyzeThreadsWithCache(threadIds);
  
  if (questionLower.includes('urgent') || questionLower.includes('top')) {
    return answerUrgentTasks(analysisResults);
  } else if (questionLower.includes('deadline') || questionLower.includes('due')) {
    return answerDeadlines(analysisResults);
  } else if (questionLower.includes('meeting')) {
    return answerMeetings(analysisResults);
  } else if (questionLower.includes('summarize') || questionLower.includes('summary')) {
    return answerSummary(analysisResults);
  } else {
    return 'I can help you with:\n• Urgent tasks\n• Deadlines\n• Meetings\n• Email summaries\n\nTry asking one of the quick questions above!';
  }
}

/**
 * Answer urgent tasks question
 */
function answerUrgentTasks(analysisResults) {
  const urgentThreads = [];
  
  Object.keys(analysisResults).forEach(threadId => {
    const analysis = analysisResults[threadId];
    if (analysis.priority && analysis.priority.label === 'P1') {
      urgentThreads.push({id: threadId, analysis: analysis});
    }
  });
  
  if (urgentThreads.length === 0) {
    return 'No urgent (P1) emails found. Good job keeping up!';
  }
  
  let answer = `Found ${urgentThreads.length} urgent email(s):\n\n`;
  
  const top3 = urgentThreads.slice(0, 3);
  top3.forEach((item, index) => {
    const thread = GmailApp.getThreadById(item.id);
    const subject = thread ? thread.getFirstMessageSubject() : 'Unknown';
    answer += `${index + 1}. ${subject}\n${item.analysis.summary}\n\n`;
  });
  
  return answer;
}

/**
 * Answer deadlines question
 */
function answerDeadlines(analysisResults) {
  const deadlines = [];
  
  Object.keys(analysisResults).forEach(threadId => {
    const analysis = analysisResults[threadId];
    if (analysis.tasks) {
      analysis.tasks.forEach(task => {
        if (task.due) {
          deadlines.push({threadId: threadId, task: task});
        }
      });
    }
  });
  
  if (deadlines.length === 0) {
    return 'No upcoming deadlines found in your emails.';
  }
  
  // Sort by due date
  deadlines.sort((a, b) => new Date(a.task.due) - new Date(b.task.due));
  
  let answer = `Found ${deadlines.length} deadline(s):\n\n`;
  
  const top5 = deadlines.slice(0, 5);
  top5.forEach((item, index) => {
    const dueText = formatDueDate(item.task.due);
    answer += `${index + 1}. ${item.task.title.substring(0, 50)}\n${dueText}\n\n`;
  });
  
  return answer;
}

/**
 * Answer meetings question
 */
function answerMeetings(analysisResults) {
  const meetings = [];
  
  Object.keys(analysisResults).forEach(threadId => {
    const analysis = analysisResults[threadId];
    if (analysis.tasks) {
      analysis.tasks.forEach(task => {
        if (task.type === 'meeting' && task.due) {
          meetings.push({threadId: threadId, task: task});
        }
      });
    }
  });
  
  if (meetings.length === 0) {
    return 'No upcoming meetings found in your emails.';
  }
  
  // Sort by due date
  meetings.sort((a, b) => new Date(a.task.due) - new Date(b.task.due));
  
  let answer = `Found ${meetings.length} meeting(s):\n\n`;
  
  meetings.forEach((item, index) => {
    const dueText = formatDueDate(item.task.due);
    answer += `${index + 1}. ${item.task.title.substring(0, 50)}\n${dueText}\n\n`;
  });
  
  return answer;
}

/**
 * Answer summary question
 */
function answerSummary(analysisResults) {
  const count = Object.keys(analysisResults).length;
  
  if (count === 0) {
    return 'No emails to summarize.';
  }
  
  const categories = categorizeEmails(analysisResults);
  
  let answer = `Summary of ${count} emails:\n\n`;
  answer += `• Urgent (P1): ${categories.urgent.length}\n`;
  answer += `• To-do (P2): ${categories.todo.length}\n`;
  answer += `• FYI (P3): ${categories.fyi.length}\n`;
  
  return answer;
}

/**
 * Answer keyword filter question
 */
function answerKeywordFilter(analysisResults, keyword) {
  const filtered = filterByKeyword(analysisResults, keyword);
  
  if (filtered.length === 0) {
    return `No emails found matching "${keyword}".`;
  }
  
  let answer = `Found ${filtered.length} email(s) about "${keyword}":\n\n`;
  
  const top3 = filtered.slice(0, 3);
  top3.forEach((threadId, index) => {
    const analysis = analysisResults[threadId];
    const thread = GmailApp.getThreadById(threadId);
    const subject = thread ? thread.getFirstMessageSubject() : 'Unknown';
    answer += `${index + 1}. ${subject}\n${analysis.summary}\n\n`;
  });
  
  return answer;
}

/**
 * Create answer card
 */
function createAnswerCard(question, answer, context) {
  const card = CardService.newCardBuilder();
  
  card.setHeader(CardService.newCardHeader()
    .setTitle('💬 Answer'));
  
  // Question
  const questionSection = CardService.newCardSection();
  questionSection.addWidget(CardService.newTextParagraph()
    .setText(`<b>Q: ${question}</b>`));
  card.addSection(questionSection);
  
  // Answer
  const answerSection = CardService.newCardSection();
  answerSection.addWidget(CardService.newTextParagraph()
    .setText(answer));
  card.addSection(answerSection);
  
  // Action buttons
  const actionsSection = CardService.newCardSection();
  actionsSection.addWidget(CardService.newTextButton()
    .setText('Ask Another')
    .setOnClickAction(CardService.newAction()
      .setFunctionName('showChatbot')
      .setParameters({
        context: context ? JSON.stringify(context) : ''
      })));
  
  card.addSection(actionsSection);
  
  return card.build();
}
