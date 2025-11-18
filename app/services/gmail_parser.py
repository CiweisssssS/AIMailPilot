"""
Gmail MIME parsing and decoding utilities
"""
import base64
import quopri
import email
import email.header
import email.utils
from email.message import EmailMessage as EmailMessageType
from typing import Optional, Dict, List, Tuple
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)


def decode_mime_header(header_value: str) -> str:
    """
    Decode MIME-encoded header (e.g., =?UTF-8?B?...?= or =?UTF-8?Q?...?=)
    """
    if not header_value:
        return ""
    
    try:
        decoded_parts = email.header.decode_header(header_value)
        decoded_string = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_string += part.decode(encoding)
                else:
                    # Try common encodings
                    for enc in ['utf-8', 'latin-1', 'iso-8859-1']:
                        try:
                            decoded_string += part.decode(enc)
                            break
                        except:
                            continue
            else:
                decoded_string += part
        return decoded_string
    except Exception as e:
        logger.warning(f"Failed to decode MIME header '{header_value}': {e}")
        return header_value


def decode_html_entities(text: str) -> str:
    """
    Decode HTML entities like &#39; &amp; &lt; etc.
    """
    import html
    return html.unescape(text)


def parse_from_header(from_header: str) -> Tuple[str, str]:
    """
    Parse From header to extract name and email
    Returns: (from_name, from_email)
    """
    if not from_header:
        return ("", "")
    
    try:
        # Decode MIME header first
        decoded = decode_mime_header(from_header)
        
        # Parse using email.utils
        name, email_addr = email.utils.parseaddr(decoded)
        
        # If no name, use email local part as fallback
        if not name or name.strip() == "":
            if email_addr:
                local_part = email_addr.split("@")[0] if "@" in email_addr else email_addr
                name = local_part
            else:
                name = ""
        
        return (name.strip(), email_addr.strip())
    except Exception as e:
        logger.warning(f"Failed to parse From header '{from_header}': {e}")
        # Fallback: try to extract email
        if "@" in from_header:
            import re
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', from_header)
            if email_match:
                email_addr = email_match.group(0)
                local_part = email_addr.split("@")[0]
                return (local_part, email_addr)
        return ("", from_header)


def decode_body_part(part: EmailMessageType, charset: Optional[str] = None) -> str:
    """
    Decode a MIME part body (handles base64, quoted-printable, etc.)
    """
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    
    # Get charset from part or use default
    if not charset:
        charset = part.get_content_charset() or 'utf-8'
    
    try:
        if isinstance(payload, bytes):
            return payload.decode(charset, errors='replace')
        else:
            return str(payload)
    except Exception as e:
        logger.warning(f"Failed to decode body with charset {charset}: {e}")
        # Fallback: try utf-8
        try:
            if isinstance(payload, bytes):
                return payload.decode('utf-8', errors='replace')
            return str(payload)
        except:
            return str(payload) if payload else ""


