#!/usr/bin/env python3
"""Fix notification service by removing queue-related code."""

import re
from pathlib import Path

def fix_notification_service():
    """Remove queue-related code from notification service."""
    
    notification_file = Path("/Users/lgee258/Desktop/LuckyGas-v3/backend/app/services/notification_service.py")
    
    content = notification_file.read_text()
    
    # Remove QueuePriority parameter from function signatures
    content = re.sub(
        r',\s*priority:\s*QueuePriority\s*=\s*QueuePriority\.[A-Z]+',
        '',
        content
    )
    
    # Remove use_queue parameter with default value
    content = re.sub(
        r',\s*use_queue:\s*bool\s*=\s*(?:True|False)',
        '',
        content
    )
    
    # Replace the send_notification method to remove queue logic
    # Find and replace the entire if use_queue block with direct sending
    content = re.sub(
        r'if use_queue:\s*\n(?:\s*#[^\n]*\n)*\s*message_id = await message_queue\.enqueue\([^)]+\)\s*\n\s*return[^\n]+\n',
        '',
        content,
        flags=re.MULTILINE | re.DOTALL
    )
    
    # Remove the fallback to queue on direct send failure
    content = re.sub(
        r'#\s*Fallback to queue on direct send failure\s*\n\s*if not use_queue:\s*\n(?:\s*[^\n]+\n)*?\s*use_queue=True,\s*\n\s*\)',
        '# Direct send failed\n            raise',
        content,
        flags=re.MULTILINE
    )
    
    # Remove priority=QueuePriority.HIGH references
    content = re.sub(
        r',\s*priority=QueuePriority\.[A-Z]+',
        '',
        content
    )
    
    # Write the fixed content
    notification_file.write_text(content)
    print(f"Fixed notification service: {notification_file}")

if __name__ == "__main__":
    fix_notification_service()