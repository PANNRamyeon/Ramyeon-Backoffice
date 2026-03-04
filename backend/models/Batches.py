"""
Batch Model - Following ERD Specification with Optimistic Locking
PK = "batches", SK = "BATCH-#####"
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.exceptions import UpdateError
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION
from app.utils.counters import counter_service
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

# Pattern for legacy MongoDB-style corrupted datetimes (e.g. 000002025-10-08T12:10:51.644000)
_CORRUPT_DATETIME_PATTERN = re.compile(r"^0+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)")


def _fix_corrupt_datetime_string(s: str) -> Optional[str]:
    """
    If s is a corrupted datetime (leading zeros before year), return fixed string; else None.
    Extra defensive handling for known legacy pattern like '000002025-10-08T12:10:51.644000'.
    """
    if not isinstance(s, str):
        return None
    # Primary regex-based fix
    m = _CORRUPT_DATETIME_PATTERN.match(s)
    if m:
        return m.group(1)
    # Fallback: if we see the legacy 000002025... pattern anywhere, strip to first '2025-'
    if "000002025-10-08" in s:
        idx = s.find("2025-")
        if idx != -1:
            return s[idx:]
    return None


def _deep_fix_datetimes_in_value(val):
    """Recursively fix corrupted datetime strings; returns (fixed_value, True if any change)."""
    if isinstance(val, str):
        fixed = _fix_corrupt_datetime_string(val)
        return (fixed if fixed is not None else val, fixed is not None)
    if isinstance(val, dict):
        out = {}
        changed = False
        for k, v in val.items():
            v2, c = _deep_fix_datetimes_in_value(v)
            out[k] = v2
            changed = changed or c
        return (out, changed)
    if isinstance(val, list):
        out = []
        changed = False
        for elem in val:
            e2, c = _deep_fix_datetimes_in_value(elem)
            out.append(e2)
            changed = changed or c
        return (out, changed)
    return (val, False)


def _repair_batch_item_datetimes(item: dict) -> dict:
    """
    Return a dict of top-level attribute names to fixed values for any attribute
    that contained a corrupted datetime string. Use with UpdateExpression SET.
    """
    updates = {}
    for key, val in list(item.items()):
        if key in ("PK", "SK"):
            continue
        fixed_val, changed = _deep_fix_datetimes_in_value(val)
        if changed:
            updates[key] = fixed_val
    return updates

# ============= NESTED MAP ATTRIBUTES =============
class SyncLogDetailItem(MapAttribute):
    """Details for sync_logs entries"""
    field_name = UnicodeAttribute(null=True)
    old_value = UnicodeAttribute(null=True)
    new_value = UnicodeAttribute(null=True)
    error_message = UnicodeAttribute(null=True)
    record_id = UnicodeAttribute(null=True)


class SyncLogItem(MapAttribute):
    """MapAttribute for sync_logs array items"""
    last_updated = UTCDateTimeAttribute()
    source = UnicodeAttribute()
    status = UnicodeAttribute()
    details = ListAttribute(of=SyncLogDetailItem, default=list)
    action = UnicodeAttribute()


class UsageHistoryItem(MapAttribute):
    """MapAttribute for usage_history array items"""
    timestamp = UTCDateTimeAttribute()
    quantity_used = NumberAttribute()
    reason = UnicodeAttribute()
    remaining_after = UnicodeAttribute()
    adjustment_type = UnicodeAttribute()
    adjusted_by = UnicodeAttribute()
    approved_by = UnicodeAttribute(null=True)
    notes = UnicodeAttribute(null=True)
    source = UnicodeAttribute()


# ============= GLOBAL SECONDARY INDEXES =============
class ProductIdIndex(GlobalSecondaryIndex):
    """GSI for querying batches by product_id"""
    class Meta:
        index_name = 'batch-product-id-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    product_id = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True, attr_name="SK")


class StatusExpiryIndex(GlobalSecondaryIndex):
    """GSI for querying batches by status with expiry date range"""
    class Meta:
        index_name = 'batch-status-expiry-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    status = UnicodeAttribute(hash_key=True)
    expiry_date = UTCDateTimeAttribute(range_key=True)


class ShipmentIdIndex(GlobalSecondaryIndex):
    """GSI for querying batches by shipment_id (foreign key to Shipment)."""
    class Meta:
        index_name = 'batch-shipment-id-index'
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5
    
    shipment_id = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True, attr_name="SK")


# ============= MAIN BATCH MODEL =============
class Batch(Model):
    """
    BATCH MODEL - Following ERD Specification with Optimistic Locking

    Each batch represents one product's quantity from a delivery. Use batch_number
    to group batches from the same physical shipment; use shipment_id to link
    to the Shipment entity when shipment-level metadata is tracked.

    - batch_number: Supplier's lot identifier (e.g. LOT-2024-001). Same value
      across batches from the same delivery. Groups products without requiring
      a Shipment record.
    - shipment_id: Optional foreign key to Shipment (SHIP-00001). Set when
      the delivery is recorded as a Shipment for metadata (freight, invoice, etc.).
    """

    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB
        region = AWS_REGION
        
        #if DYNAMODB_LOCAL:
         #   host = DYNAMODB_LOCAL_HOST
        
        read_capacity_units = 5
        write_capacity_units = 10
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="batches")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "BATCH-00001-00015"
    
    # ============= GSI DEFINITIONS =============
    product_id_index = ProductIdIndex()
    status_expiry_index = StatusExpiryIndex()
    shipment_id_index = ShipmentIdIndex()
    
    # ============= BATCH IDENTIFICATION =============
    product_id = UnicodeAttribute()
    batch_number = UnicodeAttribute()
    
    # ============= SHIPMENT REFERENCE =============
    shipment_id = UnicodeAttribute(null=True)  # Foreign key to Shipment (SHIP-#####)
    
    # ============= QUANTITY MANAGEMENT =============
    quantity_received = NumberAttribute()
    quantity_remaining = NumberAttribute()
    
    # ============= FINANCIAL INFORMATION =============
    cost_price = NumberAttribute()
    
    # ============= DATE INFORMATION =============
    expiry_date = UTCDateTimeAttribute()
    date_received = UTCDateTimeAttribute()
    
    # ============= SUPPLIER INFORMATION =============
    supplier_id = UnicodeAttribute()
    
    # ============= STATUS AND METADATA =============
    status = UnicodeAttribute(default="pending")  # Initial status
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    
    # ============= NESTED ARRAYS =============
    sync_logs = ListAttribute(of=SyncLogItem, default=list)
    usage_history = ListAttribute(of=UsageHistoryItem, default=list)
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_batch(cls, **kwargs) -> 'Batch':
        """
        Create a new batch with a per-product auto-generated SK and automatic status.
        """
        try:
            # The product_id is now required to generate the batch ID.
            product_id = kwargs.get('product_id')
            if not product_id:
                raise ValueError("product_id is required to create a batch.")

            # Generate SK using the new per-product batch counter service.
            sk = counter_service.get_next_batch_id(product_id)
            
            # Set required fields
            kwargs['pk'] = 'batches'
            kwargs['sk'] = sk
            
            # Set timestamps
            now = datetime.utcnow()
            if 'created_at' not in kwargs:
                kwargs['created_at'] = now
            if 'updated_at' not in kwargs:
                kwargs['updated_at'] = now
            
            # Set quantity_remaining if not provided
            if 'quantity_remaining' not in kwargs and 'quantity_received' in kwargs:
                kwargs['quantity_remaining'] = kwargs['quantity_received']
            
            # Create batch instance
            batch = cls(**kwargs)
            
            # Run initial status calculation
            batch._calculate_and_set_status()
            
            # Save the batch
            batch.save()
            
            logger.info(f"Batch created: {sk} - Status: {batch.status}")
            return batch
            
        except Exception as e:
            logger.error(f"Failed to create batch: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, batch_id: str) -> 'Batch | None':
        """
        Get batch by ID
        """
        try:
            if not batch_id.startswith('BATCH-'):
                batch_id = f"BATCH-{batch_id}"
            
            return cls.get("batches", batch_id)
        except cls.DoesNotExist:
            logger.warning(f"Batch not found: {batch_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching batch {batch_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_product_id(cls, product_id: str, limit: int = 100) -> list:
        """
        Get all batches for a specific product using GSI
        """
        try:
            return list(cls.product_id_index.query(
                product_id,
                limit=limit,
                scan_index_forward=True
            ))
        except Exception as e:
            logger.error(f"Error querying batches for product {product_id}: {str(e)}")
            return []
    
    @classmethod
    def get_by_status(cls, status: str, limit: int = 100) -> list:
        """
        Get batches by status using GSI
        """
        try:
            return list(cls.status_expiry_index.query(
                status,
                limit=limit
            ))
        except Exception as e:
            logger.error(f"Error querying batches by status {status}: {str(e)}")
            return []

    @classmethod
    def get_by_shipment_id(cls, shipment_id: str, limit: int = 100) -> list:
        """
        Get all batches that belong to a shipment (via shipment_id GSI).
        Returns empty list if shipment_id is None or invalid.
        """
        if not shipment_id or not shipment_id.strip():
            return []
        try:
            if not shipment_id.startswith("SHIP-"):
                shipment_id = f"SHIP-{shipment_id}"
            return list(cls.shipment_id_index.query(
                shipment_id,
                limit=limit
            ))
        except Exception as e:
            logger.error(f"Error querying batches for shipment {shipment_id}: {str(e)}")
            return []

    @classmethod
    def get_by_batch_number(cls, batch_number: str, limit: int = 100) -> list:
        """
        Get all batches with the same batch_number (same physical delivery).
        Uses scan with filter; use for grouping when shipment_id is not set.
        """
        if not batch_number or not batch_number.strip():
            return []
        try:
            return list(cls.scan(
                filter_condition=cls.batch_number == batch_number.strip(),
                limit=limit
            ))
        except Exception as e:
            logger.error(f"Error querying batches by batch_number {batch_number}: {str(e)}")
            return []
    
    @classmethod
    def get_expiring_soon(cls, days_threshold: int = 30, 
                         status_filter: Optional[List[str]] = None) -> list:
        """
        Get batches expiring within X days (using GSI)
        """
        try:
            now = datetime.utcnow()
            future_date = now + timedelta(days=days_threshold)
            
            # If no status filter, get all statuses
            if not status_filter:
                # We need to query by each status individually
                batches = []
                for status in ["active", "low_stock", "expiring_soon"]:
                    batches.extend(list(cls.status_expiry_index.query(
                        status,
                        cls.expiry_date.between(now, future_date)
                    )))
                return batches
            else:
                batches = []
                for status in status_filter:
                    batches.extend(list(cls.status_expiry_index.query(
                        status,
                        cls.expiry_date.between(now, future_date)
                    )))
                return batches
                
        except Exception as e:
            logger.error(f"Error querying expiring batches: {str(e)}")
            return []
    
    @classmethod
    def get_low_stock_batches(cls, threshold_percentage: float = 0.1) -> list:
        """
        Get batches with low stock (less than threshold percentage)
        Note: This requires scanning, but for low-frequency alerts it's acceptable
        """
        try:
            low_stock_batches = []
            
            # Query active and low_stock batches
            for status in ["active", "low_stock"]:
                batches = cls.get_by_status(status, limit=1000)
                for batch in batches:
                    if batch.quantity_received > 0:
                        remaining_percentage = batch.quantity_remaining / batch.quantity_received
                        if remaining_percentage < threshold_percentage:
                            low_stock_batches.append(batch)
            
            return low_stock_batches
            
        except Exception as e:
            logger.error(f"Error getting low stock batches: {str(e)}")
            return []
    
    @classmethod
    def _repair_corrupted_batch_datetimes_in_table(cls) -> int:
        """
        Query batch items via boto3 (raw), fix any corrupted datetime strings in place
        (e.g. 000002025-10-08T... -> 2025-10-08T...), update_item, and return count fixed.
        """
        try:
            from decouple import config
            import boto3
            from boto3.dynamodb.conditions import Key

            table_name = config("DYNAMO_TABLE_NAME", default=DYNAMO_TABLE_NAME)
            region = config("AWS_REGION_NAME", default=AWS_REGION)
            table = (
                boto3.resource(
                    "dynamodb",
                    region_name=region,
                    aws_access_key_id=config("AWS_ACCESS_KEY_ID", default=""),
                    aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY", default=""),
                )
                .Table(table_name)
            )
        except Exception as e:
            logger.warning(f"Cannot get DynamoDB table for batch datetime repair: {e}")
            return 0

        fixed_count = 0
        last_key = None
        while True:
            kwargs = {"KeyConditionExpression": Key("PK").eq("batches")}
            if last_key:
                kwargs["ExclusiveStartKey"] = last_key
            response = table.query(**kwargs)
            for item in response.get("Items", []):
                updates = _repair_batch_item_datetimes(item)
                if not updates:
                    continue
                try:
                    set_parts = [f"#{k} = :{k}" for k in updates]
                    expr = "SET " + ", ".join(set_parts)
                    attr_values = {f":{k}": v for k, v in updates.items()}
                    attr_names = {f"#{k}": k for k in updates}
                    table.update_item(
                        Key={"PK": item["PK"], "SK": item["SK"]},
                        UpdateExpression=expr,
                        ExpressionAttributeValues=attr_values,
                        ExpressionAttributeNames=attr_names,
                    )
                    fixed_count += 1
                    logger.info(f"Repaired batch datetime(s) for SK={item.get('SK')}")
                except Exception as e:
                    logger.error(f"Failed to repair batch {item.get('SK')}: {e}")
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
        return fixed_count

    @classmethod
    def get_all_batches(cls, limit: int = 1000) -> list:
        """
        Get all batches (paginated). On datetime deserialization error, attempts to
        repair corrupted legacy datetime strings in the table and retries.
        """
        try:
            result = []
            query_iter = cls.query("batches", limit=limit)
            
            # Log the raw response for debugging
            if hasattr(query_iter, '_items_queried') and query_iter._items_queried:
                logger.debug(f"PynamoDB queried {query_iter._items_queried} items so far")
            
            for idx, batch in enumerate(query_iter):
                try:
                    result.append(batch)
                except Exception as item_err:
                    logger.error(f"Failed to deserialize batch at index {idx}: {item_err}")
                    # Try to log the raw item if accessible
                    try:
                        if hasattr(query_iter, '_get_next_page'):
                            logger.error(f"Raw data might be in internal buffer; cannot extract")
                    except:
                        pass
                    continue
            return result
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Error querying all batches: {err_msg}")
            
            # Try to extract which item caused the error
            import traceback
            tb_str = traceback.format_exc()
            logger.error(f"Full traceback:\n{tb_str}")
            
            if "Datetime string" in err_msg and "does not match format" in err_msg:
                logger.warning("Batch query failed due to corrupted datetime; attempting repair...")
                fixed = cls._repair_corrupted_batch_datetimes_in_table()
                logger.info(f"Repaired {fixed} batch record(s); retrying query.")
                try:
                    result = []
                    for idx, batch in enumerate(cls.query("batches", limit=limit)):
                        try:
                            result.append(batch)
                        except Exception as item_err:
                            logger.error(f"Failed to deserialize batch at index {idx} (after repair): {item_err}")
                            continue
                    return result
                except Exception as retry_err:
                    logger.error(f"Retry after repair also failed: {retry_err}")
                    return []
            return []
    
    # ============= INSTANCE METHODS =============
    
    def update_quantity(self, quantity_change: int, reason: str, 
                       adjusted_by: str, adjustment_type: str,
                       source: str = "manual", notes: Optional[str] = None,
                       approved_by: Optional[str] = None,
                       retry_count: int = 3) -> 'Batch':
        """
        Update batch quantity with optimistic locking and automatic status updates
        
        Args:
            quantity_change: Positive for additions, negative for deductions
            reason: Reason for adjustment
            adjusted_by: User/System that made adjustment
            adjustment_type: addition or deduction
            source: manual, pos, api, etc.
            notes: Additional notes
            approved_by: User who approved (if required)
            retry_count: Number of retry attempts on optimistic lock failure
        
        Returns:
            Batch: Updated batch instance
        
        Raises:
            ValueError: If insufficient quantity for deduction
            UpdateError: If optimistic lock fails after retries
        """
        for attempt in range(retry_count):
            try:
                # Capture current timestamp for optimistic locking
                original_updated_at = self.updated_at
                
                # For deductions, check sufficient quantity
                if quantity_change < 0 and abs(quantity_change) > self.quantity_remaining:
                    raise ValueError(
                        f"Insufficient quantity. Available: {self.quantity_remaining}, "
                        f"Requested: {abs(quantity_change)}"
                    )
                
                # Calculate new quantity
                new_quantity = self.quantity_remaining + quantity_change
                quantity_used = abs(quantity_change) if quantity_change < 0 else 0
                
                # Create usage history record
                history_item = UsageHistoryItem(
                    timestamp=datetime.utcnow(),
                    quantity_used=quantity_used,
                    reason=reason,
                    remaining_after=str(new_quantity),
                    adjustment_type=adjustment_type,
                    adjusted_by=adjusted_by,
                    approved_by=approved_by,
                    notes=notes,
                    source=source
                )
                
                # Update batch attributes
                self.quantity_remaining = new_quantity
                self.usage_history.append(history_item)
                self.updated_at = datetime.utcnow()
                
                # Automatically update status based on new state
                self._calculate_and_set_status()
                
                # Save with optimistic locking condition
                condition = (Batch.pk == self.pk) & (Batch.sk == self.sk) & (Batch.updated_at == original_updated_at)
                self.save(condition=condition)
                
                logger.info(f"Batch {self.sk} quantity updated: {self.quantity_remaining}")
                return self
                
            except UpdateError as e:
                if "ConditionalCheckFailedException" in str(e) and attempt < retry_count - 1:
                    # Optimistic lock failed - reload and retry
                    logger.warning(f"Optimistic lock failed for batch {self.sk}, retry {attempt + 1}")
                    self.refresh()
                    continue
                else:
                    logger.error(f"Failed to update batch {self.sk} after {retry_count} attempts: {str(e)}")
                    raise UpdateError(f"Failed to update batch due to concurrent modification. Please try again.")
                    
            except Exception as e:
                logger.error(f"Error updating quantity for batch {self.sk}: {str(e)}")
                raise
    
    def adjust_quantity(self, new_quantity: int, reason: str,
                       adjusted_by: str, source: str = "manual",
                       notes: Optional[str] = None) -> 'Batch':
        """
        Set quantity to a specific value (absolute adjustment)
        """
        quantity_change = new_quantity - self.quantity_remaining
        return self.update_quantity(
            quantity_change=quantity_change,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type="adjustment",
            source=source,
            notes=notes
        )
    
    def consume_quantity(self, quantity: int, reason: str,
                        adjusted_by: str, source: str = "sale",
                        notes: Optional[str] = None) -> 'Batch':
        """
        Consume/deduct quantity from batch
        """
        return self.update_quantity(
            quantity_change=-quantity,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type="deduction",
            source=source,
            notes=notes
        )
    
    def add_quantity(self, quantity: int, reason: str,
                    adjusted_by: str, source: str = "receipt",
                    notes: Optional[str] = None) -> 'Batch':
        """
        Add quantity to batch
        """
        return self.update_quantity(
            quantity_change=quantity,
            reason=reason,
            adjusted_by=adjusted_by,
            adjustment_type="addition",
            source=source,
            notes=notes
        )
    
    def add_sync_log(self, source: str, status: str, action: str,
                    details: Optional[List[Dict]] = None) -> 'Batch':
        """
        Add a synchronization log entry
        """
        try:
            # Capture current timestamp for optimistic locking
            original_updated_at = self.updated_at
            
            # Convert details dicts to SyncLogDetailItem objects
            detail_items = []
            if details:
                for detail in details:
                    detail_items.append(SyncLogDetailItem(**detail))
            
            sync_log = SyncLogItem(
                last_updated=datetime.utcnow(),
                source=source,
                status=status,
                action=action,
                details=detail_items
            )
            
            self.sync_logs.append(sync_log)
            self.updated_at = datetime.utcnow()
            
            # Save with optimistic locking
            condition = (Batch.pk == self.pk) & (Batch.sk == self.sk) & (Batch.updated_at == original_updated_at)
            self.save(condition=condition)
            
            logger.info(f"Sync log added to batch {self.sk}: {action} - {status}")
            return self
            
        except UpdateError as e:
            logger.error(f"Concurrent modification while adding sync log to batch {self.sk}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to add sync log to batch {self.sk}: {str(e)}")
            raise
    
    def _calculate_and_set_status(self):
        """
        Fully automatic status calculation based on quantity and expiry date
        This is called after every quantity change
        """
        now = datetime.utcnow()
        
        # Check if expired
        if self.expiry_date and now > self.expiry_date:
            self.status = "expired"
            return
        
        # Check if exhausted
        if self.quantity_remaining <= 0:
            self.status = "exhausted"
            return
        
        # Check if low stock (less than 10%)
        if self.quantity_received > 0:
            remaining_percentage = self.quantity_remaining / self.quantity_received
            if remaining_percentage <= 0.1:  # 10% or less
                self.status = "low_stock"
                return
        
        # Check if expiring soon (within 7 days)
        if self.expiry_date:
            days_until_expiry = (self.expiry_date - now).days
            if 0 <= days_until_expiry <= 7:
                self.status = "expiring_soon"
                return
        
        # Default active status
        self.status = "active"
    
    def is_expired(self) -> bool:
        """Check if batch is expired"""
        if not self.expiry_date:
            return False
        return datetime.utcnow() > self.expiry_date
    
    def days_until_expiry(self) -> int:
        """Calculate days until expiry"""
        if not self.expiry_date:
            return float('inf')
        
        delta = self.expiry_date - datetime.utcnow()
        return delta.days
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        Get detailed status information
        """
        now = datetime.utcnow()
        
        info = {
            "current_status": self.status,
            "is_expired": self.is_expired(),
            "days_until_expiry": self.days_until_expiry(),
            "quantity_remaining": self.quantity_remaining,
            "quantity_received": self.quantity_received,
            "percentage_remaining": 0,
            "needs_attention": False,
            "reasons": []
        }
        
        if self.quantity_received > 0:
            info["percentage_remaining"] = (self.quantity_remaining / self.quantity_received) * 100
        
        # Determine if needs attention and why
        if self.status in ["expired", "exhausted"]:
            info["needs_attention"] = True
            info["reasons"].append(self.status)
        elif self.status == "low_stock":
            info["needs_attention"] = True
            info["reasons"].append("Low stock")
        elif self.status == "expiring_soon":
            info["needs_attention"] = True
            info["reasons"].append(f"Expiring in {self.days_until_expiry()} days")
        elif info["percentage_remaining"] < 20:  # Less than 20% remaining
            info["needs_attention"] = True
            info["reasons"].append("Stock running low")
        
        return info
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Get summary of batch usage
        """
        try:
            total_used = self.quantity_received - self.quantity_remaining
            usage_by_reason = {}
            usage_by_type = {}
            
            for record in self.usage_history:
                reason = record.reason
                adjustment_type = record.adjustment_type
                qty_used = record.quantity_used
                
                usage_by_reason[reason] = usage_by_reason.get(reason, 0) + qty_used
                usage_by_type[adjustment_type] = usage_by_type.get(adjustment_type, 0) + qty_used
            
            return {
                "batch_id": self.sk,
                "batch_number": self.batch_number,
                "total_received": self.quantity_received,
                "total_remaining": self.quantity_remaining,
                "total_used": total_used,
                "usage_percentage": (
                    (total_used / self.quantity_received * 100) 
                    if self.quantity_received > 0 else 0
                ),
                "usage_by_reason": usage_by_reason,
                "usage_by_type": usage_by_type,
                "usage_history_count": len(self.usage_history)
            }
            
        except Exception as e:
            logger.error(f"Error generating usage summary for batch {self.sk}: {str(e)}")
            return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert batch to dictionary for API response
        """
        try:
            return {
                "batch_id": self.sk,
                "batch_number": self.batch_number,
                "product_id": self.product_id,
                "shipment_id": self.shipment_id,
                "quantity_received": self.quantity_received,
                "quantity_remaining": self.quantity_remaining,
                "cost_price": float(self.cost_price) if self.cost_price else None,
                "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
                "date_received": self.date_received.isoformat() if self.date_received else None,
                "supplier_id": self.supplier_id,
                "status": self.status,
                "status_info": self.get_status_info(),
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "is_expired": self.is_expired(),
                "days_until_expiry": self.days_until_expiry(),
                "sync_logs_count": len(self.sync_logs),
                "usage_history_count": len(self.usage_history)
            }
        except Exception as e:
            logger.error(f"Error converting batch to dict: {str(e)}")
            return {}
    
    def save(self, condition=None, **kwargs):
        """Override save to handle optimistic locking"""
        self.updated_at = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


