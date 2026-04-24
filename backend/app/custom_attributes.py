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
        Deserialize datetime string, fixing any year corruption.
        Handles: full ISO with T, date-only, and leading-zero corruption (e.g. 0000...2025-12-26).
        """
        if not value:
            return None

        try:
            if isinstance(value, datetime):
                return value

            if not isinstance(value, str):
                return super().deserialize(value)

            s = value.strip()

            # Corrupted: leading zeros before a 4-digit year (e.g. 0000000000000000000002025-12-26 or 000002025-09-30T...)
            if re.match(r'^0+\d{4}', s):
                # Date-only: 0*YYYY-MM-DD
                match = re.search(r'0*(\d{4}-\d{2}-\d{2})(?:T|$)', s)
                if match:
                    date_part = match.group(1)
                    try:
                        return datetime.strptime(date_part, '%Y-%m-%d').replace(tzinfo=None)
                    except ValueError:
                        pass
                # DateTime: 0*YYYY-MM-DDTHH:MM:SS...
                match = re.search(r'0*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)', s)
                if match:
                    fixed_value = match.group(1)
                    try:
                        if '.' in fixed_value:
                            return datetime.strptime(fixed_value[:26], '%Y-%m-%dT%H:%M:%S.%f')
                        return datetime.strptime(fixed_value, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

            # Normal ISO with timezone
            if '+0000' in s or 'Z' in s:
                try:
                    clean = s.replace('+0000', '').replace('Z', '')
                    return datetime.strptime(clean[:26], '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    try:
                        return datetime.strptime(clean[:19], '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        pass

            # ISO with microseconds
            try:
                return datetime.strptime(s[:26], '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                pass
            try:
                return datetime.strptime(s[:19], '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                pass

            # Date-only (no leading zeros)
            try:
                return datetime.strptime(s[:10], '%Y-%m-%d').replace(tzinfo=None)
            except ValueError:
                pass

            return super().deserialize(value)

        except Exception as e:
            logger.debug("Datetime parsing fallback for %r: %s", s[:50] if isinstance(value, str) else value, e)
            return datetime.utcnow()
