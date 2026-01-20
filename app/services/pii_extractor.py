"""
PII Extractor - Extract customer PII from unstructured email bodies

This module provides utilities to extract customer names and email addresses
from email message bodies, particularly useful for Google Groups emails where
the actual sender information appears in the message text.

Common patterns:
- "John Smith (john@example.com) wrote:"
- "From: Jane Doe <jane@example.com>"
- "jane.doe@example.com"
"""
import re
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def extract_email_from_text(text: str) -> Optional[str]:
    """
    Extract email address from text using regex.

    Args:
        text: Text to search for email

    Returns:
        First email address found, or None
    """
    if not text:
        return None

    # Common email regex pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)

    if match:
        return match.group(0)

    return None


def extract_name_and_email_from_google_groups(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract name and email from Google Groups message format.

    Common patterns:
    - "John Smith (john@example.com) wrote:"
    - "Jane Doe <jane@example.com> wrote:"
    - "From: John Smith (john@example.com)"

    Args:
        text: Message body text

    Returns:
        Tuple of (name, email) or (None, None)
    """
    if not text:
        return None, None

    # Pattern 1: "Name (email@domain.com) wrote:"
    pattern1 = r'([A-Z][a-zA-Z\s\.\-\']+)\s*\(([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\)\s*wrote:'
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        logger.info(f"Extracted via pattern1: name='{name}', email='{email}'")
        return name, email

    # Pattern 2: "Name <email@domain.com> wrote:"
    pattern2 = r'([A-Z][a-zA-Z\s\.\-\']+)\s*<([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})>\s*wrote:'
    match = re.search(pattern2, text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        logger.info(f"Extracted via pattern2: name='{name}', email='{email}'")
        return name, email

    # Pattern 3: "From: Name (email)"
    pattern3 = r'From:\s*([A-Z][a-zA-Z\s\.\-\']+)\s*\(([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\)'
    match = re.search(pattern3, text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        logger.info(f"Extracted via pattern3: name='{name}', email='{email}'")
        return name, email

    # Pattern 4: "From: Name <email>"
    pattern4 = r'From:\s*([A-Z][a-zA-Z\s\.\-\']+)\s*<([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})>'
    match = re.search(pattern4, text, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip()
        logger.info(f"Extracted via pattern4: name='{name}', email='{email}'")
        return name, email

    # Pattern 5: Just email in first line/paragraph
    email = extract_email_from_text(text)
    if email:
        logger.info(f"Extracted email only: '{email}'")
        return None, email

    logger.info("No PII extracted from text")
    return None, None


def extract_pii_from_message(message_body: str, message_from: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Extract PII from email message, checking both structured fields and body.

    Args:
        message_body: The email message body text
        message_from: The From field (if available)

    Returns:
        Dict with 'name' and 'email' keys
    """
    result = {
        'name': None,
        'email': None
    }

    # First try to extract from message body (Google Groups format)
    name, email = extract_name_and_email_from_google_groups(message_body)
    if email:
        result['email'] = email
        result['name'] = name
        return result

    # Fallback: try to extract from From field
    if message_from:
        # From field might be "Name <email>" or just "email"
        from_pattern = r'([A-Z][a-zA-Z\s\.\-\']+)\s*<([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})>'
        match = re.search(from_pattern, message_from, re.IGNORECASE)
        if match:
            result['name'] = match.group(1).strip()
            result['email'] = match.group(2).strip()
            logger.info(f"Extracted from From field: name='{result['name']}', email='{result['email']}'")
            return result

        # Just email in From field
        email = extract_email_from_text(message_from)
        if email:
            result['email'] = email
            logger.info(f"Extracted email from From field: '{email}'")
            return result

    return result


# Example usage and test cases
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test cases
    test_messages = [
        "Debby Stanford-Miller (debbymiller@centurylink.net) wrote:\nI ordered 4 pantographs but only received 2",
        "Molly Stevens <molly@moontowercoaching.com> wrote:\nWhere is my tracking number?",
        "From: Jane Doe (jane.doe@example.com)\n\nI have a question about my order",
        "From: John Smith <john.smith@example.com>\n\nWhen will my order ship?",
        "Hi there, I need help with my order. My email is customer@gmail.com",
    ]

    print("=" * 80)
    print("PII Extraction Test Cases")
    print("=" * 80)

    for i, msg in enumerate(test_messages, 1):
        print(f"\nTest {i}:")
        print(f"Message: {msg[:80]}...")
        result = extract_pii_from_message(msg)
        print(f"Extracted: name='{result['name']}', email='{result['email']}'")
        print("-" * 80)
