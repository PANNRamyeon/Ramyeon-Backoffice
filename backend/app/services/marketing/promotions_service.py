from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

from pynamodb.exceptions import PynamoDBException
from pynamodb.expressions.condition import Condition

from models.Promotions import Promotion, PromotionManager, UsageHistoryItem

logger = logging.getLogger(__name__)


class PromotionService:
    """
    Service layer for promotion operations, providing:
    - CRUD with GSI queries
    - Atomic usage tracking
    - Batch operations
    - POS synchronization
    - Paginated listings with filtering
    - Consistent response format: {"success": bool, "data": any, "error": str?}
    """

    def __init__(self, current_user: str = "system"):
        """
        Initialize service with the user performing actions (for audit logs).
        In a real app, this would be extracted from the request context.
        """
        self.current_user = current_user

    # ============= CRUD Operations =============

    def get_promotions(
        self,
        status: Optional[str] = None,
        target_type: Optional[str] = None,
        seasonal_tag: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50,
        last_evaluated_key: Optional[Dict] = None,
    ) -> Tuple[List[Dict], Optional[Dict]]:
        """
        Retrieve promotions with optional filters and pagination.
        Uses appropriate GSIs to avoid full table scans.
        Returns (list_of_promotion_dicts, next_page_token).
        """
        try:
            # Base filter: exclude deleted unless requested
            filter_condition = None
            if not include_deleted:
                filter_condition = Promotion.isDeleted == False

            # Determine which index to use based on provided filters
            if status:
                query = Promotion.status_index.query(
                    "promotions",
                    Promotion.status == status,
                    filter_condition=filter_condition,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )
            elif target_type:
                query = Promotion.target_type_index.query(
                    "promotions",
                    Promotion.target_type == target_type,
                    filter_condition=filter_condition,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )
            elif seasonal_tag:
                query = Promotion.seasonal_index.query(
                    "promotions",
                    Promotion.seasonal_tag == seasonal_tag,
                    filter_condition=filter_condition,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )
            else:
                query = Promotion.query(
                    "promotions",
                    filter_condition=filter_condition,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )

            promotions = list(query)
            last_key = query.last_evaluated_key
            return [p.to_dict() for p in promotions], last_key

        except PynamoDBException as e:
            logger.error(f"Error listing promotions: {str(e)}")
            raise Exception(f"Database error: {str(e)}")

    def get_promotion_by_id(self, promotion_id: str, include_deleted: bool = False) -> Optional[Dict]:
        """Fetch a single promotion by its ID (PROMO-##### or just #####)."""
        try:
            promotion = Promotion.get_by_id(promotion_id, include_deleted=include_deleted)
            return promotion.to_dict() if promotion else None
        except PynamoDBException as e:
            logger.error(f"Error fetching promotion {promotion_id}: {str(e)}")
            raise Exception(f"Database error: {str(e)}")

    def create_promotion(self, promo_data: Dict) -> Dict:
        """
        Create a new promotion.
        Expects promo_data to contain all required fields for Promotion.create_promotion.
        The current_user is injected for audit fields.
        """
        try:
            promo_data["created_by"] = self.current_user
            promotion = Promotion.create_promotion(**promo_data)
            logger.info(f"Promotion created: {promotion.sk} by {self.current_user}")
            return {"success": True, "data": promotion.to_dict()}
        except ValueError as ve:
            logger.warning(f"Validation error creating promotion: {str(ve)}")
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            logger.error(f"Error creating promotion: {str(e)}")
            return {"success": False, "error": "Database error"}

    def update_promotion(self, promotion_id: str, promo_data: Dict) -> Dict:
        """Update an existing promotion with partial data."""
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {"success": False, "error": "Promotion not found"}

            promotion.update_promotion(updated_by=self.current_user, **promo_data)
            logger.info(f"Promotion updated: {promotion_id} by {self.current_user}")
            return {"success": True, "data": promotion.to_dict()}
        except ValueError as ve:
            logger.warning(f"Validation error updating promotion {promotion_id}: {str(ve)}")
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            logger.error(f"Error updating promotion {promotion_id}: {str(e)}")
            return {"success": False, "error": "Database error"}

    def delete_promotion(self, promotion_id: str, reason: str) -> Dict:
        """Soft-delete a promotion."""
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion or promotion.isDeleted:
                return {"success": False, "error": "Promotion not found or already deleted"}

            promotion.soft_delete(deleted_by=self.current_user, reason=reason)
            logger.info(f"Promotion soft-deleted: {promotion_id} by {self.current_user}")
            return {"success": True, "data": {"message": "Promotion soft-deleted"}}
        except ValueError as ve:
            logger.warning(f"Validation error deleting promotion {promotion_id}: {str(ve)}")
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            logger.error(f"Error deleting promotion {promotion_id}: {str(e)}")
            return {"success": False, "error": "Database error"}

    # ============= Status Management =============

    def activate_promotion(self, promotion_id: str, reason: Optional[str] = None) -> Dict:
        """Activate a promotion (if not already active)."""
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {"success": False, "error": "Promotion not found"}

            promotion.activate(activated_by=self.current_user, reason=reason)
            logger.info(f"Promotion activated: {promotion_id} by {self.current_user}")
            return {"success": True, "data": promotion.to_dict()}
        except ValueError as ve:
            logger.warning(f"Validation error activating promotion {promotion_id}: {str(ve)}")
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            logger.error(f"Error activating promotion {promotion_id}: {str(e)}")
            return {"success": False, "error": "Database error"}

    def deactivate_promotion(self, promotion_id: str, reason: str) -> Dict:
        """Deactivate a promotion (requires reason)."""
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {"success": False, "error": "Promotion not found"}

            promotion.deactivate(deactivated_by=self.current_user, reason=reason)
            logger.info(f"Promotion deactivated: {promotion_id} by {self.current_user}")
            return {"success": True, "data": promotion.to_dict()}
        except ValueError as ve:
            logger.warning(f"Validation error deactivating promotion {promotion_id}: {str(ve)}")
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            logger.error(f"Error deactivating promotion {promotion_id}: {str(e)}")
            return {"success": False, "error": "Database error"}

    # ============= Usage Tracking (Atomic) =============

    def increment_usage(
        self,
        promotion_id: str,
        order_id: str,
        discount_amount: float,
        transaction_amount: float,
        branch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        pos_terminal_id: Optional[str] = None,
        items: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Atomically increment usage counter and add a usage history entry.
        Uses a conditional update to ensure usage limit is not exceeded.
        """
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {"success": False, "error": "Promotion not found"}

            # Prepare update actions
            actions = [
                Promotion.current_usage.add(1),
                Promotion.total_revenue_impact.add(discount_amount),
                Promotion.updated_at.set(datetime.utcnow()),
            ]

            history_item = UsageHistoryItem(
                order_id=order_id,
                user_id=user_id or self.current_user,
                branch_id=branch_id,
                discount_amount=discount_amount,
                transaction_amount=transaction_amount,
                timestamp=datetime.utcnow(),
                pos_terminal_id=pos_terminal_id,
                items=items,
            )
            actions.append(
                Promotion.usage_history.set(
                    Promotion.usage_history.append([history_item])
                )
            )

            # Condition: must be active, within date range, and under usage limit
            condition = (
                (Promotion.isDeleted == False)
                & (Promotion.status == "active")
                & (Promotion.start_date <= datetime.utcnow())
                & (Promotion.end_date >= datetime.utcnow())
            )
            if promotion.usage_limit is not None:
                condition &= (Promotion.current_usage < promotion.usage_limit)

            # Perform atomic update
            Promotion.update(condition=condition, actions=actions)
            promotion.refresh()
            logger.info(f"Usage incremented for promotion {promotion_id}, order {order_id}")
            return {"success": True, "data": promotion.to_dict()}

        except PynamoDBException as e:
            if "ConditionalCheckFailedException" in str(e):
                return {"success": False, "error": "Promotion is no longer applicable or has reached its usage limit"}
            logger.error(f"Error incrementing usage for promotion {promotion_id}: {str(e)}")
            return {"success": False, "error": "Database error"}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"success": False, "error": str(e)}

    # ============= Batch Operations =============

    def activate_batch(self, promotion_ids: List[str], reason: Optional[str] = None) -> Dict:
        """
        Activate multiple promotions in batch.
        Returns summary of successes and failures.
        """
        from models.Promotions import activate_batch_promotions

        result = activate_batch_promotions(promotion_ids, self.current_user, reason)
        logger.info(f"Batch activation: {len(result['activated'])} succeeded, {len(result['errors'])} failed")
        return {"success": True, "data": result}

    def create_seasonal_batch(self, seasonal_data: List[Dict]) -> Dict:
        """
        Create multiple seasonal promotions in batch.
        """
        from models.Promotions import create_seasonal_promotions

        result = create_seasonal_promotions(seasonal_data, self.current_user)
        logger.info(f"Batch seasonal creation: {result['total_created']} created")
        return {"success": True, "data": result}

    # ============= POS Integration =============

    def sync_to_pos(self, promotion_ids: Optional[List[str]] = None) -> Dict:
        """
        Sync specified promotions (or all pending) to POS system.
        """
        try:
            result = PromotionManager.sync_promotions_to_pos(promotion_ids)
            logger.info(f"POS sync completed: {result.get('synced')}")
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"POS sync failed: {str(e)}")
            return {"success": False, "error": f"POS sync error: {str(e)}"}

    def mark_pos_synced(self, promotion_id: str, terminal_id: Optional[str] = None) -> Dict:
        """Manually mark a promotion as synced with POS."""
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {"success": False, "error": "Promotion not found"}

            promotion.mark_pos_synced(terminal_id)
            logger.info(f"Promotion {promotion_id} marked as POS synced")
            return {"success": True, "data": promotion.to_dict()}
        except PynamoDBException as e:
            logger.error(f"Error marking POS sync for {promotion_id}: {str(e)}")
            return {"success": False, "error": "Database error"}

    # ============= Discount Calculation =============

    def get_applicable_discounts(
        self,
        original_amount: float,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> Dict:
        """
        Get all applicable promotions for a transaction.
        """
        try:
            discounts = PromotionManager.get_effective_discounts(
                original_amount, target_type, target_id, branch_id
            )
            return {"success": True, "data": discounts}
        except Exception as e:
            logger.error(f"Error getting applicable discounts: {str(e)}")
            return {"success": False, "error": f"Discount calculation error: {str(e)}"}

    def calculate_best_discount(
        self,
        original_amount: float,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> Dict:
        """
        Calculate the best possible discount for a transaction.
        """
        try:
            best = PromotionManager.calculate_best_discount(
                original_amount, target_type, target_id, branch_id
            )
            return {"success": True, "data": best}
        except Exception as e:
            logger.error(f"Error calculating best discount: {str(e)}")
            return {"success": False, "error": f"Discount calculation error: {str(e)}"}

    # ============= Reporting =============

    def get_effectiveness_report(self, days: int = 30) -> Dict:
        """Generate a promotion effectiveness report."""
        try:
            report = PromotionManager.get_promotion_effectiveness_report(days)
            return {"success": True, "data": report}
        except Exception as e:
            logger.error(f"Error generating effectiveness report: {str(e)}")
            return {"success": False, "error": f"Reporting error: {str(e)}"}

    def get_summary(self) -> Dict:
        """Get summary statistics for all promotions."""
        try:
            summary = PromotionManager.get_promotion_summary()
            return {"success": True, "data": summary}
        except Exception as e:
            logger.error(f"Error getting promotion summary: {str(e)}")
            return {"success": False, "error": f"Summary error: {str(e)}"}

    # ============= High-Level Methods for Views =============

    def get_all_promotions(
        self,
        filters: Optional[Dict] = None,
        limit: int = 20,
        last_evaluated_key: Optional[Dict] = None,
    ) -> Dict:
        """
        High-level method that maps frontend filters to backend parameters.
        Returns paginated list with next_page_token.
        Expected filters:
            - status (str)
            - target_type (str)
            - seasonal_tag (str)
            - include_deleted (bool)
            - search_query (str) - not implemented; could be added later.
        """
        filters = filters or {}
        status = filters.get("status")
        target_type = filters.get("target_type")
        seasonal_tag = filters.get("seasonal_tag")
        include_deleted = filters.get("include_deleted", False)

        try:
            promotions, next_token = self.get_promotions(
                status=status,
                target_type=target_type,
                seasonal_tag=seasonal_tag,
                include_deleted=include_deleted,
                limit=limit,
                last_evaluated_key=last_evaluated_key,
            )
            return {
                "success": True,
                "data": {
                    "promotions": promotions,
                    "next_page_token": next_token,
                    "limit": limit,
                }
            }
        except Exception as e:
            logger.error(f"Error in get_all_promotions: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_active_promotions(self) -> Dict:
        """Return currently active promotions."""
        try:
            active = Promotion.get_active_promotions()
            return {"success": True, "data": [p.to_dict() for p in active]}
        except Exception as e:
            logger.error(f"Error getting active promotions: {str(e)}")
            return {"success": False, "error": str(e)}

    def apply_promotion_to_order(self, order_data: Dict, customer_id: str) -> Dict:
        """
        Calculate best discount and record usage for applied promotions.
        Expected order_data: {"total_amount": float, "items": list, "order_id": str (optional)}
        """
        try:
            total = order_data["total_amount"]
            # For a real implementation, you would pass item-level targeting.
            # Here we simplify and pass None for target filters.
            best = PromotionManager.calculate_best_discount(total)

            if best["total_discount"] > 0 and best.get("used_promotions"):
                order_id = order_data.get("order_id", f"temp_{datetime.utcnow().timestamp()}")
                for promo_info in best["used_promotions"]:
                    result = self.increment_usage(
                        promotion_id=promo_info["promotion_id"],
                        order_id=order_id,
                        discount_amount=promo_info["discount_amount"],
                        transaction_amount=total,
                        user_id=customer_id,
                    )
                    if not result["success"]:
                        logger.warning(f"Failed to record usage for promotion {promo_info['promotion_id']}: {result['error']}")
                        # Decide whether to fail the whole operation or continue.
            return {"success": True, "data": best}
        except Exception as e:
            logger.error(f"Error applying promotion to order: {str(e)}")
            return {"success": False, "error": str(e)}

    def expire_promotion(self, promotion_id: str) -> Dict:
        """Mark promotion as expired (deactivate with reason)."""
        return self.deactivate_promotion(promotion_id, reason="Expired manually")

    def get_promotion_statistics(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict:
        """Return aggregated stats; fallback to effectiveness report."""
        if start_date and end_date:
            days = (end_date - start_date).days
        else:
            days = 30
        return self.get_effectiveness_report(days)

    def get_promotion_audit_history(self, promotion_id: str, limit: int = 50) -> Dict:
        """Extract audit log from promotion item."""
        try:
            promo = Promotion.get_by_id(promotion_id, include_deleted=True)
            if not promo:
                return {"success": False, "error": "Promotion not found"}
            # Convert audit log items to dicts (assuming they have .attribute_values)
            audit = [item.attribute_values for item in promo.audit_log[-limit:]]
            return {"success": True, "data": {"audit": audit}}
        except Exception as e:
            logger.error(f"Error fetching audit history: {str(e)}")
            return {"success": False, "error": str(e)}

    def restore_promotion(self, promotion_id: str) -> Dict:
        """Restore soft‑deleted promotion."""
        try:
            promo = Promotion.get_by_id(promotion_id, include_deleted=True)
            if not promo:
                return {"success": False, "error": "Promotion not found"}
            promo.restore(restored_by=self.current_user)
            return {"success": True, "data": promo.to_dict()}
        except Exception as e:
            logger.error(f"Error restoring promotion: {str(e)}")
            return {"success": False, "error": str(e)}

    def hard_delete_promotion(self, promotion_id: str, confirmation_token: str) -> Dict:
        """
        Permanently delete – use with extreme caution.
        Confirmation token must equal "PERMANENT_DELETE_CONFIRMED".
        """
        if confirmation_token != "PERMANENT_DELETE_CONFIRMED":
            return {"success": False, "error": "Confirmation required"}
        try:
            promo = Promotion.get_by_id(promotion_id, include_deleted=True)
            if not promo:
                return {"success": False, "error": "Promotion not found"}
            promo.delete()  # PynamoDB hard delete
            return {"success": True, "data": {"message": "Promotion permanently deleted"}}
        except Exception as e:
            logger.error(f"Error hard-deleting promotion: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_deleted_promotions(self, limit: int = 20, last_evaluated_key: Optional[Dict] = None) -> Dict:
        """Return only soft‑deleted promotions."""
        return self.get_all_promotions(
            filters={"include_deleted": True},
            limit=limit,
            last_evaluated_key=last_evaluated_key,
        )