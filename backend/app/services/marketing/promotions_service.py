from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

from pynamodb.exceptions import PynamoDBException
from pynamodb.expressions.condition import Condition

from models.Promotions import Promotion, PromotionManager, UsageHistoryItem
from notifications.services import notification_service
from app.services.core.audit_service import AuditLogService

logger = logging.getLogger(__name__)


class PromotionService:
    def __init__(self, current_user: str = "system"):
        self.current_user = current_user
        self.audit_service = AuditLogService()

    def _audit_user(self):
        return {'user_id': self.current_user, 'username': self.current_user, 'source': 'service'}

    def _send_promotion_notification(self, action_type: str, promotion_name: str,
                                     promotion_id: str = None, metadata: dict = None):
        """Send promotion lifecycle notifications."""
        templates = {
            'created':      {'title': 'Promotion Created',             'message': f"Promotion '{promotion_name}' has been created",             'priority': 'medium'},
            'updated':      {'title': 'Promotion Updated',             'message': f"Promotion '{promotion_name}' has been updated",             'priority': 'medium'},
            'activated':    {'title': 'Promotion Activated',           'message': f"Promotion '{promotion_name}' is now active",                'priority': 'medium'},
            'deactivated':  {'title': 'Promotion Deactivated',         'message': f"Promotion '{promotion_name}' has been deactivated",         'priority': 'medium'},
            'soft_deleted': {'title': 'Promotion Deleted',             'message': f"Promotion '{promotion_name}' has been deleted",             'priority': 'medium'},
            'hard_deleted': {'title': 'Promotion Permanently Deleted', 'message': f"Promotion '{promotion_name}' has been permanently deleted", 'priority': 'critical'},
            'restored':     {'title': 'Promotion Restored',            'message': f"Promotion '{promotion_name}' has been restored",            'priority': 'medium'},
        }
        template = templates.get(action_type)
        if not template:
            return
        try:
            notification_service.create_notification(
                title=template['title'],
                message=template['message'],
                priority=template['priority'],
                notification_type='promotion',
                metadata={'promotion_id': promotion_id or '', 'promotion_name': promotion_name,
                          'action_type': f'promotion_{action_type}', **(metadata or {})}
            )
        except Exception as e:
            logger.error(f"Failed to send promotion notification: {e}")

    @staticmethod
    def _build_filter_condition(
        status: Optional[str] = None,
        target_type: Optional[str] = None,
        seasonal_tag: Optional[str] = None,
        type: Optional[str] = None,          # <-- NEW
        include_deleted: bool = False,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Optional[Condition]:
        conditions = []
        if not include_deleted:
            conditions.append(Promotion.isDeleted == False)
        if status:
            conditions.append(Promotion.status == status)
        if target_type:
            conditions.append(Promotion.target_type == target_type)
        if seasonal_tag:
            conditions.append(Promotion.seasonal_tag == seasonal_tag)
        if type:                              # <-- NEW: filter by discount type
            conditions.append(Promotion.type == type)
        if date_from:
            conditions.append(Promotion.end_date >= date_from)
        if date_to:
            conditions.append(Promotion.start_date <= date_to)

        if conditions:
            combined = conditions[0]
            for c in conditions[1:]:
                combined &= c
            return combined
        return None

    def get_promotions(
        self,
        status: Optional[str] = None,
        target_type: Optional[str] = None,
        seasonal_tag: Optional[str] = None,
        type: Optional[str] = None,          # NEW
        include_deleted: bool = False,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        last_evaluated_key: Optional[Dict] = None,
    ) -> Tuple[List[Dict], Optional[Dict]]:
        try:
            # Build filter WITHOUT the attribute that is the GSI range key
            if status:
                filter_cond = self._build_filter_condition(
                    target_type=target_type,
                    seasonal_tag=seasonal_tag,
                    type=type,               # NEW
                    include_deleted=include_deleted,
                    date_from=date_from,
                    date_to=date_to,
                    # status is NOT included – it's the GSI range key
                )
                query = Promotion.status_index.query(
                    "promotions",
                    Promotion.status == status,
                    filter_condition=filter_cond,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )
            elif target_type:
                filter_cond = self._build_filter_condition(
                    status=status,
                    seasonal_tag=seasonal_tag,
                    type=type,               # NEW
                    include_deleted=include_deleted,
                    date_from=date_from,
                    date_to=date_to,
                    # target_type omitted
                )
                query = Promotion.target_type_index.query(
                    "promotions",
                    Promotion.target_type == target_type,
                    filter_condition=filter_cond,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )
            elif seasonal_tag:
                filter_cond = self._build_filter_condition(
                    status=status,
                    target_type=target_type,
                    type=type,               # NEW
                    include_deleted=include_deleted,
                    date_from=date_from,
                    date_to=date_to,
                    # seasonal_tag omitted
                )
                query = Promotion.seasonal_index.query(
                    "promotions",
                    Promotion.seasonal_tag == seasonal_tag,
                    filter_condition=filter_cond,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )
            else:
                filter_cond = self._build_filter_condition(
                    status=status,
                    target_type=target_type,
                    seasonal_tag=seasonal_tag,
                    type=type,               # NEW
                    include_deleted=include_deleted,
                    date_from=date_from,
                    date_to=date_to,
                )
                query = Promotion.query(
                    "promotions",
                    filter_condition=filter_cond,
                    limit=limit,
                    last_evaluated_key=last_evaluated_key,
                )

            promotions = [p.to_dict() for p in query]
            next_token = query.last_evaluated_key
            return promotions, next_token

        except PynamoDBException as e:
            logger.error(f"Error listing promotions: {e}")
            raise Exception(f"Database error: {str(e)}")

    def _count_customer_usage(self, promotion_id: str, customer_id: str) -> int:
        """
        Count how many times a specific customer has used a promotion.
        Uses strongly consistent read to ensure the count includes recent updates.
        """
        try:
            sk = f"PROMO-{promotion_id.zfill(5)}"
            promo = Promotion.get("promotions", sk, consistent_read=True)
            if not promo or not customer_id:
                return 0
            return sum(1 for u in promo.usage_history if u.user_id == customer_id)
        except Promotion.DoesNotExist:
            return 0
        except Exception as e:
            logger.error(f"Error counting customer usage: {e}")
            return 0

    def get_all_promotions(
        self,
        filters: Optional[Dict] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict:
        filters = filters or {}
        search_query = filters.get("search_query")
        try:
            promotions, _ = self.get_promotions(
                status=filters.get("status"),
                target_type=filters.get("target_type"),
                seasonal_tag=filters.get("seasonal_tag"),
                type=filters.get("type"),              # <-- NEW
                date_from=filters.get("date_from"),
                date_to=filters.get("date_to"),
                limit=500,
            )
            if search_query:
                q = search_query.lower()
                promotions = [p for p in promotions if q in p.get('name', '').lower() or q in p.get('description', '').lower()]
            total = len(promotions)
            start = (page - 1) * limit
            end = start + limit
            paginated = promotions[start:end]
            return {
                "success": True,
                "promotions": paginated,
                "pagination": {
                    "current_page": page,
                    "total_pages": max(1, (total + limit - 1) // limit),
                    "total_items": total,
                    "items_per_page": limit,
                },
            }
        except Exception as e:
            logger.error(f"Error in get_all_promotions: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_promotion_by_id(self, promotion_id: str, include_deleted: bool = False) -> Dict:
        try:
            promo = Promotion.get_by_id(promotion_id, include_deleted)
            if promo:
                return {"success": True, "promotion": promo.to_dict()}
            return {"success": False, "error": "Promotion not found"}
        except PynamoDBException as e:
            return {"success": False, "error": "Database error"}

    def create_promotion(self, promo_data: Dict) -> Dict:
        try:
            promo_data["created_by"] = self.current_user
            if "min_purchase_amount" not in promo_data or promo_data["min_purchase_amount"] is None:
                promo_data["min_purchase_amount"] = 100
            promo = Promotion.create_promotion(**promo_data)
            promo_dict = promo.to_dict()
            self._send_promotion_notification('created', getattr(promo, 'name', promo.sk), promo.sk)
            try:
                self.audit_service.log_promotion_create(self._audit_user(), promo_dict)
            except Exception as ae:
                logger.error(f"Audit logging failed for promotion create: {ae}")
            return {"success": True, "promotion": promo_dict}
        except ValueError as ve:
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            return {"success": False, "error": "Database error"}

    def update_promotion(self, promotion_id: str, promo_data: Dict) -> Dict:
        try:
            promo = Promotion.get_by_id(promotion_id)
            if not promo:
                return {"success": False, "error": "Promotion not found"}
            old_dict = promo.to_dict()
            promo.update_promotion(updated_by=self.current_user, **promo_data)
            new_dict = promo.to_dict()
            self._send_promotion_notification('updated', getattr(promo, 'name', promo.sk), promotion_id)
            try:
                self.audit_service.log_promotion_update(self._audit_user(), promotion_id, old_dict, new_dict)
            except Exception as ae:
                logger.error(f"Audit logging failed for promotion update: {ae}")
            return {"success": True, "promotion": new_dict}
        except ValueError as ve:
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            return {"success": False, "error": "Database error"}

    def delete_promotion(self, promotion_id: str, reason: str) -> Dict:
        try:
            promo = Promotion.get_by_id(promotion_id)
            if not promo or promo.isDeleted:
                return {"success": False, "error": "Promotion not found or already deleted"}
            promo_dict = promo.to_dict()
            promo_name = getattr(promo, 'name', promo.sk)
            promo.soft_delete(deleted_by=self.current_user, reason=reason)
            self._send_promotion_notification('soft_deleted', promo_name, promotion_id)
            try:
                self.audit_service.log_promotion_soft_delete(self._audit_user(), promo_dict)
            except Exception as ae:
                logger.error(f"Audit logging failed for promotion soft delete: {ae}")
            return {"success": True, "message": "Promotion soft‑deleted"}
        except ValueError as ve:
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            return {"success": False, "error": "Database error"}

    def activate_promotion(self, promotion_id: str, reason: Optional[str] = None) -> Dict:
        try:
            promo = Promotion.get_by_id(promotion_id)
            if not promo:
                return {"success": False, "error": "Promotion not found"}
            promo_name = getattr(promo, 'name', promo.sk)
            promo.activate(self.current_user, reason)
            self._send_promotion_notification('activated', promo_name, promotion_id)
            try:
                self.audit_service.log_promotion_activate(self._audit_user(), promotion_id, promo_name)
            except Exception as ae:
                logger.error(f"Audit logging failed for promotion activate: {ae}")
            return {"success": True, "promotion": promo.to_dict()}
        except ValueError as ve:
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            return {"success": False, "error": "Database error"}

    def deactivate_promotion(self, promotion_id: str, reason: str) -> Dict:
        try:
            promo = Promotion.get_by_id(promotion_id)
            if not promo:
                return {"success": False, "error": "Promotion not found"}
            promo_name = getattr(promo, 'name', promo.sk)
            promo.deactivate(self.current_user, reason)
            self._send_promotion_notification('deactivated', promo_name, promotion_id)
            try:
                self.audit_service.log_promotion_deactivate(self._audit_user(), promotion_id, promo_name)
            except Exception as ae:
                logger.error(f"Audit logging failed for promotion deactivate: {ae}")
            return {"success": True, "promotion": promo.to_dict()}
        except ValueError as ve:
            return {"success": False, "error": str(ve)}
        except PynamoDBException as e:
            return {"success": False, "error": "Database error"}

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
        try:
            promo = Promotion.get_by_id(promotion_id)
            if not promo:
                return {"success": False, "error": "Promotion not found"}

            now = datetime.utcnow()
            history_item = UsageHistoryItem(
                order_id=order_id,
                user_id=user_id or self.current_user,
                branch_id=branch_id,
                discount_amount=discount_amount,
                transaction_amount=transaction_amount,
                timestamp=now,
                pos_terminal_id=pos_terminal_id,
                items=items,
            )

            actions = [
                Promotion.current_usage.add(1),
                Promotion.total_revenue_impact.add(discount_amount),
                Promotion.updated_at.set(now),
                Promotion.usage_history.set(Promotion.usage_history.append([history_item])),
            ]

            condition = (
                (Promotion.isDeleted == False)
                & (Promotion.status == "active")
                & (Promotion.start_date <= now)
                & (Promotion.end_date >= now)
            )
            if promo.usage_limit is not None:
                condition &= (Promotion.current_usage < promo.usage_limit)

            sk = f"PROMO-{promotion_id.zfill(5)}"
            Promotion(pk="promotions", sk=sk).update(actions=actions, condition=condition)
            promo.refresh()
            return {"success": True, "promotion": promo.to_dict()}
        except PynamoDBException as e:
            if "ConditionalCheckFailedException" in str(e):
                return {"success": False, "error": "Promotion no longer applicable or usage limit reached"}
            logger.error(f"Increment usage error: {e}")
            return {"success": False, "error": "Database error"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    def activate_batch(self, promotion_ids: List[str], reason: Optional[str] = None) -> Dict:
        from models.Promotions import activate_batch_promotions
        result = activate_batch_promotions(promotion_ids, self.current_user, reason)
        return {"success": True, "data": result}

    def create_seasonal_batch(self, seasonal_data: List[Dict]) -> Dict:
        from models.Promotions import create_seasonal_promotions
        result = create_seasonal_promotions(seasonal_data, self.current_user)
        return {"success": True, "data": result}

    def sync_to_pos(self, promotion_ids: Optional[List[str]] = None) -> Dict:
        try:
            result = PromotionManager.sync_promotions_to_pos(promotion_ids)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def mark_pos_synced(self, promotion_id: str, terminal_id: Optional[str] = None) -> Dict:
        promo = Promotion.get_by_id(promotion_id)
        if not promo:
            return {"success": False, "error": "Promotion not found"}
        try:
            promo.mark_pos_synced(terminal_id)
            return {"success": True, "promotion": promo.to_dict()}
        except PynamoDBException as e:
            return {"success": False, "error": "Database error"}

    def get_applicable_discounts(self, original_amount, target_type=None, target_id=None, branch_id=None) -> Dict:
        try:
            discounts = PromotionManager.get_effective_discounts(original_amount, target_type, target_id, branch_id)
            return {"success": True, "discounts": discounts}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_best_discount(self, original_amount, target_type=None, target_id=None, branch_id=None) -> Dict:
        try:
            best = PromotionManager.calculate_best_discount(original_amount, target_type, target_id, branch_id)
            return {"success": True, "data": best}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_effectiveness_report(self, days=30) -> Dict:
        try:
            report = PromotionManager.get_promotion_effectiveness_report(days)
            return {"success": True, "data": report}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_summary(self) -> Dict:
        try:
            summary = PromotionManager.get_promotion_summary()
            return {"success": True, "data": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_active_promotions(self) -> Dict:
        try:
            active = Promotion.get_active_promotions()
            return {"success": True, "promotions": [p.to_dict() for p in active]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =============================
    # CRITICAL: updated apply method with per‑customer limit check
    # =============================
    def apply_promotion_to_order(self, order_data: Dict, customer_id: str) -> Dict:
        """
        Calculate best discount, filter out promotions where the customer
        has reached the per‑customer limit, then record usage.
        """
        try:
            total = order_data["total_amount"]
            best = PromotionManager.calculate_best_discount(total)

            if best["total_discount"] > 0 and best.get("used_promotions"):
                order_id = order_data.get("order_id", f"temp_{datetime.utcnow().timestamp()}")
                applied_promos = []
                for promo_info in best["used_promotions"]:
                    promo_id = promo_info["promotion_id"]
                    promo = Promotion.get_by_id(promo_id)

                    # Per‑customer limit check
                    if promo and promo.per_customer_limit is not None:
                        current_usage = self._count_customer_usage(promo_id, customer_id)
                        if current_usage >= promo.per_customer_limit:
                            logger.warning(
                                f"Customer {customer_id} has already used promo {promo_id} "
                                f"{current_usage} times (limit {promo.per_customer_limit})"
                            )
                            continue   # skip this promotion

                    # If we reach here, the promotion is applicable; apply it
                    self.increment_usage(
                        promotion_id=promo_id,
                        order_id=order_id,
                        discount_amount=promo_info["discount_amount"],
                        transaction_amount=total,
                        user_id=customer_id,
                    )
                    applied_promos.append(promo_info)

                # Recalculate the actual discount based on what was applied
                if applied_promos:
                    # For simplicity, sum the discounts (the stacking logic has already
                    # been handled by calculate_best_discount; we just sum the approved ones)
                    final_discount = min(sum(p["discount_amount"] for p in applied_promos), total)
                else:
                    final_discount = 0.0

                # Return updated best with actual discount
                best["total_discount"] = final_discount
                best["used_promotions"] = applied_promos
                best["final_amount"] = total - final_discount

            return {"success": True, "data": best}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def expire_promotion(self, promotion_id: str) -> Dict:
        return self.deactivate_promotion(promotion_id, reason="Expired manually")

    def get_promotion_statistics(self, start_date=None, end_date=None) -> Dict:
        days = (end_date - start_date).days if start_date and end_date else 30
        return self.get_effectiveness_report(days)

    def get_promotion_audit_history(self, promotion_id: str, limit=50) -> Dict:
        promo = Promotion.get_by_id(promotion_id, include_deleted=True)
        if not promo:
            return {"success": False, "error": "Promotion not found"}
        audit = [item.attribute_values for item in promo.audit_log[-limit:]]
        return {"success": True, "audit": audit}

    def restore_promotion(self, promotion_id: str) -> Dict:
        promo = Promotion.get_by_id(promotion_id, include_deleted=True)
        if not promo:
            return {"success": False, "error": "Promotion not found"}
        try:
            promo_dict = promo.to_dict()
            promo.restore(self.current_user)
            self._send_promotion_notification('restored', getattr(promo, 'name', promo.sk), promotion_id)
            try:
                self.audit_service.log_promotion_restore(self._audit_user(), promo_dict)
            except Exception as ae:
                logger.error(f"Audit logging failed for promotion restore: {ae}")
            return {"success": True, "promotion": promo.to_dict()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hard_delete_promotion(self, promotion_id: str, confirmation_token: str) -> Dict:
        if confirmation_token != "PERMANENT_DELETE_CONFIRMED":
            return {"success": False, "error": "Confirmation required"}
        promo = Promotion.get_by_id(promotion_id, include_deleted=True)
        if not promo:
            return {"success": False, "error": "Promotion not found"}
        try:
            promo_dict = promo.to_dict()
            promo_name = getattr(promo, 'name', promo.sk)
            promo.delete()
            self._send_promotion_notification('hard_deleted', promo_name, promotion_id)
            try:
                self.audit_service.log_promotion_hard_delete(self._audit_user(), promo_dict)
            except Exception as ae:
                logger.error(f"Audit logging failed for promotion hard delete: {ae}")
            return {"success": True, "message": "Promotion permanently deleted"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_deleted_promotions_paginated(self, page=1, limit=20) -> Dict:
        try:
            all_deleted = list(Promotion.query(
                "promotions",
                filter_condition=Promotion.isDeleted == True,
                limit=500,
            ))
            total = len(all_deleted)
            start = (page - 1) * limit
            end = start + limit
            paginated = [p.to_dict() for p in all_deleted[start:end]]
            return {
                "success": True,
                "promotions": paginated,
                "pagination": {
                    "current_page": page,
                    "total_pages": max(1, (total + limit - 1) // limit),
                    "total_items": total,
                    "items_per_page": limit,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}