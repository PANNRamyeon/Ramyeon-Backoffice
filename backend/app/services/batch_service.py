# app/services/batch_service.py
from datetime import datetime, timedelta
from ..models.Batches import Batch, BatchManager, UsageHistoryItem, SyncLogItem, SyncLogDetailItem
from ..models.Product import Product, ProductManager
from ..models.Supplier import Supplier
from notifications.services import notification_service
import logging

logger = logging.getLogger(__name__)

class BatchService:
    def __init__(self):
        self.batch_manager = BatchManager()
        self.product_manager = ProductManager()
        
    def validate_foreign_keys(self, batch_data):
        """Validate that foreign key references exist using PynamoDB models"""
        try:
            # Validate product_id
            if 'product_id' in batch_data and batch_data['product_id']:
                product = Product.get_by_id(batch_data['product_id'])
                if not product:
                    raise ValueError(f"Product with ID {batch_data['product_id']} not found")
                # Check if product is soft deleted
                if product.isDeleted:
                    raise ValueError(f"Product with ID {batch_data['product_id']} has been deleted")
            
            # Validate supplier_id if provided
            if 'supplier_id' in batch_data and batch_data['supplier_id']:
                try:
                    # Supplier uses pk='suppliers' and sk='SUPP-001' format
                    supplier = Supplier.get("suppliers", batch_data['supplier_id'])
                    if not supplier:
                        raise ValueError(f"Supplier with ID {batch_data['supplier_id']} not found")
                except Supplier.DoesNotExist:
                    raise ValueError(f"Supplier with ID {batch_data['supplier_id']} not found")
                    
        except Exception as e:
            logger.error(f"Error validating foreign keys: {str(e)}")
            raise ValueError(f"Validation error: {str(e)}")

    def _send_batch_notification(self, action_type, product_name, additional_metadata=None):
        """Centralized notification helper for batch actions"""
        try:
            titles = {
                'created': "New Batch Added",
                'stock_received': "Stock Received",
                'stock_ordered': "Purchase Order Created",
                'activated': "Stock Activated",
                'expiry_warning': "Expiry Warning",
                'batch_expired': "Batch Expired",
                'batch_depleted': "Batch Depleted"
            }
            
            messages = {
                'created': f"New batch created for '{product_name}'",
                'stock_received': f"Stock received for '{product_name}'",
                'stock_ordered': f"Purchase order created for '{product_name}'",
                'activated': f"Stock activated for '{product_name}'",
                'expiry_warning': f"Batch expiring soon for '{product_name}'",
                'batch_expired': f"Batch expired for '{product_name}'",
                'batch_depleted': f"Batch depleted for '{product_name}'"
            }
            
            # Set priority based on action type
            if action_type in ['batch_expired', 'expiry_warning']:
                priority = "high"
                notification_type = "alert"
            elif action_type == 'batch_depleted':
                priority = "medium"
                notification_type = "alert"
            elif action_type in ['stock_ordered', 'activated']:
                priority = "low"
                notification_type = "info"
            else:
                priority = "low"
                notification_type = "system"
            
            metadata = {
                "action_type": f"batch_{action_type}",
                "product_name": product_name
            }
            
            if additional_metadata:
                metadata.update(additional_metadata)
            
            notification_service.create_notification(
                title=titles.get(action_type, "Batch Action"),
                message=messages.get(action_type, f"Batch action '{action_type}' for '{product_name}'"),
                priority=priority,
                notification_type=notification_type,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"Failed to send batch notification: {e}")

    def generate_batch_number(self, product_id):
        """Generate batch number for a product"""
        try:
            product = Product.get_by_id(product_id)
            if not product:
                return f"BATCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Format: [PRODUCT_SKU]-[DATE]-[SEQ]
            product_sku = product.SKU
            date_str = datetime.utcnow().strftime('%Y%m%d')
            
            # Get existing batches for this product today
            batches = Batch.get_by_product_id(product_id, limit=100)
            today_batches = [b for b in batches if b.batch_number and b.batch_number.startswith(f"{product_sku}-{date_str}")]
            
            sequence = len(today_batches) + 1
            return f"{product_sku}-{date_str}-{sequence:03d}"
            
        except Exception as e:
            logger.error(f"Error generating batch number: {str(e)}")
            return f"BATCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    def add_sync_log(self, source='cloud', status='synced', action='sync', details=None):
        """Helper method to create sync log entries as SyncLogDetailItem list"""
        detail_items = []
        if details:
            for detail in details:
                detail_items.append(SyncLogDetailItem(**detail))
        
        return SyncLogItem(
            last_updated=datetime.utcnow(),
            source=source,
            status=status,
            action=action,
            details=detail_items
        )

    # ================================================================
    # CORE BATCH OPERATIONS
    # ================================================================
    
    def create_batch(self, batch_data):
        """Create a new batch when stock is received using PynamoDB"""
        try:
            logger.info(f"Creating batch for product: {batch_data.get('product_id')}")
            
            # Validate foreign keys
            self.validate_foreign_keys(batch_data)
            
            # Get product info
            product = Product.get_by_id(batch_data['product_id'])
            if not product:
                raise ValueError(f"Product not found: {batch_data['product_id']}")
            
            product_name = product.product_name
            
            # Convert dates to UTC datetime
            from dateutil import parser
            
            expiry_date = None
            if 'expiry_date' in batch_data and batch_data['expiry_date']:
                try:
                    expiry_date = parser.parse(batch_data['expiry_date'])
                    if expiry_date.tzinfo is None:
                        expiry_date = expiry_date.replace(tzinfo=datetime.timezone.utc)
                except Exception as e:
                    logger.warning(f"Could not parse expiry_date: {str(e)}")
            
            expected_delivery_date = None
            if 'expected_delivery_date' in batch_data and batch_data['expected_delivery_date']:
                try:
                    expected_delivery_date = parser.parse(batch_data['expected_delivery_date'])
                    if expected_delivery_date.tzinfo is None:
                        expected_delivery_date = expected_delivery_date.replace(tzinfo=datetime.timezone.utc)
                except Exception as e:
                    logger.warning(f"Could not parse expected_delivery_date: {str(e)}")
            
            date_received = None
            batch_status = batch_data.get('status', 'pending')
            
            if 'date_received' in batch_data and batch_data['date_received']:
                try:
                    date_received = parser.parse(batch_data['date_received'])
                    if date_received.tzinfo is None:
                        date_received = date_received.replace(tzinfo=datetime.timezone.utc)
                except Exception as e:
                    logger.warning(f"Could not parse date_received: {str(e)}")
            
            # For active batches without date_received, use current time
            if batch_status == 'active' and not date_received:
                date_received = datetime.utcnow()
            
            # Generate batch number
            batch_number = batch_data.get('batch_number') or self.generate_batch_number(batch_data['product_id'])
            
            # Create batch using the PynamoDB model
            batch = Batch.create_batch(
                product_id=batch_data['product_id'],
                batch_number=batch_number,
                quantity_received=int(batch_data.get('quantity_received', 0)),
                quantity_remaining=int(batch_data.get('quantity_received', 0)),
                cost_price=float(batch_data.get('cost_price', 0)),
                expiry_date=expiry_date,
                expected_delivery_date=expected_delivery_date,
                date_received=date_received,
                supplier_id=batch_data.get('supplier_id'),
                status=batch_status,
                notes=batch_data.get('notes', ''),
                sync_logs=[self.add_sync_log(
                    source='system',
                    status='success',
                    action='created',
                    details=[{'action': 'batch_creation'}]
                )]
            )
            
            if batch:
                # Update product stock and expiry info
                self.update_product_expiry_summary(batch_data['product_id'])
                
                # Send appropriate notification
                notification_type = 'stock_ordered' if batch_status == 'pending' else 'stock_received'
                self._send_batch_notification(
                    notification_type,
                    product_name,
                    {
                        'batch_id': batch.sk,
                        'quantity': batch.quantity_received,
                        'status': batch.status,
                        'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                        'supplier_id': batch.supplier_id
                    }
                )
                
                return batch.to_dict()
            
            raise Exception("Failed to create batch")
            
        except Exception as e:
            logger.error(f"Error creating batch: {str(e)}")
            raise Exception(f"Error creating batch: {str(e)}")

    def get_batches_by_product(self, product_id, status=None):
        """Get all batches for a specific product using GSI"""
        try:
            if status:
                batches = Batch.get_by_product_and_status(product_id, status, limit=100)
            else:
                batches = Batch.get_by_product_id(product_id, limit=100)
            
            # Convert to dict and sort by date_received descending
            batch_dicts = [batch.to_dict() for batch in batches]
            batch_dicts.sort(key=lambda x: x.get('date_received', ''), reverse=True)
            
            return batch_dicts
            
        except Exception as e:
            logger.error(f"Error getting batches by product: {str(e)}")
            raise Exception(f"Error getting batches by product: {str(e)}")
    
    def update_product_expiry_summary(self, product_id):
        """Update product's simplified expiry tracking fields"""
        try:
            # Get expiry summary using BatchManager
            expiry_summary = self.batch_manager.get_expiry_summary(product_id)
            
            if expiry_summary:
                # Update product
                product = Product.get_by_id(product_id)
                if product:
                    if expiry_summary.get('oldest_expiry'):
                        product.oldest_batch_expiry = expiry_summary['oldest_expiry'].isoformat()
                    else:
                        product.oldest_batch_expiry = None
                    
                    product.expiry_alert = expiry_summary.get('expiry_alert', False)
                    product.total_stock = expiry_summary.get('total_stock', 0)
                    
                    # Update cost_price from oldest non-expired batch
                    batches = Batch.get_active_non_expired_batches(product_id)
                    if batches:
                        # Sort by expiry date (oldest first)
                        batches.sort(key=lambda x: x.expiry_date if x.expiry_date else datetime.max)
                        oldest_batch = batches[0]
                        product.cost_price = oldest_batch.cost_price
                    
                    product.updated_at = datetime.utcnow()
                    product.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating product expiry summary: {str(e)}")
            return False

    def get_expiring_batches(self, days_ahead=30):
        """Get batches expiring within specified days using GSI"""
        try:
            logger.info(f"Checking for batches expiring within {days_ahead} days")
            
            # Use the model's get_expiring_soon method
            batches = Batch.get_expiring_soon(days_threshold=days_ahead)
            
            # Enrich with product info
            enriched_batches = []
            for batch in batches:
                try:
                    product = Product.get_by_id(batch.product_id)
                    if product:
                        batch_dict = batch.to_dict()
                        batch_dict['product_info'] = {
                            'product_name': product.product_name,
                            'sku': product.SKU,
                            'category_name': product.category_name if hasattr(product, 'category_name') else None,
                            'image_url': product.image_url
                        }
                        enriched_batches.append(batch_dict)
                except Exception as e:
                    logger.error(f"Error enriching batch {batch.sk}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(enriched_batches)} expiring batches")
            return enriched_batches
            
        except Exception as e:
            logger.error(f"Error getting expiring batches: {str(e)}")
            raise Exception(f"Error getting expiring batches: {str(e)}")

    def check_and_alert_expiring_batches(self, days_ahead=7):
        """Check for expiring batches and send alerts"""
        try:
            logger.info(f"Checking for batches expiring within {days_ahead} days")
            
            expiring_batches = self.get_expiring_batches(days_ahead)
            logger.info(f"Found {len(expiring_batches)} expiring batches")
            
            alerts_sent = 0
            for batch_info in expiring_batches:
                try:
                    product_info = batch_info.get('product_info', {})
                    days_until_expiry = batch_info.get('status_info', {}).get('days_until_expiry', 0)
                    
                    logger.info(f"Sending alert for batch {batch_info['batch_id']}, expires in {days_until_expiry} days")
                    
                    self._send_batch_notification(
                        'expiry_warning',
                        product_info.get('product_name', 'Unknown Product'),
                        {
                            'batch_id': batch_info['batch_id'],
                            'batch_number': batch_info['batch_number'],
                            'expiry_date': batch_info.get('expiry_date'),
                            'days_until_expiry': days_until_expiry,
                            'quantity_remaining': batch_info.get('quantity_remaining', 0)
                        }
                    )
                    alerts_sent += 1
                    
                except Exception as batch_error:
                    logger.error(f"Error processing batch alert: {str(batch_error)}")
                    continue
            
            logger.info(f"Total alerts sent: {alerts_sent}")
            return alerts_sent
            
        except Exception as e:
            logger.error(f"Error checking expiring batches: {str(e)}")
            raise Exception(f"Error checking expiring batches: {str(e)}")

    # ================================================================
    # BATCH QUERIES AND REPORTING
    # ================================================================
    
    def get_all_batches(self, filters=None, enrich_with_product=True):
        """
        Get all batches with optional filters and product enrichment
        """
        try:
            # Get all batches
            batches = Batch.get_all_batches(limit=1000)
            
            # Apply filters
            filtered_batches = []
            for batch in batches:
                include = True
                
                if filters:
                    if filters.get('product_id') and batch.product_id != filters['product_id']:
                        include = False
                    if filters.get('status') and batch.status != filters['status']:
                        include = False
                    if filters.get('supplier_id') and batch.supplier_id != filters['supplier_id']:
                        include = False
                    if filters.get('expiring_soon'):
                        days = filters.get('days_ahead', 30)
                        if batch.expiry_date:
                            future_date = datetime.utcnow() + timedelta(days=days)
                            if batch.expiry_date > future_date:
                                include = False
                        else:
                            include = False
                
                if include:
                    filtered_batches.append(batch)
            
            # Enrich with product information if requested
            if enrich_with_product:
                enriched_batches = []
                for batch in filtered_batches:
                    try:
                        product = Product.get_by_id(batch.product_id)
                        batch_dict = batch.to_dict()
                        
                        if product:
                            batch_dict['product_name'] = product.product_name
                            batch_dict['category_id'] = product.category_id
                            batch_dict['category_name'] = product.category_name if hasattr(product, 'category_name') else None
                            batch_dict['subcategory_name'] = product.subcategory_name
                            batch_dict['product_sku'] = product.SKU
                            batch_dict['product_image'] = product.image_url
                        else:
                            batch_dict['product_name'] = 'Unknown Product'
                        
                        enriched_batches.append(batch_dict)
                    except Exception as e:
                        logger.error(f"Error enriching batch {batch.sk}: {str(e)}")
                        batch_dict = batch.to_dict()
                        batch_dict['product_name'] = 'Unknown Product'
                        enriched_batches.append(batch_dict)
                
                return enriched_batches
            
            # Return without enrichment
            return [batch.to_dict() for batch in filtered_batches]
            
        except Exception as e:
            logger.error(f"Error getting batches: {str(e)}")
            raise Exception(f"Error getting batches: {str(e)}")

    def get_batch_by_id(self, batch_id):
        """Get batch by ID"""
        try:
            batch = Batch.get_by_id(batch_id)
            if batch:
                return batch.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error getting batch: {str(e)}")
            raise Exception(f"Error getting batch: {str(e)}")

    def get_products_with_expiry_summary(self):
        """Get products with their expiry summary information"""
        try:
            # Get all active products
            products = Product.get_all_active_products()
            
            result = []
            for product in products:
                # Get expiry summary for this product
                expiry_summary = self.batch_manager.get_expiry_summary(product.sk)
                
                product_dict = {
                    'product_id': product.sk.replace('PROD-', ''),
                    'product_name': product.product_name,
                    'sku': product.SKU,
                    'total_stock': expiry_summary.get('total_stock', 0),
                    'oldest_batch_expiry': (
                        expiry_summary['oldest_expiry'].isoformat() 
                        if expiry_summary.get('oldest_expiry') else None
                    ),
                    'expiry_alert': expiry_summary.get('expiry_alert', False),
                    'low_stock_threshold': product.low_stock_threshold,
                    'stock_status': product.get_stock_status()
                }
                result.append(product_dict)
            
            # Sort by oldest expiry date
            result.sort(key=lambda x: x['oldest_batch_expiry'] or '9999-12-31')
            return result
            
        except Exception as e:
            logger.error(f"Error getting products with expiry summary: {str(e)}")
            raise Exception(f"Error getting products with expiry summary: {str(e)}")
    
    def update_batch_quantity(self, batch_id, quantity_used, adjustment_type="correction", adjusted_by=None, notes=None):
        """Update batch quantity when stock is sold/used"""
        try:
            batch = Batch.get_by_id(batch_id)
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")
            
            # Use the batch's consume_quantity method
            batch.consume_quantity(
                quantity=quantity_used,
                reason=adjustment_type,
                adjusted_by=adjusted_by or 'system',
                source='manual_adjustment',
                notes=notes
            )
            
            # Update product expiry summary
            self.update_product_expiry_summary(batch.product_id)
            
            # Send notification if batch is depleted
            if batch.quantity_remaining <= 0:
                product = Product.get_by_id(batch.product_id)
                product_name = product.product_name if product else 'Unknown Product'
                
                self._send_batch_notification(
                    'batch_depleted',
                    product_name,
                    {
                        'batch_id': batch_id,
                        'batch_number': batch.batch_number
                    }
                )
            
            return batch.to_dict()
            
        except Exception as e:
            logger.error(f"Error updating batch quantity: {str(e)}")
            raise Exception(f"Error updating batch quantity: {str(e)}")

    def update_batch(self, batch_id, update_data):
        """Update batch details"""
        try:
            from dateutil import parser
            
            batch = Batch.get_by_id(batch_id)
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")
            
            # Track changes for sync log
            changes = {}
            
            # Update fields that are provided
            if 'quantity_received' in update_data:
                quantity = update_data['quantity_received']
                if quantity <= 0:
                    raise ValueError("Quantity must be greater than 0")
                changes['quantity_received'] = quantity
                batch.quantity_received = quantity
                # Also update remaining if batch is pending
                if batch.status == 'pending':
                    batch.quantity_remaining = quantity
            
            if 'cost_price' in update_data:
                cost = update_data['cost_price']
                if cost < 0:
                    raise ValueError("Cost price cannot be negative")
                changes['cost_price'] = cost
                batch.cost_price = cost
            
            if 'expiry_date' in update_data:
                expiry_date = update_data['expiry_date']
                if expiry_date:
                    if isinstance(expiry_date, str):
                        try:
                            parsed_date = parser.parse(expiry_date)
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                            batch.expiry_date = parsed_date
                        except Exception as e:
                            logger.warning(f"Could not parse expiry_date: {str(e)}")
                    else:
                        batch.expiry_date = expiry_date
                else:
                    batch.expiry_date = None
                changes['expiry_date'] = batch.expiry_date
            
            if 'expected_delivery_date' in update_data:
                expected_delivery_date = update_data['expected_delivery_date']
                if expected_delivery_date:
                    if isinstance(expected_delivery_date, str):
                        try:
                            parsed_date = parser.parse(expected_delivery_date)
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                            batch.expected_delivery_date = parsed_date
                        except Exception as e:
                            logger.warning(f"Could not parse expected_delivery_date: {str(e)}")
                    else:
                        batch.expected_delivery_date = expected_delivery_date
                else:
                    batch.expected_delivery_date = None
            
            if 'status' in update_data:
                status = update_data['status']
                if not status or (isinstance(status, str) and status.strip() == ''):
                    raise ValueError("Status cannot be empty")
                
                normalized_status = status.strip().lower()
                allowed_statuses = {'pending', 'active', 'inactive', 'depleted', 'cancelled', 'expired'}
                
                # Map to Batch model statuses
                status_mapping = {
                    'pending': 'pending',
                    'active': 'active',
                    'inactive': 'inactive',
                    'depleted': 'exhausted',
                    'cancelled': 'cancelled',
                    'expired': 'expired'
                }
                
                if normalized_status not in allowed_statuses:
                    raise ValueError(f"Invalid status '{status}'. Allowed values: {', '.join(sorted(allowed_statuses))}")
                
                batch.status = status_mapping.get(normalized_status, normalized_status)
                changes['status'] = batch.status
            
            if 'notes' in update_data:
                batch.notes = update_data['notes']
                changes['notes'] = batch.notes
            
            if 'date_received' in update_data:
                date_received = update_data['date_received']
                if date_received:
                    if isinstance(date_received, str):
                        try:
                            parsed_date = parser.parse(date_received)
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                            batch.date_received = parsed_date
                        except Exception as e:
                            logger.warning(f"Could not parse date_received: {str(e)}")
                    else:
                        batch.date_received = date_received
                changes['date_received'] = batch.date_received
            
            if 'supplier_id' in update_data:
                batch.supplier_id = update_data['supplier_id']
                changes['supplier_id'] = batch.supplier_id
            
            # Recalculate status based on updated values
            batch._calculate_and_set_status()
            
            # Save the batch
            batch.save()
            
            # Add sync log for the update
            if changes:
                details = [{"field": field, "new_value": str(value)} for field, value in changes.items()]
                batch.add_sync_log(
                    source='system',
                    status='success',
                    action='update',
                    details=details
                )
            
            # Update product expiry summary if relevant fields changed
            if any(field in changes for field in ['expiry_date', 'quantity_received', 'status']):
                self.update_product_expiry_summary(batch.product_id)
            
            return batch.to_dict()
            
        except Exception as e:
            logger.error(f"Error updating batch: {str(e)}")
            raise Exception(f"Error updating batch: {str(e)}")

    # ================================================================
    # INTEGRATION WITH SALES
    # ================================================================
    
    def process_sale_fifo(self, product_id, quantity_sold):
        """Process a sale using FIFO (First In, First Out) logic"""
        try:
            # Get batches for fulfillment using BatchManager
            fulfillment_result = self.batch_manager.get_batch_for_fulfillment(
                product_id=product_id,
                quantity_needed=quantity_sold,
                strategy="fefo"  # Using FEFO (First Expired First Out)
            )
            
            if not fulfillment_result['can_fulfill']:
                raise Exception(f"Insufficient stock: {fulfillment_result['remaining_quantity']} units could not be fulfilled")
            
            batches_used = []
            
            # Process each batch
            for batch_info in fulfillment_result['batches_to_use']:
                batch = batch_info['batch']
                quantity_from_batch = batch_info['quantity_to_take']
                
                # Consume quantity from batch
                batch.consume_quantity(
                    quantity=quantity_from_batch,
                    reason="sale",
                    adjusted_by="pos_system",
                    source="pos_sale",
                    notes="POS sale transaction"
                )
                
                batches_used.append({
                    'batch_id': batch.sk,
                    'batch_number': batch.batch_number,
                    'quantity_used': quantity_from_batch,
                    'cost_price': batch.cost_price,
                    'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None
                })
            
            # Update product stock
            self.update_product_expiry_summary(product_id)
            
            return batches_used
            
        except Exception as e:
            logger.error(f"Error processing FIFO sale: {str(e)}")
            raise Exception(f"Error processing FIFO sale: {str(e)}")

    def process_batch_adjustment(self, product_id, quantity_used, adjustment_type, adjusted_by=None, notes=None):
        """Process a batch adjustment using FIFO logic"""
        try:
            logger.info(f"Processing batch adjustment for product {product_id}: {quantity_used} units, type: {adjustment_type}")
            
            # Get batches for fulfillment
            fulfillment_result = self.batch_manager.get_batch_for_fulfillment(
                product_id=product_id,
                quantity_needed=quantity_used,
                strategy="fefo"
            )
            
            if not fulfillment_result['can_fulfill']:
                raise Exception(f"Insufficient stock: {fulfillment_result['remaining_quantity']} units could not be adjusted")
            
            batches_adjusted = []
            
            # Process each batch
            for batch_info in fulfillment_result['batches_to_use']:
                batch = batch_info['batch']
                quantity_from_batch = batch_info['quantity_to_take']
                
                logger.info(f"Adjusting batch {batch.sk}: {quantity_from_batch} units")
                
                # Consume quantity with adjustment type as reason
                batch.consume_quantity(
                    quantity=quantity_from_batch,
                    reason=adjustment_type,
                    adjusted_by=adjusted_by or 'system',
                    source="manual_adjustment",
                    notes=notes
                )
                
                batches_adjusted.append({
                    'batch_id': batch.sk,
                    'batch_number': batch.batch_number,
                    'quantity_adjusted': quantity_from_batch,
                    'adjustment_type': adjustment_type,
                    'remaining_in_batch': batch.quantity_remaining
                })
            
            # Update product stock
            self.update_product_expiry_summary(product_id)
            
            logger.info(f"Successfully adjusted {quantity_used} units across {len(batches_adjusted)} batches")
            
            return {
                'product_id': product_id,
                'total_adjusted': quantity_used,
                'adjustment_type': adjustment_type,
                'batches_affected': batches_adjusted,
                'adjusted_by': adjusted_by
            }
            
        except Exception as e:
            logger.error(f"Error processing batch adjustment: {str(e)}")
            raise Exception(f"Error processing batch adjustment: {str(e)}")

    # ================================================================
    # MAINTENANCE AND CLEANUP
    # ================================================================
    
    def mark_expired_batches(self):
        """Mark expired batches as expired using BatchManager"""
        try:
            updated_batches = self.batch_manager.update_expired_batches()
            
            # Update product expiry summaries for affected products
            affected_products = set()
            for batch_info in updated_batches:
                batch = Batch.get_by_id(batch_info['batch_id'])
                if batch:
                    affected_products.add(batch.product_id)
            
            for product_id in affected_products:
                self.update_product_expiry_summary(product_id)
                # Send notification for expired batches
                product = Product.get_by_id(product_id)
                if product:
                    self._send_batch_notification(
                        'batch_expired',
                        product.product_name,
                        {'product_id': product_id, 'batches_expired': len(updated_batches)}
                    )
            
            return len(updated_batches)
            
        except Exception as e:
            logger.error(f"Error marking expired batches: {str(e)}")
            raise Exception(f"Error marking expired batches: {str(e)}")
    
    def activate_batch(self, batch_number, product_id, supplier_id, quantity_received=None, cost_price=None, expiry_date=None, date_received=None, notes=None):
        """Activate a pending batch by updating it to active status"""
        try:
            # Find the pending batch by batch number and product_id
            batches = Batch.get_by_product_id(product_id, limit=100)
            batch_to_activate = None
            
            for batch in batches:
                if (batch.batch_number == batch_number and 
                    batch.supplier_id == supplier_id and 
                    batch.status == 'pending'):
                    batch_to_activate = batch
                    break
            
            if not batch_to_activate:
                raise Exception(f"Pending batch with number {batch_number} not found for product {product_id}")
            
            # Update fields
            if quantity_received is not None:
                batch_to_activate.quantity_received = quantity_received
                batch_to_activate.quantity_remaining = quantity_received
            
            if cost_price is not None:
                batch_to_activate.cost_price = cost_price
            
            if expiry_date:
                from dateutil import parser
                parsed_date = parser.parse(expiry_date) if isinstance(expiry_date, str) else expiry_date
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                batch_to_activate.expiry_date = parsed_date
            
            # Set date_received
            if date_received:
                from dateutil import parser
                parsed_date = parser.parse(date_received) if isinstance(date_received, str) else date_received
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=datetime.timezone.utc)
                batch_to_activate.date_received = parsed_date
            else:
                batch_to_activate.date_received = datetime.utcnow()
            
            # Update status to active
            batch_to_activate.status = 'active'
            batch_to_activate._calculate_and_set_status()
            
            # Save the batch
            batch_to_activate.save()
            
            # Update product stock and expiry summary
            self.update_product_expiry_summary(product_id)
            
            # Send notification
            product = Product.get_by_id(product_id)
            if product:
                self._send_batch_notification(
                    'activated',
                    product.product_name,
                    {
                        'batch_number': batch_number,
                        'quantity': quantity_received or batch_to_activate.quantity_received,
                        'supplier_id': supplier_id
                    }
                )
            
            return batch_to_activate.to_dict()
            
        except Exception as e:
            logger.error(f"Error activating batch: {str(e)}")
            raise Exception(f"Error activating batch: {str(e)}")

    # ================================================================
    # FIFO STOCK DEDUCTION
    # ================================================================
    
    def deduct_stock_fifo(self, product_id, quantity_needed, transaction_date, transaction_info=None):
        """
        Deduct stock from batches using FIFO with usage_history tracking
        """
        try:
            logger.info(f"FIFO Stock Deduction - Product: {product_id}, Quantity: {quantity_needed}")
            
            # Get batches for fulfillment
            fulfillment_result = self.batch_manager.get_batch_for_fulfillment(
                product_id=product_id,
                quantity_needed=quantity_needed,
                strategy="fefo"
            )
            
            if not fulfillment_result['can_fulfill']:
                raise ValueError(
                    f"Insufficient stock. Need {quantity_needed}, have {quantity_needed - fulfillment_result['remaining_quantity']}"
                )
            
            batch_deductions = []
            
            # Process each batch
            for batch_info in fulfillment_result['batches_to_use']:
                batch = batch_info['batch']
                deduct_amount = batch_info['quantity_to_take']
                
                logger.info(f"Processing batch {batch.sk}: {deduct_amount} units")
                
                # Consume quantity with transaction info
                batch.consume_quantity(
                    quantity=deduct_amount,
                    reason="sale",
                    adjusted_by=transaction_info.get('adjusted_by') if transaction_info else None,
                    source=transaction_info.get('source', 'pos_sale') if transaction_info else 'pos_sale',
                    notes=f"Transaction {transaction_info.get('transaction_id', 'N/A')}" if transaction_info else 'POS sale'
                )
                
                batch_deductions.append({
                    'batch_id': batch.sk,
                    'batch_number': batch.batch_number,
                    'quantity_deducted': deduct_amount,
                    'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                    'cost_price': batch.cost_price
                })
            
            # Update product stock
            self.update_product_expiry_summary(product_id)
            
            logger.info(f"FIFO deduction complete - Used {len(batch_deductions)} batches")
            return batch_deductions
            
        except Exception as e:
            logger.error(f"FIFO deduction failed: {str(e)}")
            raise
    
    def check_batch_availability(self, product_id, quantity_needed):
        """
        Check if sufficient stock is available in batches
        """
        try:
            batches = Batch.get_active_non_expired_batches(product_id)
            
            total_stock = sum(batch.quantity_remaining for batch in batches)
            
            return {
                'available': total_stock >= quantity_needed,
                'total_stock': total_stock,
                'batches_count': len(batches)
            }
            
        except Exception as e:
            logger.error(f"Error checking batch availability: {str(e)}")
            return {
                'available': False,
                'total_stock': 0,
                'batches_count': 0
            }
    
    def restore_stock_to_batches(self, batches_used, transaction_date, transaction_info=None):
        """
        Restore stock to batches (for cancellations/voids)
        """
        try:
            logger.info(f"Restoring stock to {len(batches_used)} batches")
            
            for batch_info in batches_used:
                batch_id = batch_info['batch_id']
                quantity_to_restore = batch_info['quantity_deducted']
                
                batch = Batch.get_by_id(batch_id)
                if not batch:
                    logger.warning(f"Batch {batch_id} not found, skipping")
                    continue
                
                logger.info(f"Restoring {quantity_to_restore} to batch {batch.sk}")
                
                # Add quantity back to batch
                batch.add_quantity(
                    quantity=quantity_to_restore,
                    reason=transaction_info.get('reason', 'restoration') if transaction_info else 'restoration',
                    adjusted_by=transaction_info.get('adjusted_by') if transaction_info else None,
                    source='restoration',
                    notes=transaction_info.get('reason', 'Stock restored from cancelled/voided transaction') if transaction_info else 'Stock restored'
                )
            
            # Update product stock for each affected product
            affected_products = set()
            for batch_info in batches_used:
                batch = Batch.get_by_id(batch_info['batch_id'])
                if batch:
                    affected_products.add(batch.product_id)
            
            for product_id in affected_products:
                self.update_product_expiry_summary(product_id)
            
            logger.info("Stock restoration complete")
            
        except Exception as e:
            logger.error(f"Stock restoration failed: {str(e)}")
            raise
    
    # ================================================================
    # REPORTING AND ANALYTICS
    # ================================================================
    
    def get_batch_report(self, start_date=None, end_date=None, product_id=None, supplier_id=None):
        """
        Generate batch report with filtering options
        """
        try:
            batches = self.get_all_batches(filters=None, enrich_with_product=True)
            
            # Apply filters
            filtered_batches = []
            for batch in batches:
                include = True
                
                if start_date and batch.get('date_received'):
                    batch_date = datetime.fromisoformat(batch['date_received'].replace('Z', '+00:00'))
                    if batch_date < start_date:
                        include = False
                
                if end_date and batch.get('date_received'):
                    batch_date = datetime.fromisoformat(batch['date_received'].replace('Z', '+00:00'))
                    if batch_date > end_date:
                        include = False
                
                if product_id and batch.get('product_id') != product_id:
                    include = False
                
                if supplier_id and batch.get('supplier_id') != supplier_id:
                    include = False
                
                if include:
                    filtered_batches.append(batch)
            
            # Calculate summary
            summary = {
                'total_batches': len(filtered_batches),
                'total_quantity_received': sum(b.get('quantity_received', 0) for b in filtered_batches),
                'total_quantity_remaining': sum(b.get('quantity_remaining', 0) for b in filtered_batches),
                'total_value': sum(b.get('quantity_remaining', 0) * b.get('cost_price', 0) for b in filtered_batches),
                'by_status': {},
                'by_product': {},
                'by_supplier': {}
            }
            
            for batch in filtered_batches:
                # Status breakdown
                status = batch.get('status', 'unknown')
                summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
                
                # Product breakdown
                product_name = batch.get('product_name', 'Unknown')
                summary['by_product'][product_name] = summary['by_product'].get(product_name, 0) + batch.get('quantity_remaining', 0)
                
                # Supplier breakdown
                supplier_id = batch.get('supplier_id')
                if supplier_id:
                    summary['by_supplier'][supplier_id] = summary['by_supplier'].get(supplier_id, 0) + batch.get('quantity_remaining', 0)
            
            return {
                'batches': filtered_batches,
                'summary': summary,
                'filters_applied': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None,
                    'product_id': product_id,
                    'supplier_id': supplier_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating batch report: {str(e)}")
            raise Exception(f"Error generating batch report: {str(e)}")