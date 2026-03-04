"""
Shipment Model - Tracks physical deliveries from suppliers.
PK = "shipments", SK = "SHIP-#####"
Single Table Design using RamyeonCornerDB

Relationship: One Shipment has many Batches (each batch references shipment_id).
Use batch_number on both Shipment and Batch to align with supplier's lot number.
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    UTCDateTimeAttribute,
)
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION
from app.utils.counters import counter_service
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class Shipment(Model):
    """
    SHIPMENT MODEL - One record per physical delivery from a supplier.

    Use this when you need to track shipment-level metadata (freight, invoice,
    inspection status). Each Batch can reference a Shipment via shipment_id.

    batch_number: Supplier's lot/shipment identifier (e.g. LOT-2024-001).
    Same value can be stored on related Batch records for grouping.
    """

    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        read_capacity_units = 3
        write_capacity_units = 3

    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="shipments")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "SHIP-00001"

    # ============= SUPPLIER & IDENTIFICATION =============
    supplier_id = UnicodeAttribute()
    batch_number = UnicodeAttribute()  # Supplier's lot number (e.g. LOT-2024-001)

    # ============= DATES =============
    shipment_date = UTCDateTimeAttribute()  # When goods were received
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)

    # ============= OPTIONAL METADATA =============
    invoice_number = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="received")  # received, inspected, approved, quality_issue
    freight_cost = NumberAttribute(null=True)
    notes = UnicodeAttribute(null=True)
    received_by = UnicodeAttribute(null=True)
    total_products = NumberAttribute(null=True)  # Number of product batches in this shipment

    # ============= CLASS METHODS =============

    @classmethod
    def create_shipment(
        cls,
        supplier_id: str,
        batch_number: str,
        shipment_date: Optional[datetime] = None,
        **kwargs,
    ) -> "Shipment":
        """
        Create a new shipment. SK is auto-generated (SHIP-00001, SHIP-00002, ...).
        """
        if not supplier_id or not supplier_id.strip():
            raise ValueError("supplier_id is required.")
        if not batch_number or not batch_number.strip():
            raise ValueError("batch_number is required.")

        sk = counter_service.get_next_id("shipments")
        now = datetime.utcnow()
        shipment_date = shipment_date or now

        shipment = cls(
            pk="shipments",
            sk=sk,
            supplier_id=supplier_id.strip(),
            batch_number=batch_number.strip(),
            shipment_date=shipment_date,
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        shipment.save()
        logger.info(f"Shipment created: {sk} (batch_number={batch_number})")
        return shipment

    @classmethod
    def get_by_id(cls, shipment_id: str) -> Optional["Shipment"]:
        """Get shipment by ID (e.g. SHIP-00001)."""
        try:
            if not shipment_id.startswith("SHIP-"):
                shipment_id = f"SHIP-{shipment_id}"
            return cls.get("shipments", shipment_id)
        except cls.DoesNotExist:
            logger.warning(f"Shipment not found: {shipment_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching shipment {shipment_id}: {e}")
            return None

    @classmethod
    def get_by_supplier_id(cls, supplier_id: str, limit: int = 100) -> List["Shipment"]:
        """Get shipments for a supplier (scan with filter)."""
        try:
            return list(
                cls.query(
                    "shipments",
                    filter_condition=cls.supplier_id == supplier_id,
                    limit=limit,
                    scan_index_forward=False,
                )
            )
        except Exception as e:
            logger.error(f"Error querying shipments for supplier {supplier_id}: {e}")
            return []

    def to_dict(self) -> Dict[str, Any]:
        """Convert shipment to dictionary for API responses."""
        try:
            return {
                "shipment_id": self.sk,
                "supplier_id": self.supplier_id,
                "batch_number": self.batch_number,
                "shipment_date": self.shipment_date.isoformat() if self.shipment_date else None,
                "invoice_number": self.invoice_number,
                "status": self.status,
                "freight_cost": float(self.freight_cost) if self.freight_cost is not None else None,
                "notes": self.notes,
                "received_by": self.received_by,
                "total_products": int(self.total_products) if self.total_products is not None else None,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }
        except Exception as e:
            logger.error(f"Error converting shipment to dict: {e}")
            return {}
