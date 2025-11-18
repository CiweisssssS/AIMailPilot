/**
 * HTML sanitization and image URL processing utilities
 */
import DOMPurify from 'dompurify';
import { apiUrl } from './api';
import { ENDPOINTS } from './endpoints';

/**
 * Replace CID references in HTML with actual download URLs
 * @param html - HTML content with cid: references
 * @param inlineImages - Mapping of CID (without < >) to download_url
 * @returns HTML with cid: replaced by actual URLs
 */
export function replaceCidImages(html: string, inlineImages: Record<string, string> = {}): string {
  if (!html) return html;
  
  // Replace src="cid:xxxx" with the actual download URL
  return html.replace(/src=["']cid:([^"']+)["']/gi, (match, cid) => {
    const cleanCid = cid.trim();
    const downloadUrl = inlineImages[cleanCid];
    if (downloadUrl) {
      // Convert relative URL to absolute using API_BASE
      const absoluteUrl = apiUrl(downloadUrl);
      return `src="${absoluteUrl}"`;
    }
    // If no mapping found, return original (will show broken image)
    return match;
  });
}

/**
 * Replace external image URLs with proxy endpoint
 * @param html - HTML content with external image URLs
 * @returns HTML with external images proxied through backend
 */
export function proxyExternalImages(html: string): string {
  if (!html) return html;
  
  // Match img src attributes with http/https URLs (but not data: URLs or already proxied)
  return html.replace(/<img([^>]*)\ssrc=["'](https?:\/\/[^"']+)["']([^>]*)>/gi, (match, before, url, after) => {
    // Skip if already proxied or is data URL
    if (url.includes('/api/proxy-image') || url.startsWith('data:')) {
      return match;
    }
    // Encode URL for proxy endpoint
    const proxyUrl = apiUrl(`/api/proxy-image?url=${encodeURIComponent(url)}`);
    return `<img${before} src="${proxyUrl}"${after}>`;
  });
}

/**
 * Sanitize HTML content using DOMPurify
 * @param html - Raw HTML content
 * @returns Sanitized HTML safe for rendering
 */
export function sanitizeHtml(html: string): string {
  if (!html) return '';
  
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'u', 's', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'a', 'img', 'div', 'span',
      'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr'
    ],
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title', 'class', 'style', 'width', 'height',
      'align', 'colspan', 'rowspan'
    ],
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|data):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
    KEEP_CONTENT: true,
    ADD_ATTR: ['target'], // Allow target attribute for links
  });
}

/**
 * Process HTML for safe rendering: replace CID images, proxy external images, sanitize
 * @param html - Raw HTML content
 * @param inlineImages - Mapping of CID to download URLs
 * @returns Processed and sanitized HTML
 */
export function processEmailHtml(html: string, inlineImages: Record<string, string> = {}): string {
  if (!html) return '';
  
  // Step 1: Replace CID images
  let processed = replaceCidImages(html, inlineImages);
  
  // Step 2: Proxy external images
  processed = proxyExternalImages(processed);
  
  // Step 3: Sanitize
  processed = sanitizeHtml(processed);
  
  return processed;
}

/**
 * Convert plain text to HTML (simple line breaks)
 * @param text - Plain text content
 * @returns HTML with line breaks converted to <br>
 */
export function textToHtml(text: string): string {
  if (!text) return '';
  
  // Escape HTML entities
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
  
  // Convert line breaks to <br>
  return escaped.replace(/\n/g, '<br>');
}

