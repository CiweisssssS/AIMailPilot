import { describe, it, expect } from 'vitest';
import { limitWords, countWords } from '../text-utils';

describe('limitWords', () => {
  it('should return text as-is when under limit', () => {
    expect(limitWords('Hello world', 10)).toBe('Hello world');
    expect(limitWords('One two three', 3)).toBe('One two three');
  });

  it('should return text as-is when exactly at limit', () => {
    expect(limitWords('One two three', 3)).toBe('One two three');
    expect(limitWords('Hello world this is a test', 6)).toBe('Hello world this is a test');
  });

  it('should truncate and add ellipsis when over limit', () => {
    expect(limitWords('One two three four five', 3)).toBe('One two three…');
    expect(limitWords('Hello world this is a test', 3)).toBe('Hello world this…');
  });

  it('should never break in the middle of a word', () => {
    const result = limitWords('Hello world this is a test', 3);
    expect(result).toBe('Hello world this…');
    expect(result).not.toContain('th');
    expect(result.split('…')[0].trim().split(/\s+/).length).toBe(3);
  });

  it('should handle text with multiple spaces correctly', () => {
    expect(limitWords('Hello  world   this    is', 3)).toBe('Hello world this…');
  });

  it('should handle punctuation correctly', () => {
    expect(limitWords('Hello, world! This is a test.', 3)).toBe('Hello, world! This…');
    expect(limitWords('Rebecca needs you to review the deck.', 5)).toBe('Rebecca needs you to review…');
  });

  it('should handle empty string', () => {
    expect(limitWords('', 10)).toBe('');
  });

  it('should handle whitespace-only string', () => {
    expect(limitWords('   ', 10)).toBe('   ');
  });

  it('should respect custom word limits', () => {
    const text = 'One two three four five six seven eight nine ten';
    expect(limitWords(text, 5)).toBe('One two three four five…');
    expect(limitWords(text, 10)).toBe(text);
    expect(limitWords(text, 3)).toBe('One two three…');
  });

  it('should handle real email summaries', () => {
    const summary = 'Rebecca needs you to review the updated pitch deck and share your feedback by EOD.';
    expect(limitWords(summary, 20)).toBe(summary); // Under limit
    expect(limitWords(summary, 10)).toBe('Rebecca needs you to review the updated pitch deck and…');
    expect(limitWords(summary, 5)).toBe('Rebecca needs you to review…');
  });

  it('should handle single word', () => {
    expect(limitWords('Hello', 1)).toBe('Hello');
    expect(limitWords('Hello', 0)).toBe('…');
  });
});

describe('countWords', () => {
  it('should count words correctly', () => {
    expect(countWords('Hello world')).toBe(2);
    expect(countWords('One two three four five')).toBe(5);
  });

  it('should handle empty string', () => {
    expect(countWords('')).toBe(0);
  });

  it('should handle whitespace-only string', () => {
    expect(countWords('   ')).toBe(0);
  });

  it('should handle multiple spaces', () => {
    expect(countWords('Hello  world   this')).toBe(3);
  });

  it('should handle punctuation', () => {
    expect(countWords('Hello, world! This is a test.')).toBe(6);
  });
});
