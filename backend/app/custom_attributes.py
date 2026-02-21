"""
Custom PynamoDB attributes with bug fixes
"""
from pynamodb.attributes import UTCDateTimeAttribute as BaseUTCDateTimeAttribute
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class FixedUTCDateTimeAttribute(BaseUTCDateTimeAttribute):
    """
    Fixed version of UTCDateTimeAttribute that handles corrupted deserialization
    
    This fixes a bug where PynamoDB sometimes prepends extra zeros to the year
    during deserialization (e.g., '000002025' instead of '2025')
    """
    
    def deserialize(self, value):
        """
        Deserialize datetime string, fixing any year corruption
        """
        if not value:
            return None
        
        try:
            # Check if year has extra leading zeros
            if isinstance(value, str) and re.match(r'^0+\d{4,}', value):
                # Extract the correct date by removing leading zeros from year
                # Pattern: 000002025-09-30... -> 2025-09-30...
                match = re.search(r'0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)', value)
                if match:
                    fixed_value = match.group(1)
                    value = fixed_value
            
            # Parse the datetime string directly instead of calling parent
            # PynamoDB expects ISO format: YYYY-MM-DDTHH:MM:SS.ffffff
            if isinstance(value, str):
                # Try parsing with microseconds and timezone
                try:
                    # Handle format with timezone: 2026-02-21T12:02:48.435277+0000
                    if '+0000' in value or 'Z' in value:
                        value_clean = value.replace('+0000', '').replace('Z', '')
                        return datetime.strptime(value_clean, '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    pass
                
                # Try parsing with microseconds
                try:
                    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    pass
                
                # Try without microseconds
                try:
                    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    pass
            
            # If it's already a datetime object, return as-is
            if isinstance(value, datetime):
                return value
            
            # Fallback to parent method for other cases
            return super().deserialize(value)
            
        except Exception as e:
            logger.debug(f"Datetime parsing fallback for '{value[:40]}': {e}")
            return datetime.utcnow()