def extract_body_from_mime(payload: Dict, access_token: str, message_id: str) -> Tuple[Optional[str], Optional[str], Dict[str, str], List[Dict]]:
    """
    Recursively extract HTML and text body from Gmail message payload
    Also extracts inline images (CID mappings) and attachments
    
    Returns: (body_html, body_text, inline_images, attachments)
    - inline_images: dict mapping CID (without < >) to download_url
    - attachments: list of attachment info dicts
    """
    body_html = None
    body_text = None
    inline_images: Dict[str, str] = {}
    attachments: List[Dict] = []
    
    def process_part(part: Dict):
        nonlocal body_html, body_text
        
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {})
        headers = part.get("headers", [])
        
        # Extract Content-ID for inline images
        content_id = None
        content_disposition = None
        for header in headers:
            name = header.get("name", "").lower()
            value = header.get("value", "")
            if name == "content-id":
                # Remove < > from CID
                content_id = value.strip("<>")
            elif name == "content-disposition":
                content_disposition = value.lower()
        
        # Check if this is an attachment
        is_attachment = content_disposition and "attachment" in content_disposition
        is_inline = content_disposition and "inline" in content_disposition
        
        # Get attachment ID if present
        attachment_id = body_data.get("attachmentId")
        filename = None
        for header in headers:
            if header.get("name", "").lower() == "content-disposition":
                # Try to extract filename
                import re
                filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', header.get("value", ""), re.IGNORECASE)
                if filename_match:
                    filename = filename_match.group(1).strip('"\'')
                    # Decode filename if needed
                    filename = decode_mime_header(filename)
        
        # Process body data
        data = body_data.get("data")
        size = body_data.get("size", 0)
        
        if mime_type == "text/html" and not body_html and data:
            # Decode base64
            try:
                # Gmail uses base64url encoding
                decoded = base64.urlsafe_b64decode(data + '==')
                body_html = decoded.decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Failed to decode HTML body: {e}")
        
        elif mime_type == "text/plain" and not body_text and data:
            # Decode base64
            try:
                decoded = base64.urlsafe_b64decode(data + '==')
                body_text = decoded.decode('utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Failed to decode text body: {e}")
        
        # Handle inline images (images with Content-ID, typically inline)
        if content_id and attachment_id and (is_inline or (mime_type.startswith("image/") and not is_attachment)):
            # Build download URL (relative path, frontend will prepend API_BASE)
            download_url = f"/api/message/{message_id}/attachment/{attachment_id}"
            inline_images[content_id] = download_url
        
        # Handle attachments (non-inline or explicitly marked as attachment)
        if attachment_id and (is_attachment or (mime_type.startswith("image/") and not is_inline and not content_id)):
            attachments.append({
                "id": attachment_id,
                "filename": filename or f"attachment_{attachment_id}",
                "mime_type": mime_type,
                "size": size,
                "content_id": content_id,
                "is_inline": is_inline,
                "download_url": f"/api/message/{message_id}/attachment/{attachment_id}"
            })
        
        # Process nested parts (multipart)
        parts = part.get("parts", [])
        for nested_part in parts:
            process_part(nested_part)
    
    # Start processing from root payload
    if isinstance(payload, dict):
        process_part(payload)
    
    return (body_html, body_text, inline_images, attachments)


def parse_gmail_message(message_data: Dict, access_token: str) -> Dict:
    """
    Parse Gmail API message response into normalized format
    Returns dict with: id, thread_id, from_name, from_email, subject, snippet, date, body_html, body_text, inline_images, attachments
    """
    message_id = message_data.get("id", "")
    thread_id = message_data.get("threadId", "")
    snippet = message_data.get("snippet", "")
    payload = message_data.get("payload", {})
    headers = payload.get("headers", [])
    
    # Extract headers
    header_dict = {h.get("name", ""): h.get("value", "") for h in headers}
    
    from_header = header_dict.get("From", "")
    subject_header = header_dict.get("Subject", "")
    date_header = header_dict.get("Date", "")
    
    # Parse From header
    from_name, from_email = parse_from_header(from_header)
    
    # Decode subject
    subject = decode_mime_header(subject_header)
    subject = decode_html_entities(subject)
    
    # Decode snippet
    snippet = decode_html_entities(snippet) if snippet else ""
    
    # Parse date (convert to ISO8601 if needed)
    date_iso = date_header  # Gmail usually returns RFC2822, we'll keep as-is for now
    
    # Extract body and attachments
    body_html, body_text, inline_images, attachments = extract_body_from_mime(payload, access_token, message_id)
    
    return {
        "id": message_id,
        "thread_id": thread_id,
        "from_name": from_name,
        "from_email": from_email,
        "subject": subject,
        "snippet": snippet,
        "date": date_iso,
        "body_html": body_html,
        "body_text": body_text,
        "inline_images": inline_images,
        "attachments": attachments
    }

