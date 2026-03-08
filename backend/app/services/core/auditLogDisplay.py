# app/display/audit_display.py
from datetime import datetime
from typing import List, Dict, Any

from models.Audit import AuditLog
from models.Sessions import SessionLog  
import logging

logger = logging.getLogger(__name__)

class AuditLogDisplay:
    """
    Helper for formatting and combining audit logs and session logs for display.
    """

    def get_combined_logs(self, limit: int = 100) -> Dict[str, Any]:
        """
        Fetch both audit logs and session logs, combine, format, and return.

        Args:
            limit: Maximum number of logs to return (total across both types).

        Returns:
            dict: {
                'success': bool,
                'data': list of formatted log entries,
                'total_count': total number of combined logs,
                'audit_count': count of audit logs,
                'session_count': count of session logs,
                'error': str (if success=False)
            }
        """
        try:
            # Fetch audit logs (most recent first)
            audit_logs = list(AuditLog.scan(limit=limit))
            # For audit logs, we may want to sort by timestamp descending already
            audit_logs.sort(key=lambda x: x.timestamp if x.timestamp else datetime.min, reverse=True)

            # Fetch session logs (most recent first)
            session_logs = list(SessionLog.scan(limit=limit))
            session_logs.sort(key=lambda x: x.login_time if x.login_time else datetime.min, reverse=True)

            all_logs = []  # will hold formatted dicts

            # Format audit logs
            for log in audit_logs:
                formatted = self._format_audit_log(log)
                all_logs.append(formatted)

            # Format session logs
            for log in session_logs:
                formatted = self._format_session_log(log)
                all_logs.append(formatted)

            # Sort combined logs by timestamp descending (newest first)
            all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            # Apply limit after sorting
            limited_logs = all_logs[:limit]

            # Assign sequential IDs: AUD-xxxx for audit, SES-xxxx for session
            # We'll number them starting from the total count downwards (like the original)
            audit_counter = sum(1 for log in limited_logs if log['log_source'] == 'audit')
            session_counter = sum(1 for log in limited_logs if log['log_source'] == 'session')

            for log in limited_logs:
                if log['log_source'] == 'audit':
                    log['log_id'] = f"AUD-{audit_counter:04d}"
                    audit_counter -= 1
                else:
                    log['log_id'] = f"SES-{session_counter:04d}"
                    session_counter -= 1

            return {
                'success': True,
                'data': limited_logs,
                'total_count': len(all_logs),
                'audit_count': len(audit_logs),
                'session_count': len(session_logs)
            }

        except Exception as e:
            logger.error(f"Error getting combined logs: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'data': []
            }

    def _format_audit_log(self, log: AuditLog) -> Dict[str, Any]:
        """Convert an AuditLog instance to a display dict."""
        data = log.to_dict()  # AuditLog.to_dict() provides a dict with expected keys
        return {
            'user_id': data.get('username', 'Unknown'),
            'ref_id': data.get('audit_id', '')[:12],
            'event_type': data.get('action', '').replace('_', ' ').title(),
            'amount_qty': self._format_amount_qty(data),
            'status': data.get('status', 'Unknown').title(),
            'timestamp': data.get('timestamp', ''),
            'remarks': self._format_remarks(data),
            'log_source': 'audit'
        }

    def _format_session_log(self, log: SessionLog) -> Dict[str, Any]:
        """Convert a SessionLog instance to a display dict."""
        data = log.to_dict()  # SessionLog.to_dict() provides a dict with expected keys
        return {
            'user_id': data.get('username', 'Unknown'),
            'ref_id': data.get('session_id', '')[:12],
            'event_type': 'Session',
            'amount_qty': data.get('duration_human', 'N/A'),
            'status': data.get('status', 'Unknown').title(),
            'timestamp': data.get('login_time', ''),
            'remarks': f"Branch {data.get('branch_id', 'N/A')}",
            'log_source': 'session'
        }

    def _format_amount_qty(self, data: Dict[str, Any]) -> str:
        """Format amount/quantity based on audit event type."""
        event = data.get('action', '')
        metadata = data.get('metadata', {})
        if 'stock_update' in event:
            diff = metadata.get('difference', 0)
            return f"{'+' if diff > 0 else ''}{diff} units"
        elif 'delete' in event:
            count = metadata.get('count', 1)
            return f"{count} record{'s' if count != 1 else ''}"
        elif 'create' in event:
            return "1 record"
        elif 'export' in event:
            count = metadata.get('record_count', 0)
            return f"{count} records"
        elif 'import' in event:
            success = metadata.get('success_count', 0)
            total = metadata.get('total_count', 0)
            return f"{success}/{total} records"
        return "N/A"

    def _format_remarks(self, data: Dict[str, Any]) -> str:
        """Format remarks based on audit event data."""
        target_type = data.get('target_type', 'System')
        target_name = data.get('target_name', 'N/A')
        if target_type and target_name and target_name != 'N/A':
            return f"{target_type.title()}: {target_name}"
        if data.get('action') == 'login_failed':
            reason = data.get('metadata', {}).get('reason', 'Unknown')
            return f"Failed: {reason}"
        return f"Branch {data.get('branch_id', 'N/A')}"