# ============= BATCH MANAGER WITH AUTO STATUS UPDATES =============
class BatchManager:
    """
    Manager for batch operations with automatic status management
    """
    
    @staticmethod
    def update_expired_batches() -> List[Dict]:
        """
        Scan and update status for expired batches
        Returns list of updated batches
        """
        updated_batches = []
        try:
            # Get batches that are not already marked as expired
            for status in ["active", "low_stock", "expiring_soon"]:
                batches = Batch.get_by_status(status, limit=1000)
                for batch in batches:
                    if batch.is_expired() and batch.status != "expired":
                        try:
                            # Update status to expired
                            original_updated_at = batch.updated_at
                            batch.status = "expired"
                            batch.updated_at = datetime.utcnow()
                            
                            condition = (Batch.pk == batch.pk) & (Batch.sk == batch.sk) & (Batch.updated_at == original_updated_at)
                            batch.save(condition=condition)
                            
                            updated_batches.append({
                                "batch_id": batch.sk,
                                "old_status": status,
                                "new_status": "expired"
                            })
                            logger.info(f"Batch {batch.sk} marked as expired")
                            
                        except UpdateError:
                            logger.warning(f"Concurrent update on batch {batch.sk}, skipping")
                            continue
            
            return updated_batches
            
        except Exception as e:
            logger.error(f"Error updating expired batches: {str(e)}")
            return []
    
    @staticmethod
    def get_batch_for_fulfillment(product_id: str, 
                                 quantity_needed: int,
                                 strategy: str = "fefo") -> Dict:
        """
        Get batches for fulfilling an order with automatic status consideration
        
        Args:
            product_id: Product ID
            quantity_needed: Quantity needed
            strategy: "fefo" (first-expired-first-out) or "fifo" (first-in-first-out)
        
        Returns:
            dict: Batches to use and remaining quantity needed
        """
        try:
            # Get all non-exhausted, non-expired batches for the product
            batches = Batch.get_by_product_id(product_id, limit=100)
            
            valid_batches = [
                b for b in batches 
                if b.status in ["active", "low_stock", "expiring_soon"]
                and not b.is_expired()
                and b.quantity_remaining > 0
            ]
            
            if not valid_batches:
                return {
                    "batches_to_use": [],
                    "remaining_quantity": quantity_needed,
                    "can_fulfill": False,
                    "message": f"No valid batches found for product {product_id}"
                }
            
            # Sort based on strategy
            if strategy == "fefo":
                valid_batches.sort(key=lambda x: x.expiry_date)  # Soonest expiry first
            else:  # fifo
                valid_batches.sort(key=lambda x: x.date_received)  # Oldest first
            
            batches_to_use = []
            remaining_quantity = quantity_needed
            
            for batch in valid_batches:
                if remaining_quantity <= 0:
                    break
                
                # Determine how much to take from this batch
                take_quantity = min(batch.quantity_remaining, remaining_quantity)
                
                batches_to_use.append({
                    "batch": batch,
                    "quantity_to_take": take_quantity,
                    "batch_status": batch.status,
                    "expiry_date": batch.expiry_date.isoformat() if batch.expiry_date else None,
                    "days_until_expiry": batch.days_until_expiry()
                })
                
                remaining_quantity -= take_quantity
            
            can_fulfill = remaining_quantity == 0
            
            return {
                "batches_to_use": batches_to_use,
                "remaining_quantity": remaining_quantity,
                "can_fulfill": can_fulfill,
                "message": f"Can fulfill {quantity_needed - remaining_quantity} of {quantity_needed}" if not can_fulfill else "Can fully fulfill"
            }
            
        except Exception as e:
            logger.error(f"Error getting batches for fulfillment: {str(e)}")
            return {
                "batches_to_use": [],
                "remaining_quantity": quantity_needed,
                "can_fulfill": False,
                "message": f"Error: {str(e)}"
            }