from datetime import datetime
from ..core.database_service import DatabaseService
from models.Promotions import Promotion
from pynamodb.exceptions import PynamoDBException
import logging

logger = logging.getLogger(__name__)

class PromotionService:
    def get_promotions(self, include_deleted=False):
        try:
            if include_deleted:
                promotions = Promotion.scan()
            else:
                promotions = Promotion.scan(Promotion.isDeleted == False)
            
            return [p.to_dict() for p in promotions]
        except PynamoDBException as e:
            raise Exception(f"Error getting promotions: {str(e)}")

    def get_promotion_by_id(self, promotion_id):
        try:
            return Promotion.get_by_id(promotion_id).to_dict()
        except PynamoDBException:
            return None

    def create_promotion(self, promo_data):
        try:
            # Assuming promo_data contains all necessary fields for Promotion.create_promotion
            promotion = Promotion.create_promotion(**promo_data)
            return promotion.to_dict()
        except PynamoDBException as e:
            raise Exception(f"Error creating promotion: {str(e)}")

    def update_promotion(self, promotion_id, promo_data):
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if promotion:
                promotion.update_promotion(updated_by='admin', **promo_data)
                return promotion.to_dict()
            return None
        except PynamoDBException as e:
            raise Exception(f"Error updating promotion: {str(e)}")

    def delete_promotion(self, promotion_id):
        try:
            promotion = Promotion.get_by_id(promotion_id)
            if promotion:
                promotion.soft_delete(deleted_by='admin', reason='Deleted via API')
                return True
            return False
        except PynamoDBException as e:
            raise Exception(f"Error deleting promotion: {str(e)}")

    def get_active_promotions(self, target_type=None, target_id=None):
        try:
            promotions = Promotion.get_active_promotions(target_type=target_type, target_id=target_id)
            return [p.to_dict() for p in promotions]
        except PynamoDBException as e:
            raise Exception(f"Error getting active promotions: {str(e)}")