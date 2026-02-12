from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

# Import the PynamoDB model and manager
from ...models.Promotions import (
    Promotion,
    PromotionManager,
    DiscountConfigItem,
    TargetIdItem,
    UsageHistoryItem,
    AuditLogItem,
    validate_promotion_id as model_validate_promo_id,
    create_seasonal_promotions as bulk_create_seasonal,
    activate_batch_promotions as bulk_activate,
)
# Existing services
from notifications.services import NotificationService
from .audit_service import AuditLogService
from ..services.product_service import ProductService
from ..services.category_service import CategoryService

logger = logging.getLogger(__name__)


class PromotionService:
    """
    Promotion service using DynamoDB single-table design (PynamoDB).
    Delegates core operations to the Promotion model and PromotionManager.
    """

    def __init__(self):
        """Initialize with required services."""
        self.audit_service = AuditLogService()
        self.notification_service = NotificationService()
        self.product_service = ProductService()
        self.category_service = CategoryService()

    # ------------------------------------------------------------------
    # Promotion CRUD
    # ------------------------------------------------------------------

    def create_promotion(self, promotion_data: dict) -> dict:
        """
        Create a new promotion using the model's class method.
        Returns a dict with success/error and the created promotion data.
        """
        try:
            # Validate required fields (model will also validate)
            validation = self._validate_promotion_data(promotion_data)
            if not validation['is_valid']:
                return {
                    'success': False,
                    'message': validation['message'],
                    'errors': validation['errors']
                }

            # Prepare discount_config as list of DiscountConfigItem if provided as dict
            if 'discount_config' in promotion_data:
                cfg = promotion_data['discount_config']
                if isinstance(cfg, dict):
                    # Convert single dict to list of DiscountConfigItem
                    cfg_list = []
                    promo_type = cfg.get('promotion_type')
                    # If discount value ends with %, default to percentage, else fixed
                    if not promo_type:
                        promo_type = 'percentage' if promotion_data['discount_value'].endswith('%') else 'fixed_amount'
                    cfg_list.append(DiscountConfigItem(promotion_type=promo_type))
                    promotion_data['discount_config'] = cfg_list
                # If it's already a list of dicts, PynamoDB will convert automatically
                # but we can also ensure they are DiscountConfigItem objects
                elif isinstance(cfg, list):
                    promotion_data['discount_config'] = [
                        DiscountConfigItem(**item) if isinstance(item, dict) else item
                        for item in cfg
                    ]

            # Convert target_ids list of dicts to list of TargetIdItem
            if 'target_ids' in promotion_data:
                promotion_data['target_ids'] = [
                    TargetIdItem(**t) if isinstance(t, dict) else t
                    for t in promotion_data['target_ids']
                ]

            # Convert dates to naive UTC datetime
            for field in ['start_date', 'end_date']:
                if field in promotion_data:
                    promotion_data[field] = self._ensure_naive_utc(promotion_data[field])

            # Create the promotion using the model
            promo = Promotion.create_promotion(
                name=promotion_data['name'],
                description=promotion_data.get('description', ''),
                discount_value=promotion_data['discount_value'],
                start_date=promotion_data['start_date'],
                end_date=promotion_data['end_date'],
                created_by=promotion_data.get('created_by', 'system'),
                target_type=promotion_data.get('target_type', 'all'),
                **{k: v for k, v in promotion_data.items() if k not in [
                    'name', 'description', 'discount_value', 'start_date',
                    'end_date', 'created_by', 'target_type'
                ]}
            )

            promotion_dict = promo.to_dict()

            # Log to external audit service
            try:
                self.audit_service.log_promotion_create(
                    user_data={'user_id': promotion_data.get('created_by')},
                    promotion_data=promotion_dict
                )
            except Exception as audit_error:
                logger.warning(f"Audit logging failed: {audit_error}")

            # Send notification
            self._send_promotion_notification('created', promotion_dict)

            return {
                'success': True,
                'message': f"Promotion {promotion_dict['promotion_id']} created successfully",
                'promotion_id': promotion_dict['promotion_id'],
                'promotion': promotion_dict
            }

        except ValueError as ve:
            logger.error(f"Validation error creating promotion: {ve}")
            return {'success': False, 'message': str(ve)}
        except Exception as e:
            logger.error(f"Error creating promotion: {e}")
            return {'success': False, 'message': f"Error creating promotion: {str(e)}"}

    def update_promotion(self, promotion_id: str, update_data: dict, user_id: Optional[str] = None) -> dict:
        """
        Update a promotion using the model's update_promotion method.
        """
        try:
            # Fetch existing promotion
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                self._log_audit_failure('promotion_update_failed', promotion_id, user_id,
                                        {'reason': 'promotion_not_found'})
                return {'success': False, 'message': 'Promotion not found'}

            # Additional service-level validations (e.g., cannot change type when active)
            validation = self._validate_promotion_update(update_data, promotion)
            if not validation['is_valid']:
                self._log_audit_failure('promotion_update_failed', promotion_id, user_id,
                                        {'validation_errors': validation['errors']})
                return {
                    'success': False,
                    'message': validation['message'],
                    'errors': validation['errors']
                }

            # Prepare data: convert dates to naive UTC, transform discount_config/target_ids
            update_data = self._prepare_update_data(update_data)

            # Perform the update using model's method (includes audit log & POS sync flag)
            updated_promo = promotion.update_promotion(updated_by=user_id or 'system', **update_data)

            promo_dict = updated_promo.to_dict()

            # External audit log
            changes = self._detect_promotion_changes(promotion, updated_promo)
            self.audit_service.log_action(
                action='promotion_updated',
                resource_type='promotion',
                resource_id=promo_dict['promotion_id'],
                user_id=user_id,
                changes={'field_changes': changes},
                metadata={'update_type': self._classify_update_type(changes)}
            )

            # Send notification if significant changes
            if self._requires_notification(changes):
                self._send_promotion_notification('updated', promo_dict, {'changes': changes})

            return {
                'success': True,
                'message': f"Promotion {promo_dict['promotion_id']} updated successfully",
                'changes': changes,
                'promotion': promo_dict
            }

        except Exception as e:
            logger.error(f"Error updating promotion {promotion_id}: {e}")
            self._log_audit_failure('promotion_update_error', promotion_id, user_id,
                                    {'error': str(e)})
            return {'success': False, 'message': f"Error updating promotion: {str(e)}"}

    def get_promotion_by_id(self, promotion_id: str) -> dict:
        """Retrieve a promotion by its numeric ID or full SK."""
        try:
            promotion = Promotion.get_by_id(promotion_id, include_deleted=False)
            if not promotion:
                return {'success': False, 'message': 'Promotion not found'}

            promo_dict = promotion.to_dict()
            # Add computed fields for display (some already in to_dict)
            return {
                'success': True,
                'promotion': promo_dict
            }
        except Exception as e:
            logger.error(f"Error getting promotion {promotion_id}: {e}")
            return {'success': False, 'message': f"Error retrieving promotion: {str(e)}"}

    # ------------------------------------------------------------------
    # Status Management
    # ------------------------------------------------------------------

    def activate_promotion(self, promotion_id: str, user_id: Optional[str] = None,
                           auto_activated: bool = False) -> dict:
        """Activate a promotion using model's activate() method."""
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                self._log_audit_failure('promotion_activation_failed', promotion_id, user_id,
                                        {'reason': 'promotion_not_found'})
                return {'success': False, 'message': 'Promotion not found'}

            if promotion.isDeleted:
                return {'success': False, 'message': 'Cannot activate deleted promotion'}

            # Model's activate will validate dates and raise ValueError if invalid
            promotion.activate(activated_by=user_id or 'system')

            promo_dict = promotion.to_dict()
            self.audit_service.log_action(
                action='promotion_activated',
                resource_type='promotion',
                resource_id=promo_dict['promotion_id'],
                user_id=user_id,
                changes={'status_change': {'from': 'inactive/draft', 'to': 'active'}},
                metadata={'auto_activated': auto_activated}
            )
            self._send_promotion_notification('activated', promo_dict)

            return {'success': True, 'message': f'Promotion {promotion_id} activated successfully'}
        except ValueError as ve:
            return {'success': False, 'message': str(ve)}
        except Exception as e:
            logger.error(f"Error activating promotion {promotion_id}: {e}")
            return {'success': False, 'message': f"Error activating promotion: {str(e)}"}

    def deactivate_promotion(self, promotion_id: str, user_id: Optional[str] = None) -> dict:
        """Deactivate a promotion using model's deactivate() method."""
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {'success': False, 'message': 'Promotion not found'}

            if promotion.status != 'active':
                return {'success': False, 'message': 'Promotion is not active'}

            promotion.deactivate(deactivated_by=user_id or 'system',
                                reason='Manual deactivation by user')

            promo_dict = promotion.to_dict()
            self.audit_service.log_action(
                action='promotion_deactivated',
                resource_type='promotion',
                resource_id=promo_dict['promotion_id'],
                user_id=user_id,
                changes={'status_change': {'from': 'active', 'to': 'deactivated'}}
            )
            self._send_promotion_notification('deactivated', promo_dict)

            return {'success': True, 'message': f'Promotion {promotion_id} deactivated successfully'}
        except Exception as e:
            logger.error(f"Error deactivating promotion {promotion_id}: {e}")
            return {'success': False, 'message': f"Error deactivating promotion: {str(e)}"}

    def expire_promotion(self, promotion_id: str, user_id: Optional[str] = None) -> dict:
        """
        Manually expire a promotion.
        (Model does not have an explicit expire method; we update status to 'expired')
        """
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {'success': False, 'message': 'Promotion not found'}

            # Direct update; model's update_promotion can handle this
            promotion.update_promotion(updated_by=user_id or 'system', status='expired')

            promo_dict = promotion.to_dict()
            usage_report = self._generate_usage_report(promotion)
            self.audit_service.log_action(
                action='promotion_expired',
                resource_type='promotion',
                resource_id=promo_dict['promotion_id'],
                user_id=user_id,
                changes={'status_change': {'from': promotion.status, 'to': 'expired'}},
                metadata={'usage_report': usage_report}
            )
            self._send_promotion_notification('expired', promo_dict, {'usage_report': usage_report})

            return {
                'success': True,
                'message': f'Promotion {promotion_id} expired successfully',
                'usage_report': usage_report
            }
        except Exception as e:
            logger.error(f"Error expiring promotion {promotion_id}: {e}")
            return {'success': False, 'message': f"Error expiring promotion: {str(e)}"}

    # ------------------------------------------------------------------
    # Delete / Restore
    # ------------------------------------------------------------------

    def delete_promotion(self, promotion_id: str, user_id: Optional[str] = None,
                         soft_delete: bool = True) -> dict:
        """Soft or hard delete a promotion using model's methods."""
        try:
            promotion = Promotion.get_by_id(promotion_id, include_deleted=False)
            if not promotion:
                return {'success': False, 'message': 'Promotion not found'}

            if soft_delete:
                promotion.soft_delete(deleted_by=user_id or 'system', reason='Manual deletion')
                action = 'promotion_soft_deleted'
                message = f'Promotion {promotion_id} soft deleted successfully'
            else:
                # Hard delete: PynamoDB delete()
                promotion.delete()
                action = 'promotion_hard_deleted'
                message = f'Promotion {promotion_id} permanently deleted'

            self.audit_service.log_action(
                action=action,
                resource_type='promotion',
                resource_id=promotion_id,
                user_id=user_id,
                changes={'deleted_promotion_data': promotion.to_simple_dict()}
            )
            return {'success': True, 'message': message}
        except Exception as e:
            logger.error(f"Error deleting promotion {promotion_id}: {e}")
            return {'success': False, 'message': f"Error deleting promotion: {str(e)}"}

    def hard_delete_promotion(self, promotion_id: str, user_id: str,
                              confirmation_token: Optional[str] = None) -> dict:
        """Permanent deletion with confirmation."""
        if confirmation_token != "PERMANENT_DELETE_CONFIRMED":
            return {'success': False, 'message': 'Hard delete requires confirmation token'}
        return self.delete_promotion(promotion_id, user_id, soft_delete=False)

    def restore_promotion(self, promotion_id: str, user_id: Optional[str] = None) -> dict:
        """Restore a soft-deleted promotion."""
        try:
            promotion = Promotion.get_by_id(promotion_id, include_deleted=True)
            if not promotion or not promotion.isDeleted:
                return {'success': False, 'message': 'Promotion not found or not deleted'}

            promotion.restore(restored_by=user_id or 'system')

            promo_dict = promotion.to_dict()
            self.audit_service.log_action(
                action='promotion_restored',
                resource_type='promotion',
                resource_id=promotion_id,
                user_id=user_id,
                changes={'status_change': {'from': 'deleted', 'to': promo_dict['status']}}
            )
            return {'success': True, 'message': f'Promotion {promotion_id} restored successfully'}
        except Exception as e:
            logger.error(f"Error restoring promotion {promotion_id}: {e}")
            return {'success': False, 'message': f"Error restoring promotion: {str(e)}"}

    def get_deleted_promotions(self, page: int = 1, limit: int = 20) -> dict:
        """List soft-deleted promotions with pagination."""
        try:
            # Query with filter condition: isDeleted == True
            # For pagination we need to handle last_evaluated_key; this is a simplified version.
            # For production, implement proper page key handling.
            all_promos = list(Promotion.query(
                "promotions",
                filter_condition=Promotion.isDeleted == True
            ))
            # Sort by updated_at descending (model doesn't have deleted_at, use updated_at)
            all_promos.sort(key=lambda p: p.updated_at, reverse=True)

            total = len(all_promos)
            start = (page - 1) * limit
            end = start + limit
            page_items = all_promos[start:end]

            return {
                'success': True,
                'promotions': [p.to_dict() for p in page_items],
                'pagination': {
                    'current_page': page,
                    'total_pages': (total + limit - 1) // limit,
                    'total_count': total,
                    'has_next': end < total,
                    'has_previous': page > 1
                }
            }
        except Exception as e:
            logger.error(f"Error getting deleted promotions: {e}")
            return {'success': False, 'message': f"Error retrieving deleted promotions: {str(e)}"}

    # ------------------------------------------------------------------
    # Listing and Filters
    # ------------------------------------------------------------------

    def get_active_promotions(self) -> dict:
        """Get all currently active promotions (via model)."""
        try:
            active = Promotion.get_active_promotions()
            return {
                'success': True,
                'promotions': [p.to_dict() for p in active],
                'count': len(active)
            }
        except Exception as e:
            logger.error(f"Error getting active promotions: {e}")
            return {'success': False, 'message': f"Error retrieving active promotions: {str(e)}"}

    def get_all_promotions(self, filters: Optional[dict] = None,
                           page: int = 1, limit: int = 20,
                           sort_by: str = 'created_at', sort_order: str = 'desc') -> dict:
        """
        List promotions with filtering and pagination.
        Uses model's get_all_promotions() and filters in memory for simplicity.
        For large datasets, consider using DynamoDB query with appropriate GSI.
        """
        try:
            include_deleted = filters.get('include_deleted', False) if filters else False
            promos = Promotion.get_all_promotions(include_deleted=include_deleted)

            # Apply in-memory filters
            filtered = self._apply_filters(promos, filters or {})

            # Sort
            reverse = sort_order.lower() == 'desc'
            if sort_by == 'created_at':
                filtered.sort(key=lambda p: p.created_at, reverse=reverse)
            elif sort_by == 'end_date':
                filtered.sort(key=lambda p: p.end_date, reverse=reverse)
            # ... add other sort fields as needed

            total = len(filtered)
            start = (page - 1) * limit
            end = start + limit
            page_items = filtered[start:end]

            return {
                'success': True,
                'promotions': [p.to_dict() for p in page_items],
                'pagination': {
                    'current_page': page,
                    'total_pages': (total + limit - 1) // limit,
                    'total_count': total,
                    'has_next': end < total,
                    'has_previous': page > 1
                }
            }
        except Exception as e:
            logger.error(f"Error getting promotions: {e}")
            return {'success': False, 'message': f"Error retrieving promotions: {str(e)}"}

    # ------------------------------------------------------------------
    # Promotion Application (Order Processing)
    # ------------------------------------------------------------------

    def apply_promotion_to_order(self, order_data: dict, customer_id: Optional[str] = None) -> dict:
        """
        Apply the best eligible promotion to an order.
        Delegates to PromotionManager.calculate_best_discount().
        """
        try:
            target_type = None
            target_id = None
            # Determine target type/id from order items (simplified)
            # This could be more sophisticated depending on business rules
            items = order_data.get('items', [])
            if items:
                # Assume we check for product-specific promotion first
                # For now, we pass None to target_type and target_id, letting the manager evaluate
                pass

            result = PromotionManager.calculate_best_discount(
                original_amount=order_data.get('total_amount', 0),
                target_type=target_type,
                target_id=target_id
            )

            if result['discount_amount'] > 0 and result['used_promotions']:
                # Apply the best promotion: increment usage
                best = result['used_promotions'][0]  # manager returns list
                promo_id = best['promotion_id']
                promotion = Promotion.get_by_id(promo_id)
                if promotion:
                    promotion.increment_usage(
                        order_id=order_data.get('order_id', 'unknown'),
                        discount_amount=best['discount_amount'],
                        transaction_amount=order_data.get('total_amount', 0),
                        branch_id=order_data.get('branch_id'),
                        user_id=customer_id,
                        pos_terminal_id=order_data.get('pos_terminal_id'),
                        items=items
                    )
                # Audit log
                self.audit_service.log_action(
                    action='promotion_applied',
                    resource_type='promotion',
                    resource_id=promo_id,
                    user_id=customer_id,
                    changes={'discount_applied': best['discount_amount'],
                             'order_summary': self._create_order_summary_for_audit(order_data)},
                    metadata={'promotion_type': best['type']}
                )
                return {
                    'success': True,
                    'discount_applied': result['discount_amount'],
                    'promotion_used': best,
                    'final_amount': result['final_amount'],
                    'message': f"Promotion {best['promotion_id']} applied"
                }
            else:
                # No applicable promotion
                self.audit_service.log_action(
                    action='promotion_application_no_match',
                    resource_type='promotion',
                    resource_id='multiple',
                    user_id=customer_id,
                    changes={'order_summary': self._create_order_summary_for_audit(order_data)},
                    metadata={'reason': 'no_applicable_promotions'}
                )
                return {
                    'success': True,
                    'discount_applied': 0.0,
                    'promotion_used': None,
                    'final_amount': order_data.get('total_amount', 0),
                    'message': 'No applicable promotions for this order'
                }
        except Exception as e:
            logger.error(f"Error applying promotion to order: {e}")
            return {'success': False, 'message': f"Error applying promotion: {str(e)}"}

    # ------------------------------------------------------------------
    # Reports & Statistics
    # ------------------------------------------------------------------

    def get_promotion_statistics(self, start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> dict:
        """Get comprehensive promotion statistics via PromotionManager."""
        try:
            # PromotionManager.get_promotion_summary() gives overall stats
            summary = PromotionManager.get_promotion_summary()
            return {
                'success': True,
                'statistics': summary
            }
        except Exception as e:
            logger.error(f"Error getting promotion statistics: {e}")
            return {'success': False, 'message': f"Error getting statistics: {str(e)}"}

    def get_promotion_effectiveness_report(self, days: int = 30) -> dict:
        """Get effectiveness report via PromotionManager."""
        try:
            report = PromotionManager.get_promotion_effectiveness_report(days=days)
            return {'success': True, **report}
        except Exception as e:
            logger.error(f"Error getting effectiveness report: {e}")
            return {'success': False, 'message': f"Error generating report: {str(e)}"}

    def get_promotion_audit_history(self, promotion_id: str, limit: int = 50) -> dict:
        """
        Get audit history from the model's embedded audit_log.
        (External audit service can also be queried if needed.)
        """
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if not promotion:
                return {'success': False, 'message': 'Promotion not found'}

            audit_entries = [
                {
                    'action': item.action,
                    'user_id': item.user_id,
                    'timestamp': item.timestamp.isoformat() if item.timestamp else None,
                    'changes': item.changes,
                    'reason': item.reason
                }
                for item in promotion.audit_log[-limit:]
            ]
            return {
                'success': True,
                'audit_history': audit_entries,
                'total_entries': len(promotion.audit_log)
            }
        except Exception as e:
            logger.error(f"Error getting promotion audit history: {e}")
            return {'success': False, 'message': f"Error retrieving audit history: {str(e)}"}

    # ------------------------------------------------------------------
    # POS Sync
    # ------------------------------------------------------------------

    def sync_promotions_to_pos(self, promotion_ids: Optional[List[str]] = None) -> dict:
        """
        Sync promotions to POS system using PromotionManager.
        """
        try:
            result = PromotionManager.sync_promotions_to_pos(promotion_ids)
            return {'success': True, **result}
        except Exception as e:
            logger.error(f"Error syncing promotions to POS: {e}")
            return {'success': False, 'message': f"POS sync failed: {str(e)}"}

    # ------------------------------------------------------------------
    # Bulk Operations
    # ------------------------------------------------------------------

    def create_seasonal_promotions(self, seasonal_data: List[Dict], created_by: str) -> dict:
        """
        Create multiple seasonal promotions at once.
        Delegates to the model's bulk creation function.
        """
        try:
            # Convert dates to naive UTC
            for data in seasonal_data:
                for field in ['start_date', 'end_date']:
                    if field in data:
                        data[field] = self._ensure_naive_utc(data[field])
            result = bulk_create_seasonal(seasonal_data, created_by)
            # Add external audit log
            self.audit_service.log_action(
                action='bulk_promotion_create',
                resource_type='promotion',
                resource_id='bulk',
                user_id=created_by,
                changes={'created_count': result['total_created']},
                metadata={'seasonal': True}
            )
            return result
        except Exception as e:
            logger.error(f"Error creating seasonal promotions: {e}")
            return {'success': False, 'message': str(e), 'errors': [str(e)]}

    def activate_batch_promotions(self, promotion_ids: List[str],
                                  activated_by: str, reason: Optional[str] = None) -> dict:
        """Activate multiple promotions at once."""
        try:
            result = bulk_activate(promotion_ids, activated_by, reason)
            self.audit_service.log_action(
                action='bulk_promotion_activate',
                resource_type='promotion',
                resource_id='bulk',
                user_id=activated_by,
                changes={'activated_count': result['total_activated']},
                metadata={'reason': reason}
            )
            return result
        except Exception as e:
            logger.error(f"Error activating batch promotions: {e}")
            return {'success': False, 'message': str(e)}

    # ------------------------------------------------------------------
    # Merge PWD & Senior Citizen Promotions
    # ------------------------------------------------------------------

    def merge_pwd_senior_citizen_promotions(self, user_id: Optional[str] = None) -> dict:
        """
        Merge all PWD and Senior Citizen promotions into one combined promotion.
        Uses model queries and creates a new promotion via model.create_promotion.
        """
        try:
            # Get all non-deleted promotions
            all_promos = Promotion.get_all_promotions(include_deleted=False)

            # Find PWD and Senior Citizen promotions by name
            pwd_keywords = ['pwd', 'person with disability']
            senior_keywords = ['senior', 'citizen', 'senior citizen']

            pwd_promos = [
                p for p in all_promos
                if any(kw in p.name.lower() for kw in pwd_keywords)
            ]
            senior_promos = [
                p for p in all_promos
                if any(kw in p.name.lower() for kw in senior_keywords)
                and p not in pwd_promos  # avoid duplicates
            ]

            all_to_merge = pwd_promos + senior_promos
            if not all_to_merge:
                return {
                    'success': False,
                    'message': 'No PWD or Senior Citizen promotions found to merge'
                }

            # Use the most recently created promotion as base
            all_to_merge.sort(key=lambda p: p.created_at, reverse=True)
            base = all_to_merge[0]

            # Aggregate totals
            total_usage = sum(p.current_usage for p in all_to_merge)
            total_revenue = sum(p.total_revenue_impact for p in all_to_merge)
            combined_history = []
            for p in all_to_merge:
                combined_history.extend(p.usage_history)

            # Prepare data for new promotion
            merged_data = {
                'name': 'PWD & Senior Citizen',
                'description': 'Combined promotion for Persons with Disabilities and Senior Citizens',
                'type': base.type,
                'discount_value': base.discount_value,
                'discount_config': base.discount_config,
                'target_type': base.target_type,
                'target_ids': base.target_ids,
                'start_date': min(p.start_date for p in all_to_merge),
                'end_date': max(p.end_date for p in all_to_merge),
                'usage_limit': base.usage_limit,
                'current_usage': total_usage,
                'total_revenue_impact': total_revenue,
                'usage_history': combined_history[-100:],  # keep last 100
                'created_by': user_id or base.created_by,
                'status': 'active' if any(p.status == 'active' for p in all_to_merge) else base.status,
                'merged_from': [p.sk for p in all_to_merge]
            }

            # Create merged promotion
            merged_promo = Promotion.create_promotion(
                name=merged_data['name'],
                description=merged_data['description'],
                discount_value=merged_data['discount_value'],
                start_date=merged_data['start_date'],
                end_date=merged_data['end_date'],
                created_by=merged_data['created_by'],
                target_type=merged_data['target_type'],
                discount_config=merged_data['discount_config'],
                target_ids=merged_data['target_ids'],
                usage_limit=merged_data['usage_limit'],
                current_usage=merged_data['current_usage'],
                total_revenue_impact=merged_data['total_revenue_impact'],
                usage_history=merged_data['usage_history'],
                status=merged_data['status'],
                **{'merged_from': merged_data['merged_from']}  # custom attribute not in model? We can add via kwargs
            )

            # Soft delete old promotions
            old_ids = []
            for promo in all_to_merge:
                promo.soft_delete(
                    deleted_by=user_id or 'system',
                    reason=f"Merged into {merged_promo.sk}"
                )
                old_ids.append(promo.sk.replace('PROMO-', ''))

            # Update sales records that reference old promotions
            # This would require a separate service call; for now we log it.
            # In a real implementation, you'd query the sales service and update references.
            logger.info(f"Merged {len(all_to_merge)} promotions into {merged_promo.sk}")

            # Audit log
            self.audit_service.log_action(
                action='promotions_merged',
                resource_type='promotion',
                resource_id=merged_promo.sk.replace('PROMO-', ''),
                user_id=user_id,
                changes={
                    'merged_promotions': old_ids,
                    'new_promotion_id': merged_promo.sk.replace('PROMO-', '')
                },
                metadata={'merge_type': 'pwd_senior_citizen'}
            )

            return {
                'success': True,
                'message': f"Successfully merged {len(all_to_merge)} promotions",
                'merged_promotion_id': merged_promo.sk.replace('PROMO-', ''),
                'merged_promotion_name': merged_promo.name,
                'old_promotion_ids': old_ids,
                'statistics': {
                    'total_usage': total_usage,
                    'total_revenue_impact': total_revenue
                }
            }

        except Exception as e:
            logger.error(f"Error merging PWD and Senior Citizen promotions: {e}")
            return {'success': False, 'message': f"Error merging promotions: {str(e)}"}

    # ------------------------------------------------------------------
    # Helper Methods (Private)
    # ------------------------------------------------------------------

    def _validate_promotion_data(self, data: dict) -> dict:
        """
        Service-level validation before calling model.create_promotion.
        Model's own validation will also run.
        """
        errors = []
        # Required fields
        required = ['name', 'type', 'discount_value', 'target_type', 'start_date', 'end_date']
        for field in required:
            if not data.get(field):
                errors.append(f"{field} is required")

        # Type validation
        valid_types = ['percentage', 'fixed_amount', 'buy_x_get_y']
        if data.get('type') not in valid_types:
            errors.append(f"type must be one of: {', '.join(valid_types)}")

        # Discount value format (model does this, but early check)
        dv = data.get('discount_value', '')
        if dv:
            if dv.endswith('%'):
                try:
                    pct = float(dv[:-1])
                    if pct <= 0 or pct > 100:
                        errors.append("Percentage must be between 0 and 100")
                except ValueError:
                    errors.append("Invalid percentage format")
            else:
                try:
                    amt = float(dv)
                    if amt <= 0:
                        errors.append("Fixed amount must be > 0")
                except ValueError:
                    errors.append("Invalid fixed amount format")

        # Target type validation
        valid_targets = ['category', 'product', 'all']
        if data.get('target_type') not in valid_targets:
            errors.append(f"target_type must be one of: {', '.join(valid_targets)}")

        # Target IDs required if not 'all'
        if data.get('target_type') in ['category', 'product']:
            target_ids = data.get('target_ids', [])
            if not target_ids:
                errors.append("target_ids required when target_type is category or product")
            else:
                # Validate existence (call external services)
                target_validation = self._validate_targets_exist(data['target_type'], target_ids)
                if not target_validation['is_valid']:
                    errors.extend(target_validation['errors'])

        # Date validation
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end:
            if end <= start:
                errors.append("end_date must be after start_date")
            # Duration limit (optional)
            if (end - start).days > 365:
                errors.append("promotion duration cannot exceed 365 days")

        # Usage limit
        if data.get('usage_limit'):
            try:
                ul = int(data['usage_limit'])
                if ul <= 0:
                    errors.append("usage_limit must be > 0")
            except (ValueError, TypeError):
                errors.append("usage_limit must be an integer")

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'message': 'Validation passed' if not errors else 'Validation failed'
        }

    def _validate_promotion_update(self, update_data: dict, promotion: Promotion) -> dict:
        """
        Service-level validation for updates.
        """
        errors = []
        # Cannot modify certain fields if promotion is active
        if promotion.status == 'active':
            restricted = ['type', 'discount_value', 'target_type', 'target_ids']
            for field in restricted:
                if field in update_data:
                    errors.append(f"Cannot modify {field} while promotion is active")

        # Discount value validation if provided
        if 'discount_value' in update_data:
            dv = update_data['discount_value']
            promo_type = update_data.get('type', promotion.type)
            if dv.endswith('%'):
                try:
                    pct = float(dv[:-1])
                    if pct <= 0 or pct > 100:
                        errors.append("Percentage must be between 0 and 100")
                except ValueError:
                    errors.append("Invalid percentage format")
            else:
                try:
                    amt = float(dv)
                    if amt <= 0:
                        errors.append("Fixed amount must be > 0")
                except ValueError:
                    errors.append("Invalid fixed amount format")

        # Date validation (if both provided)
        start = update_data.get('start_date')
        end = update_data.get('end_date')
        if start and end:
            # Ensure naive UTC
            start = self._ensure_naive_utc(start)
            end = self._ensure_naive_utc(end)
            if end <= start:
                errors.append("end_date must be after start_date")

        # Target validation
        if 'target_ids' in update_data and update_data.get('target_type', promotion.target_type) != 'all':
            target_type = update_data.get('target_type', promotion.target_type)
            target_ids = update_data['target_ids']
            target_validation = self._validate_targets_exist(target_type, target_ids)
            if not target_validation['is_valid']:
                errors.extend(target_validation['errors'])

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'message': 'Update validation passed' if not errors else 'Update validation failed'
        }

    def _validate_targets_exist(self, target_type: str, target_ids: List[str]) -> dict:
        """Check that product or category IDs exist."""
        errors = []
        if target_type == 'product':
            for pid in target_ids:
                product = self.product_service.get_product_by_id(pid)
                if not product or not product.get('success'):
                    errors.append(f"Product {pid} not found")
        elif target_type == 'category':
            for cid in target_ids:
                category = self.category_service.get_category_by_id(cid)
                if category is None:  # service returns None if not found
                    errors.append(f"Category {cid} not found")
        return {'is_valid': len(errors) == 0, 'errors': errors}

    def _prepare_update_data(self, update_data: dict) -> dict:
        """Convert complex fields to model-compatible types and dates to naive UTC."""
        data = update_data.copy()

        # Convert discount_config dict to list if needed
        if 'discount_config' in data:
            cfg = data['discount_config']
            if isinstance(cfg, dict):
                cfg_list = [DiscountConfigItem(promotion_type=cfg.get('promotion_type', 'percentage'))]
                data['discount_config'] = cfg_list
            elif isinstance(cfg, list):
                data['discount_config'] = [
                    DiscountConfigItem(**item) if isinstance(item, dict) else item
                    for item in cfg
                ]

        # Convert target_ids list of dicts to TargetIdItem list
        if 'target_ids' in data:
            data['target_ids'] = [
                TargetIdItem(**t) if isinstance(t, dict) else t
                for t in data['target_ids']
            ]

        # Normalize datetime fields
        for field in ['start_date', 'end_date']:
            if field in data:
                data[field] = self._ensure_naive_utc(data[field])

        return data

    def _ensure_naive_utc(self, dt: Any) -> datetime:
        """Convert various datetime formats to naive UTC datetime."""
        if dt is None:
            return None
        if isinstance(dt, str):
            # Try ISO format
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        if isinstance(dt, datetime):
            # Remove timezone info -> naive
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    def _apply_filters(self, promotions: List[Promotion], filters: dict) -> List[Promotion]:
        """Apply in-memory filters to a list of promotions."""
        filtered = promotions

        # Filter by status
        status = filters.get('status')
        if status and status != 'all':
            filtered = [p for p in filtered if p.status == status]

        # Filter by type
        promo_type = filters.get('type')
        if promo_type and promo_type != 'all':
            filtered = [p for p in filtered if p.type == promo_type]

        # Filter by target_type
        target_type = filters.get('target_type')
        if target_type and target_type != 'all':
            filtered = [p for p in filtered if p.target_type == target_type]

        # Filter by creator
        created_by = filters.get('created_by')
        if created_by:
            filtered = [p for p in filtered if p.created_by == created_by]

        # Search by name
        search = filters.get('search_query')
        if search:
            search_lower = search.lower()
            filtered = [p for p in filtered if search_lower in p.name.lower()]

        # Date range filter on created_at
        date_from = filters.get('date_from')
        date_to = filters.get('date_to')
        if date_from or date_to:
            date_from = self._ensure_naive_utc(date_from) if date_from else datetime.min
            date_to = self._ensure_naive_utc(date_to) if date_to else datetime.max
            filtered = [p for p in filtered if date_from <= p.created_at <= date_to]

        return filtered

    def _detect_promotion_changes(self, old: Promotion, new: Promotion) -> dict:
        """Compare two promotion instances and return dict of changed fields."""
        changes = {}
        fields = ['name', 'description', 'type', 'discount_value', 'target_type',
                  'start_date', 'end_date', 'usage_limit', 'status', 'priority',
                  'min_purchase_amount', 'stackable', 'auto_apply', 'seasonal_tag']
        for field in fields:
            old_val = getattr(old, field, None)
            new_val = getattr(new, field, None)
            if old_val != new_val:
                # Handle datetime objects
                if isinstance(old_val, datetime) and isinstance(new_val, datetime):
                    # Compare naive datetimes
                    if old_val.replace(tzinfo=None) != new_val.replace(tzinfo=None):
                        changes[field] = {
                            'from': old_val.isoformat() if old_val else None,
                            'to': new_val.isoformat() if new_val else None
                        }
                else:
                    changes[field] = {'from': old_val, 'to': new_val}
        return changes

    def _classify_update_type(self, changes: dict) -> str:
        if 'status' in changes:
            return 'status_change'
        if any(f in changes for f in ['start_date', 'end_date']):
            return 'schedule_change'
        if any(f in changes for f in ['discount_value', 'type', 'target_ids', 'target_type']):
            return 'promotion_terms_change'
        if any(f in changes for f in ['name', 'description']):
            return 'metadata_change'
        return 'general_update'

    def _requires_notification(self, changes: dict) -> bool:
        significant = ['name', 'discount_value', 'start_date', 'end_date', 'status']
        return any(f in changes for f in significant)

    def _generate_usage_report(self, promotion: Promotion) -> dict:
        """Simple usage report for a promotion."""
        return {
            'promotion_id': promotion.sk.replace('PROMO-', ''),
            'promotion_name': promotion.name,
            'total_usage': promotion.current_usage,
            'total_revenue_impact': float(promotion.total_revenue_impact or 0),
            'period': {
                'start_date': promotion.start_date.isoformat() if promotion.start_date else None,
                'end_date': promotion.end_date.isoformat() if promotion.end_date else None,
                'duration_days': (promotion.end_date - promotion.start_date).days if promotion.end_date and promotion.start_date else 0
            }
        }

    def _create_order_summary_for_audit(self, order_data: dict) -> dict:
        """Extract a summary of order data for audit logs."""
        return {
            'total_amount': order_data.get('total_amount', 0),
            'item_count': len(order_data.get('items', [])),
            'product_ids': [i.get('product_id') for i in order_data.get('items', [])],
            'categories': list(set(i.get('category_id') for i in order_data.get('items', []) if i.get('category_id')))
        }

    def _send_promotion_notification(self, action: str, promotion_data: dict,
                                     additional: Optional[dict] = None) -> None:
        """Send a notification about a promotion event."""
        titles = {
            'created': "New Promotion Created",
            'updated': "Promotion Updated",
            'activated': "Promotion Activated",
            'deactivated': "Promotion Deactivated",
            'expired': "Promotion Expired",
            'deleted': "Promotion Deleted",
            'restored': "Promotion Restored"
        }
        name = promotion_data.get('name', 'Unknown')
        pid = promotion_data.get('promotion_id', 'Unknown')
        self.notification_service.create_notification(
            title=titles.get(action, "Promotion Event"),
            message=f"Promotion '{name}' ({pid}) has been {action.replace('_', ' ')}",
            priority="high" if action in ['activated', 'expired'] else "medium",
            notification_type="system",
            metadata={
                "promotion_id": pid,
                "promotion_name": name,
                "action_type": f"promotion_{action}",
                **(additional or {})
            }
        )

    def _log_audit_failure(self, action: str, promotion_id: str, user_id: Optional[str],
                           details: dict) -> None:
        """Convenience method to log a failed action to audit service."""
        try:
            self.audit_service.log_action(
                action=action,
                resource_type='promotion',
                resource_id=promotion_id,
                user_id=user_id,
                changes=details,
                metadata={'error': True}
            )
        except Exception as e:
            logger.error(f"Failed to log audit failure: {e}")


# Import timezone for _ensure_naive_utc
from datetime import timezone