from datetime import datetime, timedelta
from ...database import db_manager
from ..product_service import ProductService
from ..batch_service import BatchService
from notifications.services import notification_service
import logging
import math
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class OnlineTransactionService:
    """
    Online order transaction processing
    Handles online orders with FIFO batch inventory integration
    """
    
    def __init__(self):
        self.db = db_manager.get_database()
        self.online_transactions = self.db.online_transactions
        self.products_collection = self.db.products
        self.customers_collection = self.db.customers
        self.product_service = ProductService()
        self.batch_service = BatchService()
        
        # Auto-cancellation settings
        self.auto_cancel_enabled = True
        self.check_interval_minutes = 5  # Check every 5 minutes
        self.expiry_minutes = 30  # Cancel after 30 minutes
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_scheduler = False
        self._last_check_time: Optional[datetime] = None
        
        # Start auto-cancellation scheduler
        self._start_auto_cancellation_scheduler()
    
    # ================================================================
    # AUTO-CANCELLATION SCHEDULER
    # ================================================================
    
    def _start_auto_cancellation_scheduler(self):
        """Start the background scheduler for automatic order cancellation"""
        if not self.auto_cancel_enabled:
            logger.info("Auto-cancellation is disabled")
            return
        
        try:
            self._stop_scheduler = False
            self._scheduler_thread = threading.Thread(
                target=self._run_auto_cancellation_loop,
                daemon=True,
                name="AutoCancelScheduler"
            )
            self._scheduler_thread.start()
            
            logger.info(f"🕒 Auto-cancellation scheduler started (checking every {self.check_interval_minutes} minutes)")
            
        except Exception as e:
            logger.error(f"Failed to start auto-cancellation scheduler: {str(e)}")
    
    def _run_auto_cancellation_loop(self):
        """Main loop for automatic order cancellation checks"""
        logger.info("🔄 Starting auto-cancellation monitoring loop...")
        
        while not self._stop_scheduler:
            try:
                # Run the check
                self.auto_cancel_expired_orders(self.expiry_minutes)
                self._last_check_time = datetime.utcnow()
                
                # Wait for next check
                time.sleep(self.check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Error in auto-cancellation loop: {str(e)}")
                # Wait before retrying
                time.sleep(60)  # 1 minute before retry
    
    def stop_auto_cancellation(self):
        """Stop the automatic cancellation scheduler"""
        self._stop_scheduler = True
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)
        
        logger.info("Auto-cancellation scheduler stopped")
    
    def restart_auto_cancellation(self, check_interval_minutes=None, expiry_minutes=None):
        """Restart the auto-cancellation scheduler with new settings"""
        self.stop_auto_cancellation()
        
        if check_interval_minutes:
            self.check_interval_minutes = check_interval_minutes
        if expiry_minutes:
            self.expiry_minutes = expiry_minutes
            
        self._start_auto_cancellation_scheduler()
        
        logger.info(f"Auto-cancellation restarted: check_interval={self.check_interval_minutes}m, expiry={self.expiry_minutes}m")
    
    def get_scheduler_status(self):
        """Get the current status of the auto-cancellation scheduler"""
        status = {
            'enabled': self.auto_cancel_enabled,
            'check_interval_minutes': self.check_interval_minutes,
            'expiry_minutes': self.expiry_minutes,
            'last_check_time': self._last_check_time,
            'scheduler_running': self._scheduler_thread and self._scheduler_thread.is_alive(),
            'stop_requested': self._stop_scheduler
        }
        
        if self._last_check_time:
            status['minutes_since_last_check'] = (datetime.utcnow() - self._last_check_time).total_seconds() / 60
        
        return status
    
    # ================================================================
    # AUTO-CANCELLATION FEATURE
    # ================================================================
    
    def get_expired_pending_orders(self, expiry_minutes=30):
        """
        Find orders that have been in 'pending' status for longer than expiry_minutes
        
        Args:
            expiry_minutes: Number of minutes before order expires (default: 30)
        
        Returns:
            List of expired order documents
        """
        try:
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(minutes=expiry_minutes)
            
            # Find orders that are:
            # - status: 'pending'
            # - created before cutoff_time
            # - not cancelled
            # - payment_status: 'pending' (not paid)
            expired_orders = list(
                self.online_transactions.find({
                    'order_status': 'pending',
                    'payment_status': 'pending',
                    'created_at': {'$lt': cutoff_time},
                    'is_cancelled': False
                })
            )
            
            logger.info(f"Found {len(expired_orders)} expired pending orders")
            return expired_orders
            
        except Exception as e:
            logger.error(f"Error finding expired orders: {str(e)}")
            return []
    
    def get_expired_unconfirmed_orders(self, expiry_minutes=30):
        """
        Find orders that have been in 'confirmed' status but not processed within expiry_minutes
        
        Args:
            expiry_minutes: Number of minutes before confirmed order expires (default: 30)
        
        Returns:
            List of expired confirmed order documents
        """
        try:
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(minutes=expiry_minutes)
            
            # Find orders that are:
            # - status: 'confirmed' 
            # - last status update before cutoff_time
            # - not cancelled
            expired_orders = list(
                self.online_transactions.find({
                    'order_status': 'confirmed',
                    'is_cancelled': False,
                    'status_history': {
                        '$elemMatch': {
                            'status': 'confirmed',
                            'timestamp': {'$lt': cutoff_time}
                        }
                    }
                })
            )
            
            logger.info(f"Found {len(expired_orders)} expired confirmed orders")
            return expired_orders
            
        except Exception as e:
            logger.error(f"Error finding expired confirmed orders: {str(e)}")
            return []
    
    def auto_cancel_expired_orders(self, expiry_minutes=30):
        """
        Automatically cancel orders that haven't been processed within the time limit
        
        Args:
            expiry_minutes: Minutes before orders expire (default: 30)
        
        Returns:
            dict: Results of auto-cancellation process
        """
        try:
            print(f"\n{'='*60}")
            print(f"🕒 AUTO-CANCELLATION: Checking for expired orders (> {expiry_minutes} minutes)")
            print(f"   Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"{'='*60}\n")
            
            cancelled_orders = []
            failed_cancellations = []
            
            # Step 1: Find expired pending orders
            print("Step 1: Checking for expired pending orders...")
            expired_pending_orders = self.get_expired_pending_orders(expiry_minutes)
            print(f"   Found {len(expired_pending_orders)} expired pending orders")
            
            # Step 2: Find expired confirmed orders
            print("Step 2: Checking for expired confirmed orders...")
            expired_confirmed_orders = self.get_expired_unconfirmed_orders(expiry_minutes)
            print(f"   Found {len(expired_confirmed_orders)} expired confirmed orders")
            
            # Combine all expired orders
            all_expired_orders = expired_pending_orders + expired_confirmed_orders
            print(f"\n📋 TOTAL EXPIRED ORDERS: {len(all_expired_orders)}")
            
            if not all_expired_orders:
                print("✅ No expired orders found. All good!")
                return {
                    'success': True,
                    'cancelled_count': 0,
                    'failed_count': 0,
                    'cancelled_orders': [],
                    'failed_orders': [],
                    'check_time': datetime.utcnow()
                }
            
            # Step 3: Process each expired order
            print(f"\nStep 3: Processing {len(all_expired_orders)} expired orders...")
            
            for order in all_expired_orders:
                order_id = order['_id']
                order_age = datetime.utcnow() - order['created_at']
                age_minutes = int(order_age.total_seconds() / 60)
                
                print(f"\n   Processing: {order_id}")
                print(f"   Age: {age_minutes} minutes")
                print(f"   Status: {order['order_status']}")
                print(f"   Customer: {order.get('customer_name', 'N/A')}")
                
                try:
                    # Cancel the order
                    cancellation_reason = f"Auto-cancelled: Order not processed within {expiry_minutes} minutes"
                    
                    self.cancel_online_order(
                        order_id=order_id,
                        cancellation_reason=cancellation_reason,
                        cancelled_by='system_auto_cancel'
                    )
                    
                    cancelled_orders.append({
                        'order_id': order_id,
                        'customer_id': order['customer_id'],
                        'age_minutes': age_minutes,
                        'previous_status': order['order_status'],
                        'cancelled_at': datetime.utcnow()
                    })
                    
                    print(f"   ✅ SUCCESS: Auto-cancelled {order_id}")
                    
                    # Send specific notification for auto-cancellation
                    self._send_auto_cancellation_notification(order_id, age_minutes)
                    
                except Exception as e:
                    error_msg = f"Failed to auto-cancel {order_id}: {str(e)}"
                    logger.error(error_msg)
                    
                    failed_cancellations.append({
                        'order_id': order_id,
                        'customer_id': order['customer_id'],
                        'error': str(e)
                    })
                    
                    print(f"   ❌ FAILED: {error_msg}")
            
            # Step 4: Summary
            print(f"\n{'='*60}")
            print(f"📊 AUTO-CANCELLATION SUMMARY")
            print(f"{'='*60}")
            print(f"✅ Successfully cancelled: {len(cancelled_orders)} orders")
            print(f"❌ Failed to cancel: {len(failed_cancellations)} orders")
            print(f"{'='*60}\n")
            
            return {
                'success': True,
                'cancelled_count': len(cancelled_orders),
                'failed_count': len(failed_cancellations),
                'cancelled_orders': cancelled_orders,
                'failed_orders': failed_cancellations,
                'check_time': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error in auto-cancellation process: {str(e)}")
            return {
                'success': False,
                'cancelled_count': 0,
                'failed_count': 0,
                'cancelled_orders': [],
                'failed_orders': [],
                'error': str(e),
                'check_time': datetime.utcnow()
            }
    
    def get_order_statistics(self):
        """
        Get statistics about orders for monitoring
        
        Returns:
            dict: Order statistics
        """
        try:
            now = datetime.utcnow()
            thirty_minutes_ago = now - timedelta(minutes=30)
            one_hour_ago = now - timedelta(hours=1)
            
            # Count orders by status
            pending_count = self.online_transactions.count_documents({
                'order_status': 'pending',
                'is_cancelled': False
            })
            
            confirmed_count = self.online_transactions.count_documents({
                'order_status': 'confirmed', 
                'is_cancelled': False
            })
            
            # Count orders at risk of expiration
            pending_at_risk = self.online_transactions.count_documents({
                'order_status': 'pending',
                'is_cancelled': False,
                'created_at': {'$lt': thirty_minutes_ago}
            })
            
            confirmed_at_risk = self.online_transactions.count_documents({
                'order_status': 'confirmed',
                'is_cancelled': False,
                'status_history': {
                    '$elemMatch': {
                        'status': 'confirmed',
                        'timestamp': {'$lt': thirty_minutes_ago}
                    }
                }
            })
            
            # Recent orders count
            recent_orders = self.online_transactions.count_documents({
                'created_at': {'$gte': one_hour_ago},
                'is_cancelled': False
            })
            
            # Auto-cancellation stats
            today_start = datetime(now.year, now.month, now.day)
            auto_cancelled_today = self.online_transactions.count_documents({
                'cancelled_by': 'system_auto_cancel',
                'cancelled_at': {'$gte': today_start}
            })
            
            return {
                'total_pending': pending_count,
                'total_confirmed': confirmed_count,
                'pending_at_risk': pending_at_risk,
                'confirmed_at_risk': confirmed_at_risk,
                'recent_orders_1h': recent_orders,
                'auto_cancelled_today': auto_cancelled_today,
                'checked_at': now,
                'scheduler_status': self.get_scheduler_status()
            }
            
        except Exception as e:
            logger.error(f"Error getting order statistics: {str(e)}")
            return {}
    
    def _send_auto_cancellation_notification(self, order_id, age_minutes):
        """
        Send notifications for auto-cancelled orders
        
        Args:
            order_id: Cancelled order ID
            age_minutes: How old the order was in minutes
        """
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                return
            
            # Notification for staff
            notification_service.create_notification(
                title="🕒 Order Auto-Cancelled",
                message=f"Order {order_id} was auto-cancelled after {age_minutes} minutes of inactivity. Stock has been restored.",
                priority="high",
                notification_type="system_alert",
                metadata={
                    'order_id': order_id,
                    'customer_id': order['customer_id'],
                    'customer_name': order.get('customer_name'),
                    'age_minutes': age_minutes,
                    'previous_status': order['order_status'],
                    'total_amount': order['total_amount'],
                    'auto_cancelled': True
                }
            )
            
            # Notification for customer
            notification_service.create_notification(
                title="Order Cancelled Due to Inactivity",
                message=f"Your order {order_id} was cancelled because it wasn't processed within 30 minutes. Please place a new order if you still wish to purchase.",
                priority="medium", 
                notification_type="order",
                metadata={
                    'order_id': order_id,
                    'order_status': 'cancelled',
                    'auto_cancelled': True,
                    'reason': 'Order not processed within time limit'
                }
            )
            
            logger.info(f"Sent auto-cancellation notifications for {order_id}")
            
        except Exception as e:
            logger.error(f"Failed to send auto-cancellation notification: {str(e)}")

    # ================================================================
    # MANUAL CHECK METHODS (for admin/management)
    # ================================================================
    
    def manual_check_expired_orders(self):
        """Manual trigger for checking expired orders (for admin use)"""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 MANUAL EXPIRED ORDERS CHECK")
            print(f"   Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"{'='*60}\n")
            
            result = self.auto_cancel_expired_orders(self.expiry_minutes)
            
            # Add scheduler status to result
            result['scheduler_status'] = self.get_scheduler_status()
            
            return result
            
        except Exception as e:
            logger.error(f"Manual check failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'scheduler_status': self.get_scheduler_status()
            }
    
    def update_auto_cancellation_settings(self, enabled=None, check_interval=None, expiry_minutes=None):
        """
        Update auto-cancellation settings
        
        Args:
            enabled: Enable/disable auto-cancellation
            check_interval: New check interval in minutes
            expiry_minutes: New expiry time in minutes
        """
        try:
            if enabled is not None:
                self.auto_cancel_enabled = enabled
                if enabled:
                    self._start_auto_cancellation_scheduler()
                else:
                    self.stop_auto_cancellation()
            
            if check_interval is not None:
                self.check_interval_minutes = check_interval
                if self.auto_cancel_enabled:
                    self.restart_auto_cancellation()
            
            if expiry_minutes is not None:
                self.expiry_minutes = expiry_minutes
            
            logger.info(f"Updated auto-cancellation settings: enabled={self.auto_cancel_enabled}, "
                       f"check_interval={self.check_interval_minutes}m, expiry={self.expiry_minutes}m")
            
            return {
                'success': True,
                'settings': {
                    'enabled': self.auto_cancel_enabled,
                    'check_interval_minutes': self.check_interval_minutes,
                    'expiry_minutes': self.expiry_minutes
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating auto-cancellation settings: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    # ================================================================
    # ID GENERATION
    # ================================================================
    
    def generate_online_order_id(self):
        """Generate sequential ONLINE-###### ID"""
        try:
            pipeline = [
                {'$match': {'_id': {'$regex': '^ONLINE-'}}},
                {'$project': {
                    'numericPart': {'$toInt': {'$substr': ['$_id', 7, -1]}}
                }},
                {'$sort': {'numericPart': -1}},
                {'$limit': 1}
            ]
            
            result = list(self.online_transactions.aggregate(pipeline))
            next_number = result[0]['numericPart'] + 1 if result else 1
            
            return f"ONLINE-{next_number:06d}"
        except Exception:
            count = self.online_transactions.count_documents({}) + 1
            return f"ONLINE-{count:06d}"
    
    # ================================================================
    # FEE CALCULATION
    # ================================================================
    
    def calculate_service_fee(self, subtotal_after_discount, delivery_fee, payment_method):
        """
        Calculate service fee based on payment method
        
        Args:
            subtotal_after_discount: Subtotal after points discount
            delivery_fee: Delivery fee amount
            payment_method: 'cod', 'gcash_paymongo', 'bank_paymongo'
        
        Returns:
            dict with fee breakdown
        """
        try:
            if payment_method == 'cod':
                return {
                    'service_fee': 15.00,
                    'breakdown': {
                        'payment_method': 'cod',
                        'base_amount': 0,
                        'paymongo_percentage_fee': 0,
                        'paymongo_fixed_fee': 0,
                        'calculated_total': 15.00,
                        'rounded_to': 15.00
                    }
                }
            
            elif payment_method in ['gcash_paymongo', 'bank_paymongo']:
                # PayMongo fee: 3.5% + ₱15
                base_amount = subtotal_after_discount + delivery_fee
                percentage_fee = base_amount * 0.035
                fixed_fee = 15.00
                calculated_fee = percentage_fee + fixed_fee
                
                # Round to nearest ₱5
                rounded_fee = math.ceil(calculated_fee / 5) * 5
                
                # Minimum ₱20 for PayMongo orders
                final_fee = max(rounded_fee, 20.00)
                
                return {
                    'service_fee': final_fee,
                    'breakdown': {
                        'payment_method': payment_method,
                        'base_amount': round(base_amount, 2),
                        'paymongo_percentage_fee': round(percentage_fee, 2),
                        'paymongo_fixed_fee': fixed_fee,
                        'calculated_total': round(calculated_fee, 2),
                        'rounded_to': final_fee
                    }
                }
            
            # Default fallback
            return {
                'service_fee': 15.00,
                'breakdown': {
                    'payment_method': payment_method,
                    'base_amount': 0,
                    'paymongo_percentage_fee': 0,
                    'paymongo_fixed_fee': 0,
                    'calculated_total': 15.00,
                    'rounded_to': 15.00
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating service fee: {str(e)}")
            return {
                'service_fee': 15.00,
                'breakdown': {}
            }
    
    def calculate_loyalty_points_earned(self, subtotal_after_discount):
        """
        Calculate loyalty points earned (20% of subtotal after discount)
        
        Args:
            subtotal_after_discount: Subtotal after points redemption
        
        Returns:
            int: Points to be earned
        """
        return int(subtotal_after_discount * 0.20)
    
    def calculate_points_discount(self, points_to_redeem):
        """
        Convert points to discount amount
        4 points = ₱1 discount
        
        Args:
            points_to_redeem: Number of points customer wants to use
        
        Returns:
            float: Discount amount in pesos
        """
        return points_to_redeem / 4.0
    
    # ================================================================
    # STOCK VALIDATION
    # ================================================================
    
    def validate_order_stock(self, items):
        """
        Validate stock availability for all items before order creation
        
        Args:
            items: list of {'product_id': str, 'quantity': int}
        
        Returns:
            dict: {
                'valid': bool,
                'errors': list,
                'stock_details': dict
            }
        """
        try:
            errors = []
            stock_details = {}
            
            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']
                
                # Get product details
                product = self.products_collection.find_one({'_id': product_id})
                
                if not product:
                    errors.append(f"Product {product_id} not found")
                    continue
                
                # Check batch availability
                batch_check = self.batch_service.check_batch_availability(
                    product_id, 
                    quantity
                )
                
                stock_details[product_id] = {
                    'product_name': product.get('product_name', 'Unknown'),
                    'requested': quantity,
                    'available': batch_check['total_stock'],
                    'sufficient': batch_check['available']
                }
                
                if not batch_check['available']:
                    errors.append(
                        f"Insufficient stock for {product.get('product_name')}. "
                        f"Available: {batch_check['total_stock']}, Requested: {quantity}"
                    )
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'stock_details': stock_details
            }
            
        except Exception as e:
            logger.error(f"Stock validation error: {str(e)}")
            return {
                'valid': False,
                'errors': [f"Stock validation failed: {str(e)}"],
                'stock_details': {}
            }
    
    # ================================================================
    # LOYALTY POINTS MANAGEMENT
    # ================================================================
    
    def validate_points_redemption(self, customer_id, points_to_redeem, subtotal):
        """
        Validate loyalty points redemption
        
        Args:
            customer_id: Customer ID
            points_to_redeem: Points customer wants to use
            subtotal: Order subtotal
        
        Returns:
            dict: {'valid': bool, 'error': str}
        """
        try:
            if points_to_redeem == 0:
                return {'valid': True, 'error': None}
            
            # Minimum redemption: 40 points (₱10)
            if points_to_redeem < 40:
                return {
                    'valid': False,
                    'error': 'Minimum redemption is 40 points (₱10)'
                }
            
            # Get customer
            customer = self.customers_collection.find_one({'_id': customer_id})
            
            if not customer:
                return {'valid': False, 'error': 'Customer not found'}
            
            # Check if customer has enough points
            available_points = customer.get('loyalty_points', 0)
            
            if available_points < points_to_redeem:
                return {
                    'valid': False,
                    'error': f'Insufficient points. Available: {available_points}, Requested: {points_to_redeem}'
                }
            
            # Check max discount: min(₱20, 20% of subtotal)
            points_discount = self.calculate_points_discount(points_to_redeem)
            max_discount = min(20, subtotal * 0.20)
            
            if points_discount > max_discount:
                max_points = int(max_discount * 4)  # Convert back to points
                return {
                    'valid': False,
                    'error': f'Points discount exceeds cap. Maximum: {max_points} points (₱{max_discount:.2f})'
                }
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            logger.error(f"Points validation error: {str(e)}")
            return {'valid': False, 'error': str(e)}
    
    def deduct_customer_points(self, customer_id, points_to_deduct, order_id):
        """
        Deduct loyalty points from customer balance
        
        Args:
            customer_id: Customer ID
            points_to_deduct: Points to deduct
            order_id: Order ID for transaction history
        """
        try:
            customer = self.customers_collection.find_one({'_id': customer_id})
            
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            current_balance = customer.get('loyalty_points', 0)
            new_balance = current_balance - points_to_deduct
            
            # Create points transaction
            points_transaction = {
                'transaction_id': order_id,
                'transaction_type': 'redeemed',
                'points': -points_to_deduct,
                'balance_before': current_balance,
                'balance_after': new_balance,
                'description': f"Redeemed {points_to_deduct} points on order {order_id}",
                'created_at': datetime.utcnow()
            }
            
            # Update customer
            self.customers_collection.update_one(
                {'_id': customer_id},
                {
                    '$set': {'loyalty_points': new_balance},
                    '$push': {'points_transactions': points_transaction}
                }
            )
            
            logger.info(f"Deducted {points_to_deduct} points from {customer_id}")
            
        except Exception as e:
            logger.error(f"Error deducting points: {str(e)}")
            raise
    
    def award_loyalty_points(self, customer_id, points_to_award, order_id, order_amount):
        """
        Award loyalty points to customer when order is completed
        
        Args:
            customer_id: Customer ID
            points_to_award: Points to award
            order_id: Order ID
            order_amount: Order subtotal after discount
        """
        try:
            customer = self.customers_collection.find_one({'_id': customer_id})
            
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            current_balance = customer.get('loyalty_points', 0)
            new_balance = current_balance + points_to_award
            
            # Points expire in 12 months
            expires_at = datetime.utcnow() + timedelta(days=365)
            
            # Create points transaction
            points_transaction = {
                'transaction_id': order_id,
                'transaction_type': 'earned',
                'points': points_to_award,
                'balance_before': current_balance,
                'balance_after': new_balance,
                'description': f"Earned from order {order_id} (₱{order_amount:.2f} purchase)",
                'earned_at': datetime.utcnow(),
                'expires_at': expires_at,
                'status': 'active',
                'created_at': datetime.utcnow()
            }
            
            # Update customer
            self.customers_collection.update_one(
                {'_id': customer_id},
                {
                    '$set': {
                        'loyalty_points': new_balance,
                        'last_purchase': datetime.utcnow()
                    },
                    '$push': {'points_transactions': points_transaction}
                }
            )
            
            logger.info(f"Awarded {points_to_award} points to {customer_id}")
            
            # Send notification
            notification_service.create_notification(
                title="Loyalty Points Earned!",
                message=f"You earned {points_to_award} points from your order! New balance: {new_balance} points (₱{new_balance/4:.2f})",
                priority="low",
                notification_type="loyalty",
                metadata={
                    'customer_id': customer_id,
                    'order_id': order_id,
                    'points_earned': points_to_award,
                    'new_balance': new_balance
                }
            )
            
        except Exception as e:
            logger.error(f"Error awarding points: {str(e)}")
            raise
    
    def refund_customer_points(self, customer_id, points_to_refund, order_id):
        """
        Refund loyalty points when order is cancelled
        
        Args:
            customer_id: Customer ID
            points_to_refund: Points to refund
            order_id: Order ID
        """
        try:
            customer = self.customers_collection.find_one({'_id': customer_id})
            
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            current_balance = customer.get('loyalty_points', 0)
            new_balance = current_balance + points_to_refund
            
            # Create points transaction
            points_transaction = {
                'transaction_id': f"{order_id}-CANCEL",
                'transaction_type': 'refunded',
                'points': points_to_refund,
                'balance_before': current_balance,
                'balance_after': new_balance,
                'description': f"Refunded {points_to_refund} points from cancelled order {order_id}",
                'created_at': datetime.utcnow()
            }
            
            # Update customer
            self.customers_collection.update_one(
                {'_id': customer_id},
                {
                    '$set': {'loyalty_points': new_balance},
                    '$push': {'points_transactions': points_transaction}
                }
            )
            
            logger.info(f"Refunded {points_to_refund} points to {customer_id}")
            
        except Exception as e:
            logger.error(f"Error refunding points: {str(e)}")
            raise
    
    # ================================================================
    # CORE ORDER OPERATIONS
    # ================================================================
    
    def create_online_order(self, order_data, customer_id):
        """
        Create a new online order with FIFO batch deduction and usage_history tracking
        
        Args:
            order_data: Dictionary containing order information
            customer_id: Customer ID (CUST-##### format)
        
        Returns:
            Dictionary with success status and created order data
        """
        try:
            # Generate order ID
            order_id = self.generate_online_order_id()
            transaction_date = datetime.utcnow()
            
            print(f"\n{'='*60}")
            print(f"🛒 Creating Online Order: {order_id}")
            print(f"   Customer: {customer_id}")
            print(f"   Items: {len(order_data.get('items', []))}")
            print(f"{'='*60}\n")
            
            # Get customer details
            customer = self.customers_collection.find_one({'_id': customer_id})
            
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")
            
            # Step 1: Validate stock availability
            print("Step 1: Validating stock...")
            stock_validation = self.validate_order_stock(order_data.get('items', []))
            
            if not stock_validation['valid']:
                raise ValueError(f"Stock validation failed: {', '.join(stock_validation['errors'])}")
            
            print("✅ Stock validation passed\n")
            
            # Step 2: Calculate initial subtotal
            print("Step 2: Calculating pricing...")
            subtotal = 0
            items_with_prices = []
            
            for item in order_data.get('items', []):
                product = self.products_collection.find_one({'_id': item['product_id']})
                
                if not product:
                    raise ValueError(f"Product {item['product_id']} not found")
                
                unit_price = product.get('selling_price', 0)
                quantity = item['quantity']
                item_subtotal = unit_price * quantity
                
                items_with_prices.append({
                    'product_id': item['product_id'],
                    'product_name': product.get('product_name'),
                    'sku': product.get('SKU'),
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'subtotal': item_subtotal,
                    'is_taxable': product.get('is_taxable', True)
                })
                
                subtotal += item_subtotal
            
            print(f"   Subtotal: ₱{subtotal:.2f}")
            
            # Step 3: Apply points discount (if any)
            points_to_redeem = order_data.get('points_to_redeem', 0)
            points_discount = 0
            
            if points_to_redeem > 0:
                print(f"Step 3: Applying points discount ({points_to_redeem} points)...")
                
                # Validate points redemption
                points_validation = self.validate_points_redemption(
                    customer_id, 
                    points_to_redeem, 
                    subtotal
                )
                
                if not points_validation['valid']:
                    raise ValueError(points_validation['error'])
                
                points_discount = self.calculate_points_discount(points_to_redeem)
                
                # Deduct points from customer
                self.deduct_customer_points(customer_id, points_to_redeem, order_id)
                
                print(f"   Points discount: ₱{points_discount:.2f}")
            
            subtotal_after_discount = subtotal - points_discount
            print(f"   Subtotal after discount: ₱{subtotal_after_discount:.2f}")
            
            # Step 4: Calculate fees
            delivery_fee = 50.00
            payment_method = order_data.get('payment_method', 'cod')
            service_fee_data = self.calculate_service_fee(
                subtotal_after_discount,
                delivery_fee,
                payment_method
            )
            service_fee = service_fee_data['service_fee']
            
            print(f"   Delivery fee: ₱{delivery_fee:.2f}")
            print(f"   Service fee: ₱{service_fee:.2f}")
            
            # Step 5: Calculate total
            total_amount = subtotal_after_discount + delivery_fee + service_fee
            print(f"   TOTAL: ₱{total_amount:.2f}\n")
            
            # Step 6: Calculate loyalty points to be earned
            loyalty_points_earned = self.calculate_loyalty_points_earned(subtotal_after_discount)
            print(f"Step 4: Loyalty points to earn: {loyalty_points_earned} points\n")
            
            # Step 7: Build order record
            print("Step 5: Processing order items with FIFO...\n")
            
            order_record = {
                '_id': order_id,
                'customer_id': customer_id,
                'customer_name': customer.get('full_name'),
                'customer_email': customer.get('email'),
                'customer_phone': customer.get('phone'),
                'transaction_date': transaction_date,
                'delivery_address': order_data.get('delivery_address', {}),
                'items': [],  # Will be populated with batch tracking
                'subtotal': round(subtotal, 2),
                'points_redeemed': points_to_redeem,
                'points_discount': round(points_discount, 2),
                'subtotal_after_discount': round(subtotal_after_discount, 2),
                'delivery_fee': delivery_fee,
                'service_fee': service_fee,
                'service_fee_breakdown': service_fee_data['breakdown'],
                'total_amount': round(total_amount, 2),
                'payment_method': payment_method,
                'payment_status': 'pending',
                'payment_reference': None,
                'payment_confirmed_by': None,
                'payment_confirmed_at': None,
                'paymongo_payment_id': None,
                'order_status': 'pending',
                'status_history': [
                    {
                        'status': 'pending',
                        'timestamp': transaction_date,
                        'updated_by': 'system',
                        'notes': 'Order created'
                    }
                ],
                'loyalty_points_earned': loyalty_points_earned,
                'loyalty_points_used': points_to_redeem,
                'points_awarded': False,
                'is_cancelled': False,
                'cancellation_reason': None,
                'cancelled_by': None,
                'cancelled_at': None,
                'stock_restored': False,
                'points_refunded': False,
                'prepared_by': None,
                'ready_at': None,
                'delivered_at': None,
                'delivery_person': None,
                'source': 'online',
                'created_at': transaction_date,
                'updated_at': transaction_date,
                'notes': order_data.get('notes', '')
            }
            
            # Step 8: Process each item with FIFO batch deduction
            for item in items_with_prices:
                product_id = item['product_id']
                quantity_needed = item['quantity']
                
                print(f"📦 Processing: {item['product_name']} ({product_id}) x{quantity_needed}")
                
                # ✅ PREPARE TRANSACTION INFO FOR USAGE_HISTORY
                transaction_info = {
                    'transaction_id': order_id,
                    'adjusted_by': customer_id,
                    'source': 'online_order'
                }
                
                # ✅ Deduct from batches using FIFO with transaction tracking
                batch_deductions = self.batch_service.deduct_stock_fifo(
                    product_id,
                    quantity_needed,
                    transaction_date,
                    transaction_info=transaction_info  # ✅ Pass transaction info
                )
                
                # Add batches_used to item
                item['batches_used'] = batch_deductions
                
                # Add item to order
                order_record['items'].append(item)
                
                # Update product total stock (cached)
                product = self.products_collection.find_one({'_id': product_id})
                new_total_stock = product.get('stock', 0) - quantity_needed
                
                self.products_collection.update_one(
                    {'_id': product_id},
                    {
                        '$set': {
                            'stock': new_total_stock,
                            'updated_at': transaction_date
                        }
                    }
                )
                
                print(f"   ✅ Stock updated: {product.get('stock')} → {new_total_stock}\n")
            
            # Step 9: Insert order record
            self.online_transactions.insert_one(order_record)
            
            # Step 10: Auto-confirm COD orders
            if payment_method == 'cod':
                print("Step 6: Auto-confirming COD order...")
                self.update_order_status(order_id, 'confirmed', 'system')
            
            print(f"{'='*60}")
            print(f"✅ Online order created successfully: {order_id}")
            print(f"{'='*60}\n")
            
            # Step 11: Send notifications
            self._send_order_notification('new_order_created', order_id)
            
            return {
                'success': True,
                'message': 'Order created successfully',
                'data': {
                    'order': order_record,
                    'order_id': order_id,
                    'auto_confirmed': payment_method == 'cod'
                }
            }
            
        except ValueError as e:
            print(f"❌ Validation error: {str(e)}")
            
            # Rollback: Refund points if they were deducted
            if 'points_to_redeem' in locals() and points_to_redeem > 0:
                try:
                    self.refund_customer_points(customer_id, points_to_redeem, f"{order_id}-ROLLBACK")
                except:
                    pass
            
            raise
            
        except Exception as e:
            print(f"❌ Unexpected error creating online order: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Rollback: Refund points if they were deducted
            if 'points_to_redeem' in locals() and points_to_redeem > 0:
                try:
                    self.refund_customer_points(customer_id, points_to_redeem, f"{order_id}-ROLLBACK")
                except:
                    pass
            
            raise Exception(f"Error creating online order: {str(e)}")
    
    # ================================================================
    # ORDER CANCELLATION
    # ================================================================
    
    def cancel_online_order(self, order_id, cancellation_reason, cancelled_by):
        """
        Cancel order and restore stock to batches with usage_history tracking
        
        Args:
            order_id: Order ID (ONLINE-######)
            cancellation_reason: Reason for cancellation
            cancelled_by: Who cancelled (CUST-#### or USER-####)
        
        Returns:
            Updated order document
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚫 Cancelling Order: {order_id}")
            print(f"   Cancelled by: {cancelled_by}")
            print(f"   Reason: {cancellation_reason}")
            print(f"{'='*60}\n")
            
            # Step 1: Get and validate order
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order.get('is_cancelled'):
                raise ValueError(f"Order {order_id} is already cancelled")
            
            current_status = order['order_status']
            
            if current_status not in ['pending', 'confirmed']:
                raise ValueError(
                    f"Cannot cancel order in '{current_status}' status. "
                    f"Orders can only be cancelled when 'pending' or 'confirmed'."
                )
            
            print("✅ Order validation passed\n")
            
            # ✅ PREPARE TRANSACTION INFO FOR RESTORATION
            transaction_info = {
                'transaction_id': f"{order_id}-CANCEL",
                'adjusted_by': cancelled_by,
                'reason': f"Order cancelled: {cancellation_reason}"
            }
            
            # Step 2: Restore stock to batches
            print("Step 1: Restoring stock to batches...\n")
            
            for item in order.get('items', []):
                if 'batches_used' in item:
                    print(f"   Restoring: {item['product_name']} x{item['quantity']}")
                    
                    # ✅ Restore to batches using batch service with tracking
                    self.batch_service.restore_stock_to_batches(
                        item['batches_used'],
                        datetime.utcnow(),
                        transaction_info=transaction_info  # ✅ Pass transaction info
                    )
                    
                    # Update product total stock
                    product = self.products_collection.find_one({'_id': item['product_id']})
                    
                    if product:
                        new_stock = product.get('stock', 0) + item['quantity']
                        
                        self.products_collection.update_one(
                            {'_id': item['product_id']},
                            {
                                '$set': {
                                    'stock': new_stock,
                                    'updated_at': datetime.utcnow()
                                }
                            }
                        )
                        
                        print(f"      Stock restored: {product.get('stock')} → {new_stock}")
            
            print("\n✅ Stock restored to batches\n")
            
            # Step 3: Refund loyalty points if used
            points_refunded = False
            
            if order.get('loyalty_points_used', 0) > 0:
                print(f"Step 2: Refunding {order['loyalty_points_used']} loyalty points...")
                
                self.refund_customer_points(
                    order['customer_id'],
                    order['loyalty_points_used'],
                    order_id
                )
                
                points_refunded = True
                print("✅ Points refunded\n")
            
            # Step 4: Update payment status if paid
            payment_status_update = {}
            
            if order['payment_status'] == 'paid':
                payment_status_update['payment_status'] = 'refunded'
                print("Step 3: Marking payment for refund...")
                print("✅ Payment marked for refund\n")
            
            # Step 5: Update order to cancelled
            print("Step 4: Updating order status...")
            
            cancellation_data = {
                'is_cancelled': True,
                'order_status': 'cancelled',
                'cancellation_reason': cancellation_reason,
                'cancelled_by': cancelled_by,
                'cancelled_at': datetime.utcnow(),
                'stock_restored': True,
                'points_refunded': points_refunded,
                'updated_at': datetime.utcnow(),
                **payment_status_update
            }
            
            status_history_entry = {
                'status': 'cancelled',
                'timestamp': datetime.utcnow(),
                'updated_by': cancelled_by,
                'notes': cancellation_reason
            }
            
            self.online_transactions.update_one(
                {'_id': order_id},
                {
                    '$set': cancellation_data,
                    '$push': {'status_history': status_history_entry}
                }
            )
            
            print("✅ Order cancelled successfully\n")
            
            print(f"{'='*60}")
            print(f"✅ Order {order_id} cancelled successfully")
            print(f"{'='*60}\n")
            
            # Step 6: Send notifications
            self._send_order_notification('order_cancelled', order_id)
            
            return self.get_order_by_id(order_id)
            
        except Exception as e:
            logger.error(f"❌ Cancel order failed: {str(e)}")
            raise
    
    # ================================================================
    # ORDER STATUS MANAGEMENT
    # ================================================================
    
    def update_order_status(self, order_id, new_status, updated_by, notes=''):
        """
        Update order status with validation
        
        Args:
            order_id: Order ID
            new_status: New status (confirmed, processing, on_the_way, completed)
            updated_by: User ID who updated (USER-#### or 'system')
            notes: Optional notes
        
        Returns:
            Updated order document
        """
        try:
            # Get current order
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order.get('is_cancelled'):
                raise ValueError(f"Cannot update cancelled order")
            
            current_status = order['order_status']
            
            # Validate transition
            ALLOWED_TRANSITIONS = {
                'pending': ['confirmed', 'cancelled'],
                'confirmed': ['processing', 'cancelled'],
                'processing': ['on_the_way'],
                'on_the_way': ['completed'],
                'completed': [],
                'cancelled': []
            }
            
            if new_status not in ALLOWED_TRANSITIONS[current_status]:
                raise ValueError(
                    f"Cannot transition from '{current_status}' to '{new_status}'. "
                    f"Allowed transitions: {ALLOWED_TRANSITIONS[current_status]}"
                )
            
            print(f"\n{'='*60}")
            print(f"🔄 Updating order status: {order_id}")
            print(f"   {current_status} → {new_status}")
            print(f"   Updated by: {updated_by}")
            print(f"{'='*60}\n")
            
            # Prepare update data
            update_data = {
                'order_status': new_status,
                'updated_at': datetime.utcnow()
            }
            
            # Auto-transitions and special handling
            if new_status == 'confirmed':
                # Validate stock still available
                print("Validating stock availability...")
                
                for item in order['items']:
                    stock_check = self.batch_service.check_batch_availability(
                        item['product_id'],
                        item['quantity']
                    )
                    
                    if not stock_check['available']:
                        raise ValueError(
                            f"Insufficient stock for {item['product_name']}. "
                            f"Available: {stock_check['total_stock']}, Needed: {item['quantity']}"
                        )
                
                print("✅ Stock validation passed")
            
            elif new_status == 'processing':
                update_data['prepared_by'] = updated_by
                print(f"Order preparation started by {updated_by}")
            
            elif new_status == 'on_the_way':
                update_data['ready_at'] = datetime.utcnow()
                print("Order marked as ready for delivery")
            
            elif new_status == 'completed':
                update_data['delivered_at'] = datetime.utcnow()
                
                # COD: Mark payment as received
                if order['payment_method'] == 'cod':
                    update_data['payment_status'] = 'paid'
                    print("COD payment marked as received")
                
                # Award loyalty points (if not already awarded)
                if not order.get('points_awarded', False):
                    print(f"Awarding {order['loyalty_points_earned']} loyalty points...")
                    
                    self.award_loyalty_points(
                        order['customer_id'],
                        order['loyalty_points_earned'],
                        order_id,
                        order['subtotal_after_discount']
                    )
                    
                    update_data['points_awarded'] = True
                    print("✅ Points awarded")
            
            # Add to status history
            status_history_entry = {
                'status': new_status,
                'timestamp': datetime.utcnow(),
                'updated_by': updated_by,
                'notes': notes
            }
            
            # Update order
            self.online_transactions.update_one(
                {'_id': order_id},
                {
                    '$set': update_data,
                    '$push': {'status_history': status_history_entry}
                }
            )
            
            print(f"\n{'='*60}")
            print(f"✅ Order status updated: {order_id} → {new_status}")
            print(f"{'='*60}\n")
            
            # Send notifications
            self._send_order_notification(f'order_{new_status}', order_id)
            
            return self.get_order_by_id(order_id)
            
        except Exception as e:
            logger.error(f"❌ Update status failed: {str(e)}")
            raise
    
    def update_payment_status(self, order_id, payment_status, payment_reference=None, confirmed_by=None):
        """
        Update payment status (for PayMongo confirmations)
        
        Args:
            order_id: Order ID
            payment_status: 'paid', 'failed', 'refunded'
            payment_reference: PayMongo transaction reference (optional)
            confirmed_by: Staff user ID who confirmed payment
        
        Returns:
            Updated order document
        """
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            print(f"\n{'='*60}")
            print(f"💳 Updating payment status: {order_id}")
            print(f"   Payment status: {payment_status}")
            print(f"   Reference: {payment_reference}")
            print(f"{'='*60}\n")
            
            update_data = {
                'payment_status': payment_status,
                'updated_at': datetime.utcnow()
            }
            
            if payment_reference:
                update_data['payment_reference'] = payment_reference
            
            if confirmed_by:
                update_data['payment_confirmed_by'] = confirmed_by
                update_data['payment_confirmed_at'] = datetime.utcnow()
            
            # Update order
            self.online_transactions.update_one(
                {'_id': order_id},
                {'$set': update_data}
            )
            
            # Auto-confirm order if payment successful and order is pending
            if payment_status == 'paid' and order['order_status'] == 'pending':
                print("Payment confirmed! Auto-confirming order...")
                self.update_order_status(order_id, 'confirmed', confirmed_by or 'system', 'Payment confirmed')
            
            print(f"✅ Payment status updated: {payment_status}\n")
            
            # Send notification
            if payment_status == 'paid':
                self._send_order_notification('payment_confirmed', order_id)
            
            return self.get_order_by_id(order_id)
            
        except Exception as e:
            logger.error(f"❌ Update payment failed: {str(e)}")
            raise
    
    def mark_ready_for_delivery(self, order_id, prepared_by, delivery_notes=''):
        """
        Shortcut to mark order as ready for delivery (processing → on_the_way)
        
        Args:
            order_id: Order ID
            prepared_by: Staff user ID
            delivery_notes: Optional delivery notes
        
        Returns:
            Updated order document
        """
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order['order_status'] != 'processing':
                raise ValueError(
                    f"Order must be in 'processing' status to mark ready for delivery. "
                    f"Current status: {order['order_status']}"
                )
            
            # Update status to on_the_way
            notes = f"Order packed and ready for delivery. {delivery_notes}".strip()
            
            return self.update_order_status(order_id, 'on_the_way', prepared_by, notes)
            
        except Exception as e:
            logger.error(f"❌ Mark ready for delivery failed: {str(e)}")
            raise
    
    def complete_order(self, order_id, completed_by, delivery_person=None):
        """
        Mark order as completed (delivered)
        
        Args:
            order_id: Order ID
            completed_by: Staff user ID
            delivery_person: Name of delivery person (optional)
        
        Returns:
            Updated order document
        """
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            if order['order_status'] != 'on_the_way':
                raise ValueError(
                    f"Order must be 'on_the_way' to complete. "
                    f"Current status: {order['order_status']}"
                )
            
            # Add delivery person info if provided
            if delivery_person:
                self.online_transactions.update_one(
                    {'_id': order_id},
                    {'$set': {'delivery_person': delivery_person}}
                )
            
            notes = f"Order delivered successfully"
            if delivery_person:
                notes += f" by {delivery_person}"
            
            return self.update_order_status(order_id, 'completed', completed_by, notes)
            
        except Exception as e:
            logger.error(f"❌ Complete order failed: {str(e)}")
            raise
    
    # ================================================================
    # ORDER RETRIEVAL
    # ================================================================
    
    def get_order_by_id(self, order_id):
        """Get single order by ID"""
        try:
            order = self.online_transactions.find_one({'_id': order_id})
            return order
            
        except Exception as e:
            logger.error(f"Error fetching order: {str(e)}")
            return None
    
    def get_customer_orders(self, customer_id, status=None, limit=50):
        """
        Get all orders for a customer
        
        Args:
            customer_id: Customer ID
            status: Filter by status (optional)
            limit: Maximum number of orders to return
        
        Returns:
            List of orders
        """
        try:
            query = {'customer_id': customer_id}
            
            if status:
                query['order_status'] = status
            
            orders = list(
                self.online_transactions
                .find(query)
                .sort('transaction_date', -1)
                .limit(limit)
            )
            
            return orders
            
        except Exception as e:
            logger.error(f"Error fetching customer orders: {str(e)}")
            return []
    
    def get_all_orders(self, filters=None, limit=100):
        """
        Get all orders with optional filters (for staff)
        
        Args:
            filters: {
                'status': 'pending',
                'payment_status': 'paid',
                'start_date': datetime,
                'end_date': datetime,
                'customer_id': 'CUST-####'
            }
            limit: Maximum orders to return
        
        Returns:
            List of orders
        """
        try:
            query = {}
            
            if filters:
                # Status filter
                if filters.get('status'):
                    query['order_status'] = filters['status']
                
                # Payment status filter
                if filters.get('payment_status'):
                    query['payment_status'] = filters['payment_status']
                
                # Customer filter
                if filters.get('customer_id'):
                    query['customer_id'] = filters['customer_id']
                
                # Date range filter
                if filters.get('start_date') or filters.get('end_date'):
                    query['transaction_date'] = {}
                    
                    if filters.get('start_date'):
                        query['transaction_date']['$gte'] = filters['start_date']
                    
                    if filters.get('end_date'):
                        query['transaction_date']['$lte'] = filters['end_date']
            
            orders = list(
                self.online_transactions
                .find(query)
                .sort('transaction_date', -1)
                .limit(limit)
            )
            
            return orders
            
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}")
            return []
    
    def get_orders_by_status(self, status, limit=50):
        """Get orders by specific status"""
        try:
            orders = list(
                self.online_transactions
                .find({'order_status': status})
                .sort('transaction_date', -1)
                .limit(limit)
            )
            
            return orders
            
        except Exception as e:
            logger.error(f"Error fetching orders by status: {str(e)}")
            return []
    
    def get_pending_orders(self):
        """Get all pending orders (needs payment confirmation)"""
        return self.get_orders_by_status('pending')
    
    def get_processing_orders(self):
        """Get all orders being prepared"""
        return self.get_orders_by_status('processing')
    
    # ================================================================
    # REPORTING & ANALYTICS
    # ================================================================
    
    def get_order_summary(self, start_date, end_date):
        """
        Get order summary for date range
        
        Returns:
            {
                'total_orders': int,
                'total_revenue': float,
                'completed_orders': int,
                'cancelled_orders': int,
                'avg_order_value': float,
                'payment_method_breakdown': {...}
            }
        """
        try:
            query = {
                'transaction_date': {
                    '$gte': start_date,
                    '$lte': end_date
                }
            }
            
            # Aggregation pipeline
            pipeline = [
                {'$match': query},
                {'$group': {
                    '_id': None,
                    'total_orders': {'$sum': 1},
                    'total_revenue': {
                        '$sum': {
                            '$cond': [
                                {'$eq': ['$order_status', 'completed']},
                                '$total_amount',
                                0
                            ]
                        }
                    },
                    'completed_orders': {
                        '$sum': {
                            '$cond': [{'$eq': ['$order_status', 'completed']}, 1, 0]
                        }
                    },
                    'cancelled_orders': {
                        '$sum': {
                            '$cond': [{'$eq': ['$is_cancelled', True]}, 1, 0]
                        }
                    },
                    'avg_order_value': {'$avg': '$total_amount'},
                    'orders': {'$push': '$$ROOT'}
                }}
            ]
            
            result = list(self.online_transactions.aggregate(pipeline))
            
            if not result:
                return {
                    'total_orders': 0,
                    'total_revenue': 0,
                    'completed_orders': 0,
                    'cancelled_orders': 0,
                    'avg_order_value': 0,
                    'payment_method_breakdown': {}
                }
            
            summary = result[0]
            
            # Calculate payment method breakdown
            payment_breakdown = {}
            for order in summary.get('orders', []):
                method = order.get('payment_method', 'unknown')
                amount = order.get('total_amount', 0)
                
                if order.get('order_status') == 'completed':
                    payment_breakdown[method] = payment_breakdown.get(method, 0) + amount
            
            return {
                'total_orders': summary.get('total_orders', 0),
                'total_revenue': round(summary.get('total_revenue', 0), 2),
                'completed_orders': summary.get('completed_orders', 0),
                'cancelled_orders': summary.get('cancelled_orders', 0),
                'avg_order_value': round(summary.get('avg_order_value', 0), 2),
                'payment_method_breakdown': payment_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error getting order summary: {str(e)}")
            return {}
    
    # ================================================================
    # NOTIFICATION HELPER
    # ================================================================
    
    def _send_order_notification(self, event_type, order_id):
        """Send notifications for order events"""
        try:
            order = self.get_order_by_id(order_id)
            
            if not order:
                return
            
            # Notification templates
            TEMPLATES = {
                'new_order_created': {
                    'staff': {
                        'title': 'New Online Order',
                        'message': f"New order {order_id} from {order['customer_name']} (₱{order['total_amount']:.2f})",
                        'priority': 'medium'
                    },
                    'customer': {
                        'title': 'Order Placed Successfully',
                        'message': f"Your order {order_id} has been received. Total: ₱{order['total_amount']:.2f}",
                        'priority': 'low'
                    }
                },
                'payment_confirmed': {
                    'staff': {
                        'title': 'Payment Confirmed',
                        'message': f"Payment received for order {order_id} (₱{order['total_amount']:.2f})",
                        'priority': 'medium'
                    },
                    'customer': {
                        'title': 'Payment Confirmed',
                        'message': f"Your payment has been confirmed. Order {order_id} is now being processed.",
                        'priority': 'low'
                    }
                },
                'order_confirmed': {
                    'customer': {
                        'title': 'Order Confirmed',
                        'message': f"Your order {order_id} has been confirmed and will be prepared soon.",
                        'priority': 'low'
                    }
                },
                'order_processing': {
                    'customer': {
                        'title': 'Order Being Prepared',
                        'message': f"Your order {order_id} is now being prepared for delivery.",
                        'priority': 'low'
                    }
                },
                'order_on_the_way': {
                    'customer': {
                        'title': 'Order On The Way!',
                        'message': f"Your order {order_id} is out for delivery. Get ready!",
                        'priority': 'medium'
                    }
                },
                'order_completed': {
                    'customer': {
                        'title': 'Order Delivered',
                        'message': f"Your order {order_id} has been delivered. You earned {order.get('loyalty_points_earned', 0)} points! Thank you!",
                        'priority': 'low'
                    }
                },
                'order_cancelled': {
                    'staff': {
                        'title': 'Order Cancelled',
                        'message': f"Order {order_id} has been cancelled. Reason: {order.get('cancellation_reason', 'N/A')}",
                        'priority': 'medium'
                    },
                    'customer': {
                        'title': 'Order Cancelled',
                        'message': f"Your order {order_id} has been cancelled. " + 
                                   (f"Refund will be processed shortly." if order.get('payment_status') == 'refunded' else ''),
                        'priority': 'medium'
                    }
                }
            }
            
            template = TEMPLATES.get(event_type, {})
            
            # Send to staff (backoffice notifications)
            if 'staff' in template:
                notification_service.create_notification(
                    title=template['staff']['title'],
                    message=template['staff']['message'],
                    priority=template['staff']['priority'],
                    notification_type='order',
                    metadata={
                        'order_id': order_id,
                        'customer_id': order['customer_id'],
                        'total_amount': order['total_amount'],
                        'order_status': order['order_status'],
                        'payment_status': order['payment_status']
                    }
                )
            
            # Send to customer
            if 'customer' in template:
                notification_service.create_notification(
                    title=template['customer']['title'],
                    message=template['customer']['message'],
                    priority=template['customer']['priority'],
                    notification_type='order',
                    metadata={
                        'order_id': order_id,
                        'order_status': order['order_status'],
                        'total_amount': order['total_amount']
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")