/**
 * Text utility functions for word-based text manipulation
 */

/**
 * Limit text to a maximum number of words with ellipsis
 * Never breaks in the middle of a word - only adds ellipsis on word boundaries
 * 
 * @param text - The text to limit
 * @param maxWords - Maximum number of words (default: 20)
 * @returns Limited text with ellipsis if truncated, otherwise original text
 * 
 * @example
 * limitWords("Hello world this is a test", 3) // "Hello world this…"
 * limitWords("Short text", 10) // "Short text"
 * limitWords("One two three", 3) // "One two three"
 */
export function limitWords(text: string, maxWords: number = 20): string {
  if (!text || text.trim() === "") {
    return text;
  }

  // Split by whitespace
  const words = text.trim().split(/\s+/);

  // If within limit, return as-is
  if (words.length <= maxWords) {
    return text;
  }

  // Take first maxWords and add ellipsis
  const limited = words.slice(0, maxWords).join(" ");
  return `${limited}…`;
}

/**
 * Count words in text
 * 
 * @param text - The text to count words in
 * @returns Number of words
 */
export function countWords(text: string): number {
  if (!text || text.trim() === "") {
    return 0;
  }
  return text.trim().split(/\s+/).length;
}
