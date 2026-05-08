"""
ShipmentService - Service layer for shipment (delivery) operations.
Uses singleton pattern. Usage: get_singleton(ShipmentService)
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.utils.singleton import get_singleton
from app.services.inventory.batch_service import BatchService
from app.services.core.audit_service import AuditLogService
from models.Shipment import Shipment
from models.Batches import Batch
from models.Product import Product
import logging

logger = logging.getLogger(__name__)

_SYSTEM_USER = {'user_id': 'system', 'username': 'system', 'branch_id': None, 'source': 'service'}


class ShipmentService:
    """
    Service layer for shipment management.
    Use via: from app.utils.singleton import get_singleton; get_singleton(ShipmentService)
    """

    def __init__(self):
        logger.info("Initializing ShipmentService singleton instance")
        self._supplier_name_cache = {}
        self.audit_service = AuditLogService()

    def _get_supplier_name(self, supplier_id: str) -> str:
        """Resolve supplier_id to name with simple cache. Returns 'Unknown Supplier' if not found."""
        if not supplier_id:
            return "Unknown Supplier"
        if supplier_id in self._supplier_name_cache:
            return self._supplier_name_cache[supplier_id]
        try:
            from models.Supplier import Supplier
            from pynamodb.exceptions import DoesNotExist
            supplier = Supplier.get("suppliers", supplier_id)
            if supplier and getattr(supplier, "supplier_name", None):
                name = supplier.supplier_name
                self._supplier_name_cache[supplier_id] = name
                return name
        except DoesNotExist:
            pass
        except Exception as e:
            logger.warning(f"Failed to fetch supplier name for {supplier_id}: {e}")
        return "Unknown Supplier"

    def create_shipment(self, shipment_data: Dict[str, Any], current_user=None) -> Dict[str, Any]:
        """
        Create a new shipment. Required: supplier_id, batch_number.
        Optional: shipment_date, invoice_number, status, freight_cost, notes, received_by.
        """
        try:
            supplier_id = shipment_data.get("supplier_id")
            batch_number = shipment_data.get("batch_number")
            if not supplier_id or not batch_number:
                raise ValueError("supplier_id and batch_number are required")

            shipment_date = shipment_data.get("shipment_date")
            if isinstance(shipment_date, str):
                try:
                    shipment_date = datetime.fromisoformat(shipment_date.replace("Z", "+00:00"))
                except ValueError:
                    shipment_date = None

            shipment = Shipment.create_shipment(
                supplier_id=supplier_id,
                batch_number=batch_number,
                shipment_date=shipment_date,
                invoice_number=shipment_data.get("invoice_number"),
                status=shipment_data.get("status", "received"),
                freight_cost=shipment_data.get("freight_cost"),
                notes=shipment_data.get("notes"),
                received_by=shipment_data.get("received_by"),
            )
            logger.info(f"Shipment created: {shipment.sk}")
            if getattr(shipment, "status", None) == "received":
                try:
                    get_singleton(BatchService).activate_batches_for_shipment(
                        shipment.sk, current_user=current_user
                    )
                except Exception as act_err:
                    logger.warning("Activate batches for new shipment %s: %s", shipment.sk, act_err)

            shipment_dict = shipment.to_dict()
            try:
                self.audit_service.log_shipment_create(current_user or _SYSTEM_USER, shipment_dict)
            except Exception as ae:
                logger.error(f"Audit logging failed for shipment create: {ae}")

            return shipment_dict
        except ValueError as e:
            logger.error(f"Validation error creating shipment: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating shipment: {e}")
            raise Exception(f"Error creating shipment: {str(e)}") from e

    def get_shipment_by_id(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Get a single shipment by ID. Returns None if not found."""
        try:
            shipment = Shipment.get_by_id(shipment_id)
            return shipment.to_dict() if shipment else None
        except Exception as e:
            logger.error(f"Error getting shipment {shipment_id}: {e}")
            raise Exception(f"Error getting shipment: {str(e)}") from e

    def get_all_shipments(
        self,
        supplier_id: Optional[str] = None,
        limit: int = 100,
        enrich_with_supplier_name: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List shipments, optionally filtered by supplier_id.
        """
        try:
            if supplier_id:
                shipments = Shipment.get_by_supplier_id(supplier_id, limit=limit)
            else:
                shipments = list(Shipment.query("shipments", limit=limit, scan_index_forward=False))

            result = [s.to_dict() for s in shipments]
            if enrich_with_supplier_name:
                for d in result:
                    d["supplier_name"] = self._get_supplier_name(d.get("supplier_id") or "")
            return result
        except Exception as e:
            logger.error(f"Error listing shipments: {e}")
            raise Exception(f"Error listing shipments: {str(e)}") from e

    def get_shipments_by_supplier(self, supplier_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Convenience: list shipments for a supplier."""
        return self.get_all_shipments(supplier_id=supplier_id, limit=limit)

    def get_shipment_with_batches(
        self,
        shipment_id: str,
        enrich_with_product: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Get shipment by ID and attach its batches (via Batch.get_by_shipment_id).
        Optionally add product_name to each batch.
        """
        try:
            shipment = Shipment.get_by_id(shipment_id)
            if not shipment:
                return None

            data = shipment.to_dict()
            batches = Batch.get_by_shipment_id(shipment_id)
            batch_dicts = [b.to_dict() for b in batches]

            if enrich_with_product:
                for b in batch_dicts:
                    pid = b.get("product_id")
                    if pid:
                        try:
                            p = Product.get_by_id(pid)
                            b["product_name"] = p.product_name if p else "Unknown Product"
                        except Exception:
                            b["product_name"] = "Unknown Product"

            data["batches"] = batch_dicts
            data["batches_count"] = len(batch_dicts)
            return data
        except Exception as e:
            logger.error(f"Error getting shipment with batches {shipment_id}: {e}")
            raise Exception(f"Error getting shipment with batches: {str(e)}") from e

    def update_shipment(self, shipment_id: str, update_data: Dict[str, Any], current_user=None) -> Optional[Dict[str, Any]]:
        """
        Update shipment fields. Read-only: pk, sk.
        Allowed: status, invoice_number, freight_cost, notes, received_by, total_products.
        """
        try:
            shipment = Shipment.get_by_id(shipment_id)
            if not shipment:
                return None

            old_dict = shipment.to_dict()

            read_only = {"pk", "sk", "shipment_id"}
            for key, value in update_data.items():
                if key in read_only:
                    continue
                if hasattr(shipment, key):
                    setattr(shipment, key, value)

            shipment.updated_at = datetime.utcnow()
            shipment.save()
<<<<<<< Updated upstream
            if getattr(shipment, "status", None) == "received":
=======
            new_dict = shipment.to_dict()

            new_status = getattr(shipment, "status", None)
            if new_status == "received":
>>>>>>> Stashed changes
                try:
                    get_singleton(BatchService).activate_batches_for_shipment(
                        shipment_id, current_user=current_user
                    )
                except Exception as act_err:
                    logger.warning("Activate batches for shipment %s: %s", shipment_id, act_err)
<<<<<<< Updated upstream
            return shipment.to_dict()
=======
            elif new_status == "cancelled":
                try:
                    get_singleton(BatchService).cancel_batches_for_shipment(
                        shipment_id, current_user=current_user
                    )
                except Exception as cancel_err:
                    logger.warning("Cancel batches for shipment %s: %s", shipment_id, cancel_err)

            try:
                self.audit_service.log_shipment_update(
                    current_user or _SYSTEM_USER, shipment_id, old_dict, new_dict
                )
            except Exception as ae:
                logger.error(f"Audit logging failed for shipment update: {ae}")

            return new_dict
>>>>>>> Stashed changes
        except Exception as e:
            logger.error(f"Error updating shipment {shipment_id}: {e}")
            raise Exception(f"Error updating shipment: {str(e)}") from e
