"""
Notifications Model – Single Table Design (no new GSIs)
PK = notifications#<YYYY-MM-DD>   (date‑sharded)
SK = NOTIF-#####                   (global 5‑digit sequence)
Auto‑archive on read after 90 days, auto‑delete via TTL after 120 days.
Includes optional include_archived parameter for frontend.
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, NumberAttribute,
    UTCDateTimeAttribute, JSONAttribute
)
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from datetime import datetime, timedelta, timezone, date
import logging
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)



# ============= MAIN NOTIFICATION MODEL =============
class Notification(Model):
    """
    NOTIFICATION MODEL – Automatic archiving + TTL deletion.
    
    - PK = notifications#<YYYY-MM-DD>   (date shard)
    - SK = NOTIF-#####                  (globally unique 5‑digit)
    - Lazy archive: any read that finds the item older than ARCHIVE_AFTER_DAYS
      will mark archived=True and save before returning it (unless include_archived=True).
    - TTL set to DELETE_AFTER_DAYS for automatic deletion by DynamoDB.
    """
    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        if DYNAMODB_LOCAL:
            host = DYNAMODB_LOCAL_HOST
        read_capacity_units = 10
        write_capacity_units = 20

    # Configurable thresholds
    ARCHIVE_AFTER_DAYS = 90
    DELETE_AFTER_DAYS = 120

    # Primary keys
    pk = UnicodeAttribute(hash_key=True, attr_name="PK")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")

    # Content
    title = UnicodeAttribute()
    message = UnicodeAttribute()
    priority = UnicodeAttribute()
    notification_type = UnicodeAttribute()
    action_type = UnicodeAttribute(null=True)

    # Status
    is_read = BooleanAttribute(default=False)
    archived = BooleanAttribute(default=False)

    # Timestamps
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    delivered_at = UTCDateTimeAttribute(null=True)

    # TTL for automatic deletion
    ttl = NumberAttribute(null=True, attr_name="TTL")

    # Metadata
    metadata = JSONAttribute(null=True)

    # ------------------------------------------------------------------
    # Universal template — every notification shares this exact structure
    # ------------------------------------------------------------------
    # Priority levels (use these constants, not raw strings)
    PRIORITY_CRITICAL = "critical"   # system errors, security events, zero-stock alerts
    PRIORITY_HIGH     = "high"       # low stock, order failures, time-sensitive actions
    PRIORITY_MEDIUM   = "medium"     # order updates, general inventory changes
    PRIORITY_LOW      = "low"        # informational, routine status changes

    VALID_PRIORITIES = {PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW}
    VALID_TYPES = {
        "system", "user", "order", "inventory", "promotion",
        "alert", "reminder", "security", "maintenance", "update",
        "pos",
    }

    @staticmethod
    def validate_priority(priority: str) -> bool:
        return priority in Notification.VALID_PRIORITIES

    @staticmethod
    def validate_notification_type(notification_type: str) -> bool:
        return notification_type in Notification.VALID_TYPES

    @staticmethod
    def _date_partition(dt: datetime) -> str:
        return f"notifications#{dt.strftime('%Y-%m-%d')}"

    # ------------------------------------------------------------------
    #  Core creation method
    # ------------------------------------------------------------------
    @classmethod
    def create_notification(cls, title: str, message: str,
                            notification_type: str, priority: str = "medium",
                            action_type: str = None, metadata: Dict = None,
                            delivered_at: datetime = None) -> 'Notification':
        """Create a new notification with auto‑generated SK and TTL."""
        if not cls.validate_notification_type(notification_type):
            raise ValueError(f"Invalid notification type: {notification_type}")
        if not cls.validate_priority(priority):
            raise ValueError(f"Invalid priority: {priority}")

        now = datetime.now(timezone.utc)
        partition = cls._date_partition(now)

        # SK: NOTIF-##### (globally unique)
        sk = generate_sk('NOTIF', 'notification_seq')

        # TTL: delete automatically after DELETE_AFTER_DAYS
        expiry = int((now + timedelta(days=cls.DELETE_AFTER_DAYS)).timestamp())

        notification = cls(
            pk=partition,
            sk=sk,
            title=title.strip(),
            message=message.strip(),
            notification_type=notification_type,
            priority=priority,
            action_type=action_type,
            metadata=metadata or {},
            delivered_at=delivered_at or now,
            is_read=False,
            archived=False,
            created_at=now,
            updated_at=now,
            ttl=expiry
        )
        notification.save()
        cls._write_lookup(sk, partition)
        # Optional stats update (best‑effort)
        cls._increment_stats(total=1, unread=1,
                             urgent=1 if priority in (cls.PRIORITY_HIGH, cls.PRIORITY_CRITICAL) else 0)
        logger.info(f"Notification created: {sk} - Type: {notification_type}, Priority: {priority}")
        return notification

    # ------------------------------------------------------------------
    #  Automatic archiving logic (lazy)
    # ------------------------------------------------------------------
    def _auto_archive_if_needed(self) -> None:
        """
        If the notification is older than ARCHIVE_AFTER_DAYS and not yet
        archived, mark it archived now and save.
        """
        if not self.archived and self.created_at is not None:
            age = datetime.now(timezone.utc) - self.created_at
            if age > timedelta(days=self.ARCHIVE_AFTER_DAYS):
                logger.info(f"Auto‑archiving notification {self.sk}")
                self.archive()  # will save and update stats

    # ------------------------------------------------------------------
    #  Lookup by ID (scans backwards over date partitions)
    # ------------------------------------------------------------------
    @classmethod
    def get_by_id(cls, notification_id: str, include_archived: bool = False) -> 'Notification | None':
        """
        Fetch by SK (e.g., 'NOTIF-00001').
        Scans recent date partitions backwards (up to TTL horizon).
        If include_archived is True, returns even if archived.
        Otherwise, triggers auto‑archive if old and returns None if archived.
        """
        if not notification_id.startswith('NOTIF-'):
            notification_id = f"NOTIF-{notification_id}"

        # Fast path: lookup record resolves partition in O(1), avoids scanning all date partitions
        lookup_partition = cls._get_partition_from_lookup(notification_id)
        if lookup_partition:
            try:
                result = cls.query(lookup_partition, cls.sk == notification_id, limit=1)
                for item in result:
                    if item.archived and not include_archived:
                        return None
                    if not include_archived:
                        item._auto_archive_if_needed()
                    return item
            except Exception as e:
                logger.warning(f"Error querying lookup partition {lookup_partition}: {e}")

        # Fallback: scan partitions (covers notifications created before lookup records existed)
        today = date.today()
        max_days = cls.DELETE_AFTER_DAYS + 1

        for days_ago in range(max_days):
            d = today - timedelta(days=days_ago)
            partition = cls._date_partition(
                datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
            try:
                result = cls.query(partition, cls.sk == notification_id, limit=1)
                for item in result:
                    if item.archived and not include_archived:
                        return None
                    if not include_archived:
                        item._auto_archive_if_needed()
                    return item
            except Exception as e:
                logger.warning(f"Error scanning partition {partition}: {e}")
                continue
        return None

    @classmethod
    def get_by_id_including_archived(cls, notification_id: str) -> Optional['Notification']:
        """Shortcut to retrieve a notification even if it's archived."""
        return cls.get_by_id(notification_id, include_archived=True)

    # ------------------------------------------------------------------
    #  Partition-scan queries (no GSIs — filter applied server-side per partition)
    # ------------------------------------------------------------------
    @classmethod
    def _archive_batch(cls, items: List['Notification']) -> None:
        """Lazily archive a batch of fetched items (only when include_archived=False)."""
        for item in items:
            if not item.archived:
                item._auto_archive_if_needed()

    @classmethod
    def _scan_partitions(cls, limit: int, filter_condition=None,
                         include_archived: bool = False,
                         days: int = None) -> List['Notification']:
        """Scan date partitions newest-first with an optional server-side filter condition."""
        max_days = days if days is not None else cls.DELETE_AFTER_DAYS
        today = date.today()
        items = []
        for days_ago in range(max_days + 1):
            if len(items) >= limit:
                break
            d = today - timedelta(days=days_ago)
            partition = cls._date_partition(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
            try:
                for item in cls.query(partition, scan_index_forward=False,
                                      filter_condition=filter_condition,
                                      limit=limit - len(items)):
                    if not include_archived and item.archived:
                        continue
                    items.append(item)
                    if len(items) >= limit:
                        break
            except Exception as e:
                logger.debug(f"Error querying partition {partition}: {e}")
        if not include_archived:
            cls._archive_batch(items)
        return items

    @classmethod
    def get_by_type(cls, notification_type: str,
                    limit: int = 50, last_key: dict = None,
                    include_archived: bool = False) -> Tuple[List['Notification'], Optional[dict]]:
        items = cls._scan_partitions(
            limit=limit,
            filter_condition=(cls.notification_type == notification_type),
            include_archived=include_archived
        )
        return items, None

    @classmethod
    def get_by_priority(cls, priority: str,
                        limit: int = 50, last_key: dict = None,
                        include_archived: bool = False) -> Tuple[List['Notification'], Optional[dict]]:
        items = cls._scan_partitions(
            limit=limit,
            filter_condition=(cls.priority == priority),
            include_archived=include_archived
        )
        return items, None

    @classmethod
    def get_unread_notifications(cls, limit: int = 100, last_key: dict = None,
                                 include_archived: bool = False) -> Tuple[List['Notification'], Optional[dict]]:
        items = cls._scan_partitions(
            limit=limit,
            filter_condition=(cls.is_read == False),
            include_archived=include_archived
        )
        return items, None

    @classmethod
    def get_by_action_type(cls, action_type: str,
                           limit: int = 50, last_key: dict = None,
                           include_archived: bool = False) -> Tuple[List['Notification'], Optional[dict]]:
        if not action_type:
            return [], None
        items = cls._scan_partitions(
            limit=limit,
            filter_condition=(cls.action_type == action_type),
            include_archived=include_archived
        )
        return items, None

    @classmethod
    def get_recent_notifications(cls, hours: int = 24,
                                 limit: int = 100,
                                 include_archived: bool = False) -> List['Notification']:
        """
        Get recent notifications using date partitions.
        """
        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=hours)
        items = []

        d = now.date()
        while d >= start.date():
            partition = cls._date_partition(
                datetime(d.year, d.month, d.day, tzinfo=timezone.utc))
            try:
                for item in cls.query(partition,
                                      scan_index_forward=False,
                                      limit=limit - len(items)):
                    if item.created_at >= start:
                        if not include_archived and item.archived:
                            continue
                        items.append(item)
                        if len(items) >= limit:
                            break
            except Exception as e:
                logger.debug(f"Error querying partition {partition}: {e}")
            if len(items) >= limit:
                break
            d -= timedelta(days=1)

        if not include_archived:
            cls._archive_batch(items)
        return items

    # ------------------------------------------------------------------
    #  Stats (best‑effort counter item)
    # ------------------------------------------------------------------
    @classmethod
    def _update_stats(cls, **increments):
        try:
            parts = []
            expr_attr_names = {}
            expr_attr_vals = {}
            for i, (field, delta) in enumerate(increments.items()):
                if delta == 0:
                    continue
                place = f"#f{i}"
                expr_attr_names[place] = field
                val_place = f":v{i}"
                expr_attr_vals[val_place] = delta
                parts.append(f"{place} {val_place}")
            if not parts:
                return

            conn = cls._get_connection()
            conn.update_item(
                cls.Meta.table_name,
                {"PK": "NOTIF_STATS", "SK": "COUNTS"},
                update_expression=f"ADD {', '.join(parts)}",
                expression_attribute_names=expr_attr_names,
                expression_attribute_values=expr_attr_vals
            )
        except Exception as e:
            logger.warning(f"Failed to update notification stats: {e}")

    @classmethod
    def _increment_stats(cls, total=0, unread=0, urgent=0):
        cls._update_stats(total=total, unread=unread, urgent=urgent)

    @classmethod
    def _decrement_stats(cls, total=0, unread=0, urgent=0):
        cls._update_stats(total=-total, unread=-unread, urgent=-urgent)

    @classmethod
    def _write_lookup(cls, notification_id: str, date_partition: str) -> None:
        """Write a reverse-lookup record so get_by_id avoids full partition scanning."""
        try:
            conn = cls._get_connection()
            conn.update_item(
                cls.Meta.table_name,
                {"PK": "NOTIF_LOOKUP", "SK": notification_id},
                update_expression="SET date_pk = :v",
                expression_attribute_values={":v": date_partition}
            )
        except Exception as e:
            logger.warning(f"Failed to write notification lookup: {e}")

    @classmethod
    def _get_partition_from_lookup(cls, notification_id: str) -> Optional[str]:
        """Retrieve the stored date partition for a notification ID (O(1) lookup)."""
        try:
            conn = cls._get_connection()
            response = conn.get_item(
                table_name=cls.Meta.table_name,
                key={"PK": "NOTIF_LOOKUP", "SK": notification_id},
                consistent_read=False
            )
            item = response.get("Item")
            if item:
                return item.get("date_pk")
        except Exception:
            pass
        return None

    @classmethod
    def get_unread_count(cls) -> int:
        try:
            conn = cls._get_connection()
            response = conn.get_item(
                table_name=cls.Meta.table_name,
                key={"PK": "NOTIF_STATS", "SK": "COUNTS"},
                consistent_read=False
            )
            item = response.get("Item")
            if item:
                return int(item.get("unread", 0))
        except Exception:
            pass
        # Fallback: count via partition scan
        return len(cls._scan_partitions(limit=1000, filter_condition=(cls.is_read == False)))

    @classmethod
    def mark_all_as_read(cls) -> int:
        count = 0
        while True:
            items, _ = cls.get_unread_notifications(limit=500)
            if not items:
                break
            for notif in items:
                notif.mark_as_read()
                count += 1
        return count

    # ------------------------------------------------------------------
    #  Instance methods (state changes with stats updates)
    # ------------------------------------------------------------------
    def mark_as_read(self) -> 'Notification':
        if not self.is_read:
            self.is_read = True
            self.updated_at = datetime.now(timezone.utc)
            self.save()
            self._decrement_stats(unread=1)
            logger.info(f"Notification {self.sk} marked as read")
        return self

    def mark_as_unread(self) -> 'Notification':
        if self.is_read:
            self.is_read = False
            self.updated_at = datetime.now(timezone.utc)
            self.save()
            self._increment_stats(unread=1)
            logger.info(f"Notification {self.sk} marked as unread")
        return self

    def archive(self) -> 'Notification':
        if not self.archived:
            self.archived = True
            self.updated_at = datetime.now(timezone.utc)
            self.save()
            self._decrement_stats(
                total=1,
                unread=0 if self.is_read else 1,
                urgent=1 if self.priority in (self.PRIORITY_HIGH, self.PRIORITY_CRITICAL) else 0
            )
            logger.info(f"Notification {self.sk} archived")
        return self

    def unarchive(self) -> 'Notification':
        if self.archived:
            self.archived = False
            self.updated_at = datetime.now(timezone.utc)
            self.save()
            self._increment_stats(
                total=1,
                unread=0 if self.is_read else 1,
                urgent=1 if self.priority in (self.PRIORITY_HIGH, self.PRIORITY_CRITICAL) else 0
            )
            logger.info(f"Notification {self.sk} unarchived")
        return self

    def is_urgent(self) -> bool:
        return self.priority in (self.PRIORITY_HIGH, self.PRIORITY_CRITICAL)

    def get_age_days(self) -> float:
        if not self.created_at:
            return 0.0
        delta = datetime.now(timezone.utc) - self.created_at
        return delta.days + delta.seconds / 86400.0

    def is_actionable(self) -> bool:
        return bool(self.action_type)

    def to_dict(self) -> dict:
        return {
            "notification_id": self.sk,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "notification_type": self.notification_type,
            "action_type": self.action_type,
            "is_read": self.is_read,
            "archived": self.archived,
            "is_urgent": self.is_urgent(),
            "is_actionable": self.is_actionable(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "age_days": round(self.get_age_days(), 1),
            "metadata": self.metadata or {}
        }

    def to_summary_dict(self) -> dict:
        return {
            "notification_id": self.sk,
            "title": self.title,
            "priority": self.priority,
            "notification_type": self.notification_type,
            "action_type": self.action_type,
            "is_read": self.is_read,
            "is_urgent": self.is_urgent(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "age_days": round(self.get_age_days(), 1)
        }

    def save(self, condition=None, **kwargs):
        self.updated_at = datetime.now(timezone.utc)
        return super().save(condition=condition, **kwargs)


    # ============= Convenience factories =============
    @classmethod
    def create_system_notification(cls, title: str, message: str,
                                   priority: str = "medium",
                                   metadata: Dict = None) -> 'Notification':
        return cls.create_notification(
            title=title, message=message,
            notification_type="system", priority=priority,
            action_type="system_alert", metadata=metadata)

    @classmethod
    def create_order_notification(cls, title: str, message: str,
                                  order_id: str, order_status: str,
                                  priority: str = "medium") -> 'Notification':
        metadata = {
            "event": "order_update",
            "order_id": order_id,
            "order_status": order_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return cls.create_notification(
            title=title, message=message,
            notification_type="order", priority=priority,
            action_type="view_order", metadata=metadata)

    @classmethod
    def create_inventory_notification(cls, title: str, message: str,
                                      product_id: str, batch_id: str,
                                      change_type: str,
                                      priority: str = "high") -> 'Notification':
        metadata = {
            "event": "inventory_change",
            "product_id": product_id,
            "batch_id": batch_id,
            "change_type": change_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return cls.create_notification(
            title=title, message=message,
            notification_type="inventory", priority=priority,
            action_type="update_inventory", metadata=metadata)

    @classmethod
    def create_security_notification(cls, title: str, message: str,
                                     event_type: str, ip_address: str = None,
                                     priority: str = "critical") -> 'Notification':
        metadata = {
            "event": "security_alert",
            "event_type": event_type,
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return cls.create_notification(
            title=title, message=message,
            notification_type="security", priority=priority,
            action_type="review_security", metadata=metadata)

    @classmethod
    def notify_inventory_low(cls, product_id: str, product_name: str,
                             current_quantity: int, threshold: int) -> 'Notification':
        return cls.create_inventory_notification(
            title=f"Low Inventory Alert: {product_name}",
            message=f"Inventory for {product_name} is low. Current: {current_quantity}, Threshold: {threshold}",
            product_id=product_id, batch_id="N/A",
            change_type="low_stock", priority="high")

    @classmethod
    def notify_order_status_change(cls, order_id: str, order_number: str,
                                   old_status: str, new_status: str) -> 'Notification':
        priority = "medium" if new_status in ("processing", "shipped") else "low"
        return cls.create_order_notification(
            title=f"Order Status Updated: {order_number}",
            message=f"Order {order_number} status changed from {old_status} to {new_status}",
            order_id=order_id, order_status=new_status, priority=priority)