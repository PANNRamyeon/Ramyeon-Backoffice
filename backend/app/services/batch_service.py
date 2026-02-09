from datetime import datetime, timedelta
from ..database import db_manager
from notifications.services import notification_service
import logging

logger = logging.getLogger(__name__)

class BatchService:
    def __init__(self):
        self.db = db_manager.get_database()
        self.batch_collection = self.db.batches
        self.product_collection = self.db.products
        self.supplier_collection = self.db.suppliers
        # ✅ Enhanced: Add products_collection for FIFO operations
        self.products_collection = self.db.products
        
    def validate_foreign_keys(self, batch_data):
        """Validate that foreign key references exist"""
        # Validate product_id
        if 'product_id' in batch_data and batch_data['product_id']:
            product = self.product_collection.find_one({
                '_id': batch_data['product_id'],
                'isDeleted': {'$ne': True}
            })
            if not product:
                raise ValueError(f"Product with ID {batch_data['product_id']} not found")
        
        # Validate supplier_id if provided
        if 'supplier_id' in batch_data and batch_data['supplier_id']:
            supplier = self.supplier_collection.find_one({'_id': batch_data['supplier_id']})
            if not supplier:
                raise ValueError(f"Supplier with ID {batch_data['supplier_id']} not found")

    def _send_batch_notification(self, action_type, product_name, additional_metadata=None):
        """Centralized notification helper for batch actions"""
        try:
            titles = {
                'created': "New Batch Added",
                'stock_received': "Stock Received",
                'stock_ordered': "Purchase Order Created",  # ✅ NEW
                'activated': "Stock Activated",  # ✅ NEW
                'expiry_warning': "Expiry Warning",
                'batch_expired': "Batch Expired",
                'batch_depleted': "Batch Depleted"
            }
            
            messages = {
                'created': f"New batch created for '{product_name}'",
                'stock_received': f"Stock received for '{product_name}'",
                'stock_ordered': f"Purchase order created for '{product_name}'",  # ✅ NEW
                'activated': f"Stock activated for '{product_name}'",  # ✅ NEW
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

    def generate_batch_id(self, product_id):
        """Generate unique batch ID for a product"""
        try:
            # Format: BATCH-PROD00001-001
            product_suffix = product_id.replace('PROD-', '')
            base_pattern = f"BATCH-{product_suffix}-"
            
            # Find all existing batch IDs for this product
            existing_batches = self.batch_collection.find(
                {'product_id': product_id},
                {'_id': 1}
            )
            
            # Extract sequence numbers from existing batch IDs
            max_sequence = 0
            for batch in existing_batches:
                batch_id = batch.get('_id', '')
                if batch_id.startswith(base_pattern):
                    try:
                        # Extract the sequence number (last part after final dash)
                        sequence_str = batch_id.split('-')[-1]
                        sequence_num = int(sequence_str)
                        max_sequence = max(max_sequence, sequence_num)
                    except (ValueError, IndexError):
                        continue
            
            # Generate next sequence number
            next_sequence = max_sequence + 1
            batch_id = f"{base_pattern}{next_sequence:03d}"
            
            # Double-check uniqueness (safety check)
            counter = 0
            while self.batch_collection.find_one({'_id': batch_id}) and counter < 1000:
                next_sequence += 1
                batch_id = f"{base_pattern}{next_sequence:03d}"
                counter += 1
            
            if counter >= 1000:
                # If somehow we can't find a unique ID after 1000 tries, use timestamp
                raise Exception("Could not generate unique batch ID")
            
            return batch_id
        
        except Exception as e:
            # Fallback to timestamp-based ID
            logger.warning(f"Failed to generate sequential batch ID: {e}, using timestamp fallback")
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            random_suffix = datetime.utcnow().microsecond % 1000
            return f"BATCH-{product_id}-{timestamp}-{random_suffix:03d}"

    def add_sync_log(self, source='cloud', status='synced', details=None):
        """Helper method to create sync log entries"""
        return {
            'last_updated': datetime.utcnow(),
            'source': source,
            'status': status,
            'details': details or {}
        }

    # ================================================================
    # CORE BATCH OPERATIONS
    # ================================================================
    
    def create_batch(self, batch_data):
        """Create a new batch when stock is received"""
        try:
            logger.info(f"Creating batch for product: {batch_data.get('product_id')}")
            
            # Validate foreign keys
            self.validate_foreign_keys(batch_data)
            
            # Generate batch ID
            batch_id = self.generate_batch_id(batch_data['product_id'])
            
            # Use timezone-aware current time for consistency
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
            
            # Handle expiry_date conversion (with timezone awareness)
            expiry_date = batch_data.get('expiry_date')
            if expiry_date:
                if isinstance(expiry_date, str):
                    try:
                        # Try parsing different date formats and ensure timezone aware
                        from dateutil import parser
                        from datetime import timezone
                        parsed_date = parser.parse(expiry_date)
                        # If no timezone info, assume UTC
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        expiry_date = parsed_date
                    except Exception as e:
                        logger.warning(f"Could not parse expiry_date '{expiry_date}': {e}")
                        expiry_date = None
                elif not isinstance(expiry_date, datetime):
                    logger.warning(f"Invalid expiry_date type: {type(expiry_date)}")
                    expiry_date = None
            
            # Handle expected_delivery_date conversion (same format as expiry_date and date_received)
            expected_delivery_date = batch_data.get('expected_delivery_date')
            if expected_delivery_date:
                if isinstance(expected_delivery_date, str):
                    try:
                        # Try parsing different date formats and ensure timezone aware
                        from dateutil import parser
                        from datetime import timezone
                        parsed_date = parser.parse(expected_delivery_date)
                        # If no timezone info, assume UTC
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        expected_delivery_date = parsed_date
                    except Exception as e:
                        logger.warning(f"Could not parse expected_delivery_date '{expected_delivery_date}': {e}")
                        expected_delivery_date = None
                elif not isinstance(expected_delivery_date, datetime):
                    logger.warning(f"Invalid expected_delivery_date type: {type(expected_delivery_date)}")
                    expected_delivery_date = None
            
            # Handle date_received conversion (only set when stock is actually received)
            # For pending batches, this should be None until activation
            date_received = batch_data.get('date_received')
            batch_status = batch_data.get('status', 'active')
            
            if date_received:
                if isinstance(date_received, str):
                    try:
                        # Try parsing different date formats and ensure timezone aware
                        from dateutil import parser
                        from datetime import timezone
                        parsed_date = parser.parse(date_received)
                        # If no timezone info, assume UTC
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        date_received = parsed_date
                    except Exception as e:
                        logger.warning(f"Could not parse date_received '{date_received}': {e}")
                        date_received = None
                elif not isinstance(date_received, datetime):
                    logger.warning(f"Invalid date_received type: {type(date_received)}")
                    date_received = None
            else:
                # If status is active and no date_received provided, use current time (UTC)
                # If status is pending, leave date_received as None
                if batch_status == 'active':
                    from datetime import timezone
                    date_received = datetime.now(timezone.utc)
                else:
                    date_received = None
            
            # Get product info for category and subcategory
            product = self.product_collection.find_one({'_id': batch_data['product_id']})
            product_name = product.get('product_name', 'Unknown Product') if product else 'Unknown Product'
            
            # Create batch document
            batch_document = {
                '_id': batch_id,
                'product_id': batch_data['product_id'],
                'batch_number': batch_data.get('batch_number', f"B-{current_time.strftime('%Y%m%d')}"),
                'quantity_received': int(batch_data.get('quantity_received', 0)),
                'quantity_remaining': int(batch_data.get('quantity_received', 0)),
                'cost_price': float(batch_data.get('cost_price', 0)),
                'expiry_date': expiry_date,
                'expected_delivery_date': expected_delivery_date,
                'date_received': date_received,
                'supplier_id': batch_data.get('supplier_id'),
                'status': batch_status,  # ✅ Use status from request, default to 'active' for backwards compatibility
                'created_at': current_time,
                'updated_at': current_time,
                'notes': batch_data.get('notes', ''),  # ✅ Add notes field
                # Note: category info is NOT stored in batch - fetch from product when needed
                'sync_logs': [self.add_sync_log(source='cloud', status='pending', details={'action': 'created'})]
            }
            
            # Insert batch
            self.batch_collection.insert_one(batch_document)
            
            # Update product's simplified expiry tracking (only counts active batches)
            self.update_product_expiry_summary(batch_data['product_id'])
            
            # Send appropriate notification based on status
            batch_status = batch_document.get('status', 'active')
            if batch_status == 'pending':
                notification_type = 'stock_ordered'  # For pending orders
            else:
                notification_type = 'stock_received'  # For active/received stock
            
            self._send_batch_notification(
                notification_type,
                product_name,
                {
                    'batch_id': batch_id,
                    'quantity': batch_document['quantity_received'],
                    'status': batch_status,
                    'expiry_date': batch_document['expiry_date'].isoformat() if batch_document['expiry_date'] else None,
                    'supplier_id': batch_document.get('supplier_id')
                }
            )
            
            # Return created batch
            created_batch = self.batch_collection.find_one({'_id': batch_id})
            return created_batch
        
        except Exception as e:
            logger.error(f"Error creating batch: {str(e)}")
            raise Exception(f"Error creating batch: {str(e)}")

    def get_batches_by_product(self, product_id, status=None):
        """Get all batches for a specific product"""
        try:
            query = {'product_id': product_id}
            
            if status:
                query['status'] = status
            
            # Sort by date_received descending (latest first)
            batches = list(self.batch_collection.find(query).sort('date_received', -1))
            return batches
        
        except Exception as e:
            raise Exception(f"Error getting batches: {str(e)}")
    
    def update_product_expiry_summary(self, product_id):
        """Update product's simplified expiry tracking fields"""
        try:
            # Get active batches for this product
            active_batches = list(self.batch_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }).sort('expiry_date', 1))
            
            # Filter out expired batches based on expiry_date
            now = datetime.utcnow()
            non_expired_batches = []
            for batch in active_batches:
                if batch.get('expiry_date'):
                    # Skip if expired
                    if batch['expiry_date'] < now:
                        continue
                non_expired_batches.append(batch)
            
            # Calculate summary fields
            update_data = {}
            
            if non_expired_batches:
                # Get expiry dates (filter out None values)
                expiry_dates = [batch['expiry_date'] for batch in non_expired_batches if batch.get('expiry_date')]

                if expiry_dates:
                    update_data['oldest_batch_expiry'] = min(expiry_dates)
                    update_data['newest_batch_expiry'] = max(expiry_dates)

                    # Check if any batch is expiring within 30 days
                    warning_date = datetime.utcnow() + timedelta(days=30)
                    update_data['expiry_alert'] = any(exp_date <= warning_date for exp_date in expiry_dates)
                else:
                    # No expiry dates available
                    update_data['oldest_batch_expiry'] = None
                    update_data['newest_batch_expiry'] = None
                    update_data['expiry_alert'] = False

                # Calculate total stock from non-expired active batches
                total_stock = sum(batch['quantity_remaining'] for batch in non_expired_batches)
                update_data['total_stock'] = total_stock
                update_data['stock'] = total_stock  # Sync stock field with total_stock

                # Update cost_price from oldest non-expired batch (FIFO)
                # non_expired_batches is already sorted by expiry_date (oldest first)
                oldest_batch = non_expired_batches[0]
                update_data['cost_price'] = oldest_batch.get('cost_price', 0)
            else:
                # No active non-expired batches
                update_data.update({
                    'oldest_batch_expiry': None,
                    'newest_batch_expiry': None,
                    'expiry_alert': False,
                    'total_stock': 0,
                    'stock': 0,
                    'cost_price': 0
                })
            
            update_data['updated_at'] = datetime.utcnow()
            
            # Update product
            self.product_collection.update_one(
                {'_id': product_id},
                {'$set': update_data}
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error updating product expiry summary: {str(e)}")
            return False

    def get_expiring_batches(self, days_ahead=30):
        """Get batches expiring within specified days"""
        try:
            current_time = datetime.utcnow()
            future_date = current_time + timedelta(days=days_ahead)
            
            logger.info(f"Checking for batches expiring between {current_time} and {future_date}")
            
            # First, let's get all active batches and filter in Python to debug
            all_active_batches = list(self.batch_collection.find({
                'status': 'active',
                'quantity_remaining': {'$gt': 0},
                'expiry_date': {'$exists': True, '$ne': None}
            }))
            
            logger.info(f"Found {len(all_active_batches)} active batches with expiry dates")
            
            expiring_batches = []
            
            for batch in all_active_batches:
                try:
                    expiry_date = batch.get('expiry_date')
                    if not expiry_date:
                        continue
                    
                    # Convert string dates to datetime for comparison
                    if isinstance(expiry_date, str):
                        from dateutil import parser
                        expiry_date = parser.parse(expiry_date)
                    
                    # Check if batch expires within the timeframe
                    if current_time < expiry_date <= future_date:
                        # Get product info
                        product = self.product_collection.find_one({'_id': batch['product_id']})
                        if product:
                            batch['product_info'] = product
                            expiring_batches.append(batch)
                            logger.info(f"Batch {batch['_id']} expires {expiry_date}, adding to results")
                    else:
                        logger.info(f"Batch {batch['_id']} expires {expiry_date}, outside timeframe")
                        
                except Exception as batch_error:
                    logger.error(f"Error processing batch {batch.get('_id')}: {str(batch_error)}")
                    continue
            
            # Sort by expiry date
            expiring_batches.sort(key=lambda x: x.get('expiry_date'))
            
            logger.info(f"Found {len(expiring_batches)} expiring batches")
            return expiring_batches
            
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
                    batch = batch_info
                    product_info = batch_info.get('product_info', {})
                    
                    # Calculate days until expiry properly
                    expiry_date = batch.get('expiry_date')
                    if not expiry_date:
                        continue
                        
                    if isinstance(expiry_date, str):
                        from dateutil import parser
                        expiry_date = parser.parse(expiry_date)
                    
                    days_until_expiry = (expiry_date - datetime.utcnow()).days
                    
                    logger.info(f"Sending alert for batch {batch['_id']}, expires in {days_until_expiry} days")
                    
                    self._send_batch_notification(
                        'expiry_warning',
                        product_info.get('product_name', 'Unknown Product'),
                        {
                            'batch_id': batch['_id'],
                            'batch_number': batch.get('batch_number', 'Unknown'),
                            'expiry_date': expiry_date.isoformat(),
                            'days_until_expiry': days_until_expiry,
                            'quantity_remaining': batch.get('quantity_remaining', 0)
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
        Get all batches with optional filters and optional product enrichment.
        
        Note: Product enrichment includes DELETED products (isDeleted=True) because
        we need to display product names in historical records (orders, receipts, etc.)
        even if the product has been deleted from the catalog.
        """
        try:
            query = {}
            
            if filters:
                if filters.get('product_id'):
                    query['product_id'] = filters['product_id']
                
                if filters.get('status'):
                    query['status'] = filters['status']
                
                if filters.get('supplier_id'):
                    query['supplier_id'] = filters['supplier_id']
                
                if filters.get('expiring_soon'):
                    days = filters.get('days_ahead', 30)
                    future_date = datetime.utcnow() + timedelta(days=days)
                    query['expiry_date'] = {'$lte': future_date}
            
            batches = list(self.batch_collection.find(query).sort('expiry_date', 1))
            
            # Enrich batches with product information if requested
            # IMPORTANT: Includes deleted products for historical data integrity
            if enrich_with_product and batches:
                # Get unique product IDs
                product_ids = list(set([b.get('product_id') for b in batches if b.get('product_id')]))
                
                # Fetch all products at once
                products = {}
                if product_ids:
                    # Log for debugging
                    logger.debug(f"Enriching {len(batches)} batches with {len(product_ids)} unique product IDs: {product_ids[:5]}...")
                    
                    # Try to find products - handle both _id and product_id fields
                    # Products may use _id as the PROD-##### string OR have a separate product_id field
                    found_products = []
                    
                    # Strategy 1: Look up by _id (assuming _id = PROD-#####)
                    # IMPORTANT: Include deleted products - historical records (orders/receipts) need product names
                    # even if products are soft-deleted from the catalog
                    product_docs = list(self.product_collection.find(
                        {
                            '_id': {'$in': product_ids},
                            # Explicitly NOT filtering by isDeleted - include ALL products (active + deleted)
                            # This ensures historical purchase orders and receipts show correct product names
                        },
                        {'_id': 1, 'product_id': 1, 'product_name': 1, 'name': 1, 'category_id': 1, 'category_name': 1, 'subcategory_name': 1, 'isDeleted': 1}
                    ))
                    
                    for product in product_docs:
                        # Store using _id
                        product_key = str(product['_id'])
                        products[product_key] = product
                        products[product['_id']] = product
                        # Also store using product_id if it exists and is different
                        if 'product_id' in product and product['product_id'] != product['_id']:
                            products[str(product['product_id'])] = product
                            products[product['product_id']] = product
                        found_products.append(product_key)
                    
                    # Strategy 2: For missing products, try looking up by product_id field
                    missing_product_ids = [pid for pid in product_ids if str(pid) not in found_products and pid not in found_products]
                    if missing_product_ids:
                        logger.warning(f"Products not found by _id, trying product_id field for: {missing_product_ids[:10]}")
                        product_docs_by_product_id = list(self.product_collection.find(
                            {
                                'product_id': {'$in': missing_product_ids},
                                # Include deleted products for historical data integrity
                            },
                            {'_id': 1, 'product_id': 1, 'product_name': 1, 'name': 1, 'category_id': 1, 'category_name': 1, 'subcategory_name': 1, 'isDeleted': 1}
                        ))
                        
                        for product in product_docs_by_product_id:
                            product_id_val = product.get('product_id') or str(product['_id'])
                            product_key = str(product_id_val)
                            products[product_key] = product
                            products[product_id_val] = product
                            # Also store by _id
                            products[str(product['_id'])] = product
                            products[product['_id']] = product
                            if str(product_id_val) in missing_product_ids:
                                found_products.append(product_key)
                        
                        # Update missing list after second attempt
                        still_missing = [pid for pid in missing_product_ids if str(pid) not in found_products and pid not in found_products]
                        if still_missing:
                            logger.warning(f"Products still not found after both lookup methods for IDs: {still_missing[:5]}")
                            # Try individual direct lookups as last resort
                            for missing_id in still_missing[:5]:
                                try:
                                    # Try _id - include deleted products for historical records
                                    product = self.product_collection.find_one({'_id': missing_id})
                                    if not product:
                                        # Try product_id field - include deleted products
                                        product = self.product_collection.find_one({'product_id': missing_id})
                                    if product:
                                        product_key = str(missing_id)
                                        products[product_key] = product
                                        products[missing_id] = product
                                        is_deleted = product.get('isDeleted', False)
                                        logger.info(f"Found product {missing_id} with individual lookup (isDeleted: {is_deleted})")
                                    else:
                                        # Log detailed info about what we tried
                                        logger.warning(f"Product {missing_id} not found with individual lookup. Checking database...")
                                        # Check if ANY product with similar ID exists
                                        similar = list(self.product_collection.find(
                                            {'$or': [
                                                {'_id': {'$regex': str(missing_id)[:8]}},
                                                {'product_id': {'$regex': str(missing_id)[:8]}}
                                            ]}
                                        ).limit(3))
                                        if similar:
                                            logger.warning(f"Found similar products: {[(str(p.get('_id')), p.get('product_id'), p.get('product_name')) for p in similar]}")
                                except Exception as e:
                                    logger.debug(f"Failed individual lookup for product {missing_id}: {e}")
                
                # Enrich batches with product information
                enriched_batches = []
                for batch in batches:
                    batch_data = batch.copy() if isinstance(batch, dict) else dict(batch)
                    product_id = batch_data.get('product_id')
                    
                    # Try to find product using different key formats
                    product = None
                    if product_id:
                        # Try direct match
                        if product_id in products:
                            product = products[product_id]
                        # Try string conversion
                        elif str(product_id) in products:
                            product = products[str(product_id)]
                        # Try with ObjectId conversion if it's a string that looks like ObjectId
                        else:
                            try:
                                # from bson import ObjectId
                                if isinstance(product_id, str) and len(product_id) == 24:
                                    obj_id = product_id
                                    if obj_id in products:
                                        product = products[obj_id]
                            except:
                                pass
                    
                    if product:
                        batch_data['product_name'] = product.get('product_name') or product.get('name') or 'Unknown Product'
                        batch_data['category_id'] = batch_data.get('category_id') or product.get('category_id', '')
                        batch_data['category_name'] = batch_data.get('category_name') or product.get('category_name', '')
                        batch_data['subcategory_name'] = batch_data.get('subcategory_name') or product.get('subcategory_name', '')
                        logger.debug(f"Enriched batch {batch_data.get('_id')} with product name: {batch_data['product_name']}")
                    elif product_id and 'product_name' not in batch_data:
                        # Product not found but product_id exists
                        logger.warning(f"Product {product_id} (type: {type(product_id).__name__}) not found for batch {batch_data.get('_id')}. Batch product_id exists but product lookup failed.")
                        # Try one more time with direct DB lookup
                        try:
                            direct_product = self.product_collection.find_one({'_id': product_id})
                            if direct_product:
                                batch_data['product_name'] = direct_product.get('product_name') or direct_product.get('name') or 'Unknown Product'
                                batch_data['category_id'] = batch_data.get('category_id') or direct_product.get('category_id', '')
                                batch_data['category_name'] = batch_data.get('category_name') or direct_product.get('category_name', '')
                                batch_data['subcategory_name'] = batch_data.get('subcategory_name') or direct_product.get('subcategory_name', '')
                                logger.info(f"Found product {product_id} with direct DB lookup for batch {batch_data.get('_id')}")
                            else:
                                batch_data['product_name'] = 'Unknown Product'
                                logger.warning(f"Direct DB lookup also failed for product {product_id}")
                        except Exception as e:
                            logger.error(f"Error in direct DB lookup for product {product_id}: {e}")
                            batch_data['product_name'] = 'Unknown Product'
                    elif 'product_name' not in batch_data:
                        # No product_id at all
                        logger.warning(f"Batch {batch_data.get('_id')} has no product_id")
                        batch_data['product_name'] = 'Unknown Product'
                    # If product_name already exists in batch, keep it
                    
                    enriched_batches.append(batch_data)
                
                return enriched_batches
            
            return batches
        
        except Exception as e:
            logger.error(f"Error getting batches: {str(e)}")
            raise Exception(f"Error getting batches: {str(e)}")

    def get_batch_by_id(self, batch_id):
        """Get batch by ID"""
        try:
            batch = self.batch_collection.find_one({'_id': batch_id})
            return batch
        
        except Exception as e:
            raise Exception(f"Error getting batch: {str(e)}")

    def get_products_with_expiry_summary(self):
        """Get products with their expiry summary information"""
        try:
            pipeline = [
                {
                    '$match': {
                        'isDeleted': {'$ne': True}
                    }
                },
                {
                    '$project': {
                        '_id': 1,
                        'product_name': 1,
                        'SKU': 1,
                        'total_stock': 1,
                        'oldest_batch_expiry': 1,
                        'newest_batch_expiry': 1,
                        'expiry_alert': 1,
                        'low_stock_threshold': 1
                    }
                },
                {
                    '$sort': {'oldest_batch_expiry': 1}
                }
            ]
            
            products = list(self.product_collection.aggregate(pipeline))
            return products
        
        except Exception as e:
            raise Exception(f"Error getting products with expiry summary: {str(e)}")
        
    def update_batch_quantity(self, batch_id, quantity_used, adjustment_type="correction", adjusted_by=None, notes=None):
        """Update batch quantity when stock is sold/used - ENHANCED VERSION"""
        try:
            batch = self.batch_collection.find_one({'_id': batch_id})
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")
            
            new_quantity = max(0, batch['quantity_remaining'] - quantity_used)
            new_status = 'depleted' if new_quantity == 0 else 'active'
            
            current_time = datetime.utcnow()
            
            # Enhanced usage history entry (NO reason field)
            usage_entry = {
                'timestamp': current_time,
                'quantity_used': quantity_used,
                'remaining_after': new_quantity,
                'adjustment_type': adjustment_type,  # sale, damage, theft, correction, spoilage, return, shrinkage
                'adjusted_by': adjusted_by,
                'approved_by': None,
                'notes': notes,
                'source': 'manual_adjustment'
            }
            
            # Update batch
            result = self.batch_collection.update_one(
                {'_id': batch_id},
                {
                    '$set': {
                        'quantity_remaining': new_quantity,
                        'status': new_status,
                        'updated_at': current_time
                    },
                    '$push': {
                        'usage_history': usage_entry
                    }
                }
            )
            
            if result.modified_count > 0:
                self.update_product_expiry_summary(batch['product_id'])
                
                # Send notification if batch is depleted
                if new_status == 'depleted':
                    product = self.product_collection.find_one({'_id': batch['product_id']})
                    product_name = product.get('product_name', 'Unknown Product') if product else 'Unknown Product'
                    
                    self._send_batch_notification(
                        'batch_depleted',
                        product_name,
                        {
                            'batch_id': batch_id,
                            'batch_number': batch['batch_number']
                        }
                    )
                
                return self.batch_collection.find_one({'_id': batch_id})
            
            return None

        except Exception as e:
            raise Exception(f"Error updating batch quantity: {str(e)}")

    def update_batch(self, batch_id, update_data):
        """Update batch details like quantity, price, expiry date, expected delivery date, notes"""
        try:
            from datetime import timezone
            from dateutil import parser
            
            batch = self.batch_collection.find_one({'_id': batch_id})
            if not batch:
                raise Exception(f"Batch with ID {batch_id} not found")
            
            current_time = datetime.now(timezone.utc)
            updates = {}
            
            # Update quantity_received if provided
            if 'quantity_received' in update_data:
                quantity = update_data['quantity_received']
                if quantity <= 0:
                    raise ValueError("Quantity must be greater than 0")
                updates['quantity_received'] = quantity
                # Also update quantity_remaining if batch is pending or not yet used
                if batch['status'] == 'pending':
                    updates['quantity_remaining'] = quantity
                else:
                    # For active batches, adjust proportionally or keep the remaining as is
                    # Depending on your business logic, you might want to adjust this
                    updates['quantity_remaining'] = quantity
            
            # Update cost_price if provided
            if 'cost_price' in update_data:
                cost = update_data['cost_price']
                if cost < 0:
                    raise ValueError("Cost price cannot be negative")
                updates['cost_price'] = cost
            
            # Update expiry_date if provided
            if 'expiry_date' in update_data:
                expiry_date = update_data['expiry_date']
                if expiry_date:
                    if isinstance(expiry_date, str):
                        try:
                            parsed_date = parser.parse(expiry_date)
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                            expiry_date = parsed_date
                        except Exception as e:
                            logger.warning(f"Could not parse expiry_date '{expiry_date}': {e}")
                            expiry_date = None
                    elif not isinstance(expiry_date, datetime):
                        logger.warning(f"Invalid expiry_date type: {type(expiry_date)}")
                        expiry_date = None
                updates['expiry_date'] = expiry_date
            
            # Update expected_delivery_date if provided
            if 'expected_delivery_date' in update_data:
                expected_delivery_date = update_data['expected_delivery_date']
                if expected_delivery_date:
                    if isinstance(expected_delivery_date, str):
                        try:
                            parsed_date = parser.parse(expected_delivery_date)
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                            expected_delivery_date = parsed_date
                        except Exception as e:
                            logger.warning(f"Could not parse expected_delivery_date '{expected_delivery_date}': {e}")
                            expected_delivery_date = None
                    elif not isinstance(expected_delivery_date, datetime):
                        logger.warning(f"Invalid expected_delivery_date type: {type(expected_delivery_date)}")
                        expected_delivery_date = None
                updates['expected_delivery_date'] = expected_delivery_date
            
            # Update status if provided
            if 'status' in update_data:
                status = update_data['status']
                if status is None or (isinstance(status, str) and status.strip() == ''):
                    raise ValueError("Status cannot be empty")

                if not isinstance(status, str):
                    raise ValueError("Status must be a string")

                normalized_status = status.strip().lower()
                allowed_statuses = {
                    'pending',
                    'active',
                    'inactive',
                    'depleted',
                    'cancelled',
                    'expired'
                }

                if normalized_status not in allowed_statuses:
                    raise ValueError(f"Invalid status '{status}'. Allowed values: {', '.join(sorted(allowed_statuses))}")

                updates['status'] = normalized_status
            
            # Update notes if provided
            if 'notes' in update_data:
                updates['notes'] = update_data['notes']
            
            # Always update the updated_at timestamp
            updates['updated_at'] = current_time
            
            # Perform the update
            result = self.batch_collection.update_one(
                {'_id': batch_id},
                {'$set': updates}
            )
            
            if result.modified_count > 0:
                # Update product expiry summary if expiry date changed
                if 'expiry_date' in updates:
                    self.update_product_expiry_summary(batch['product_id'])
                
                return self.batch_collection.find_one({'_id': batch_id})
            
            return batch  # Return existing batch if nothing changed
        
        except Exception as e:
            logger.error(f"Error updating batch: {str(e)}")
            raise Exception(f"Error updating batch: {str(e)}")

    # ================================================================
    # INTEGRATION WITH SALES
    # ================================================================
    
    def process_sale_fifo(self, product_id, quantity_sold):
        """Process a sale using FIFO (First In, First Out) logic"""
        try:
            # Get active batches sorted by expiry date (FIFO)
            active_batches = list(self.batch_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }).sort('expiry_date', 1))
            
            if not active_batches:
                raise Exception(f"No active batches available for product {product_id}")
            
            remaining_to_sell = quantity_sold
            batches_used = []
            
            for batch in active_batches:
                if remaining_to_sell <= 0:
                    break
                
                quantity_from_batch = min(remaining_to_sell, batch['quantity_remaining'])
                
                # Update batch quantity with SALE type (NO reason parameter)
                self.update_batch_quantity(
                    batch['_id'], 
                    quantity_from_batch,
                    adjustment_type="sale",
                    adjusted_by=None,
                    notes="POS sale transaction"
                )
                
                batches_used.append({
                    'batch_id': batch['_id'],
                    'batch_number': batch['batch_number'],
                    'quantity_used': quantity_from_batch,
                    'cost_price': batch['cost_price'],
                    'expiry_date': batch['expiry_date']
                })
                
                remaining_to_sell -= quantity_from_batch
            
            if remaining_to_sell > 0:
                raise Exception(f"Insufficient stock: {remaining_to_sell} units could not be fulfilled")
            
            return batches_used
        
        except Exception as e:
            raise Exception(f"Error processing FIFO sale: {str(e)}")

    def process_batch_adjustment(self, product_id, quantity_used, adjustment_type, adjusted_by=None, notes=None):
        """Process a batch adjustment using FIFO logic"""
        try:
            logger.info(f"Processing batch adjustment for product {product_id}: {quantity_used} units, type: {adjustment_type}")
            
            # Get active batches sorted by expiry date (FIFO)
            active_batches = list(self.batch_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }).sort('expiry_date', 1))
            
            if not active_batches:
                raise Exception(f"No active batches available for product {product_id}")
            
            remaining_to_adjust = quantity_used
            batches_adjusted = []
            
            for batch in active_batches:
                if remaining_to_adjust <= 0:
                    break
                
                quantity_from_batch = min(remaining_to_adjust, batch['quantity_remaining'])
                
                logger.info(f"Adjusting batch {batch['_id']}: {quantity_from_batch} units")
                
                # Update batch quantity with the specified adjustment type
                self.update_batch_quantity(
                    batch['_id'], 
                    quantity_from_batch,
                    adjustment_type=adjustment_type,
                    adjusted_by=adjusted_by,
                    notes=notes
                )
                
                batches_adjusted.append({
                    'batch_id': batch['_id'],
                    'batch_number': batch['batch_number'],
                    'quantity_adjusted': quantity_from_batch,
                    'adjustment_type': adjustment_type,
                    'remaining_in_batch': batch['quantity_remaining'] - quantity_from_batch
                })
                
                remaining_to_adjust -= quantity_from_batch
            
            if remaining_to_adjust > 0:
                raise Exception(f"Insufficient stock: {remaining_to_adjust} units could not be adjusted")
            
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
        """Mark expired batches as expired"""
        try:
            current_time = datetime.utcnow()
            
            result = self.batch_collection.update_many(
                {
                    'status': 'active',
                    'expiry_date': {'$lt': current_time}
                },
                {
                    '$set': {
                        'status': 'expired',
                        'updated_at': current_time
                    }
                }
            )
            
            # Update product expiry summaries for affected products
            expired_batches = list(self.batch_collection.find({
                'status': 'expired',
                'updated_at': current_time
            }))
            
            affected_products = set(batch['product_id'] for batch in expired_batches)
            
            for product_id in affected_products:
                self.update_product_expiry_summary(product_id)
            
            return result.modified_count
        
        except Exception as e:
            raise Exception(f"Error marking expired batches: {str(e)}")
    
    def activate_batch(self, batch_number, product_id, supplier_id, quantity_received=None, cost_price=None, expiry_date=None, date_received=None, notes=None):
        """Activate a pending batch by updating it to active status"""
        try:
            # Find the pending batch
            query = {
                'batch_number': batch_number,
                'product_id': product_id,
                'supplier_id': supplier_id,
                'status': 'pending'
            }
            
            batch = self.batch_collection.find_one(query)
            if not batch:
                raise Exception(f"Pending batch with number {batch_number} not found for product {product_id}")
            
            # Prepare update data
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
            update_data = {
                'status': 'active',
                'updated_at': current_time
            }
            
            # Update fields if provided
            if quantity_received is not None:
                update_data['quantity_received'] = quantity_received
                update_data['quantity_remaining'] = quantity_received
            
            if cost_price is not None:
                update_data['cost_price'] = cost_price
            
            if expiry_date:
                if isinstance(expiry_date, str):
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(expiry_date)
                        # If no timezone info, assume UTC
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        update_data['expiry_date'] = parsed_date
                    except Exception as e:
                        logger.warning(f"Could not parse expiry_date '{expiry_date}': {e}")
                else:
                    update_data['expiry_date'] = expiry_date
            
            # Set date_received - if not provided, use current time (when stock was received)
            if date_received:
                if isinstance(date_received, str):
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(date_received)
                        # If no timezone info, assume UTC
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        update_data['date_received'] = parsed_date
                    except Exception as e:
                        logger.warning(f"Could not parse date_received '{date_received}': {e}")
                        update_data['date_received'] = current_time
                else:
                    update_data['date_received'] = date_received
            else:
                # Always set date_received when activating (marking as received)
                update_data['date_received'] = current_time
            
            if notes:
                existing_notes = batch.get('notes', '')
                update_data['notes'] = f"{existing_notes} | {notes}" if existing_notes else notes
            
            # Update the batch
            result = self.batch_collection.update_one(
                {'_id': batch['_id']},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                # Update product stock
                product = self.product_collection.find_one({'_id': product_id})
                if product:
                    # Recalculate total stock from all active batches
                    active_batches = list(self.batch_collection.find({
                        'product_id': product_id,
                        'status': 'active'
                    }))
                    new_stock = sum(b.get('quantity_remaining', 0) for b in active_batches)
                    
                    self.product_collection.update_one(
                        {'_id': product_id},
                        {'$set': {'total_stock': new_stock, 'updated_at': datetime.utcnow()}}
                    )
                    
                    # Update expiry summary
                    self.update_product_expiry_summary(product_id)
                    
                    # Send notification
                    self._send_batch_notification(
                        'activated',
                        product.get('product_name', 'Unknown Product'),
                        additional_metadata={
                            'batch_number': batch_number,
                            'quantity': update_data.get('quantity_received', batch['quantity_received']),
                            'supplier_id': supplier_id
                        }
                    )
                
                return self.batch_collection.find_one({'_id': batch['_id']})
            else:
                raise Exception("Failed to activate batch")
        
        except Exception as e:
            raise Exception(f"Error activating batch: {str(e)}")

    # ================================================================
    # FIFO STOCK DEDUCTION (Enhanced for Online Transactions)
    # ================================================================
    
    def deduct_stock_fifo(self, product_id, quantity_needed, transaction_date, transaction_info=None):
        """
        Deduct stock from batches using FIFO with usage_history tracking
        
        Args:
            product_id: Product ID (PROD-##### format)
            quantity_needed: Quantity to deduct
            transaction_date: Transaction timestamp
            transaction_info: Optional dict with {
                'transaction_id': str,
                'adjusted_by': str (cashier_id or customer_id),
                'source': 'pos_sale' | 'online_order' | 'manual_adjustment'
            }
        
        Returns:
            List of batch deductions with tracking info
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 FIFO Stock Deduction")
            print(f"   Product: {product_id}")
            print(f"   Quantity needed: {quantity_needed}")
            if transaction_info:
                print(f"   Transaction: {transaction_info.get('transaction_id', 'N/A')}")
                print(f"   Source: {transaction_info.get('source', 'N/A')}")
            print(f"{'='*60}\n")
            
            # Use batch_collection (PANN_POS naming convention)
            batches = list(self.batch_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }).sort('expiry_date', 1))
            
            if not batches:
                raise ValueError(f"No active batches available for product {product_id}")
            
            # Calculate total available stock
            total_available = sum(batch['quantity_remaining'] for batch in batches)
            
            print(f"📦 Found {len(batches)} active batches")
            print(f"   Total available: {total_available}")
            print(f"   Requested: {quantity_needed}\n")
            
            if total_available < quantity_needed:
                raise ValueError(
                    f"Insufficient stock in batches. "
                    f"Need {quantity_needed}, have {total_available}"
                )
            
            batch_deductions = []
            remaining_quantity = quantity_needed
            
            for batch in batches:
                if remaining_quantity <= 0:
                    break
                
                # Calculate how much to deduct from this batch
                deduct_amount = min(remaining_quantity, batch['quantity_remaining'])
                new_quantity = batch['quantity_remaining'] - deduct_amount
                
                print(f"   Batch {batch['batch_number']}:")
                print(f"      Before: {batch['quantity_remaining']}")
                print(f"      Deduct: {deduct_amount}")
                print(f"      After: {new_quantity}")
                print(f"      Expires: {batch['expiry_date']}")
                
                # ✅ CREATE USAGE_HISTORY ENTRY
                usage_entry = {
                    'timestamp': transaction_date,
                    'quantity_used': deduct_amount,
                    'remaining_after': new_quantity,
                    'adjustment_type': 'sale',
                    'adjusted_by': transaction_info.get('adjusted_by') if transaction_info else None,
                    'approved_by': None,
                    'notes': f"Transaction {transaction_info.get('transaction_id', 'N/A')}" if transaction_info else '',
                    'source': transaction_info.get('source', 'pos_sale') if transaction_info else 'pos_sale'
                }
                
                # Update batch with usage history
                self.batch_collection.update_one(
                    {'_id': batch['_id']},
                    {
                        '$set': {
                            'quantity_remaining': new_quantity,
                            'status': 'depleted' if new_quantity == 0 else 'active',
                            'updated_at': transaction_date
                        },
                        '$push': {
                            'usage_history': usage_entry
                        }
                    }
                )
                
                # Track batch usage for transaction record
                batch_deductions.append({
                    'batch_id': batch['_id'],
                    'batch_number': batch['batch_number'],
                    'quantity_deducted': deduct_amount,
                    'expiry_date': batch['expiry_date'],
                    'cost_price': batch.get('cost_price', 0)
                })
                
                remaining_quantity -= deduct_amount
                
                if new_quantity == 0:
                    print(f"      ⚠️  Batch depleted!\n")
                else:
                    print(f"      ✅ Updated\n")
            
            print(f"{'='*60}")
            print(f"✅ FIFO deduction complete")
            print(f"   Used {len(batch_deductions)} batches")
            print(f"{'='*60}\n")
            
            return batch_deductions
            
        except Exception as e:
            logger.error(f"❌ FIFO deduction failed: {str(e)}")
            raise
    
    def check_batch_availability(self, product_id, quantity_needed):
        """
        Check if sufficient stock is available in batches
        
        Args:
            product_id: Product ID
            quantity_needed: Quantity to check
        
        Returns:
            dict: {
                'available': bool,
                'total_stock': int,
                'batches_count': int
            }
        """
        try:
            batches = list(self.batch_collection.find({
                'product_id': product_id,
                'status': 'active',
                'quantity_remaining': {'$gt': 0}
            }))
            
            total_stock = sum(batch['quantity_remaining'] for batch in batches)
            
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
        Restore stock to batches (for cancellations/voids) with usage_history tracking
        
        Args:
            batches_used: List of batch deductions to restore
            transaction_date: Restoration timestamp
            transaction_info: Optional dict with {
                'transaction_id': str,
                'adjusted_by': str,
                'reason': str
            }
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 Restoring Stock to Batches")
            if transaction_info:
                print(f"   Transaction: {transaction_info.get('transaction_id', 'N/A')}")
                print(f"   Reason: {transaction_info.get('reason', 'N/A')}")
            print(f"{'='*60}\n")
            
            for batch_info in batches_used:
                batch_id = batch_info['batch_id']
                quantity_to_restore = batch_info['quantity_deducted']
                
                print(f"   Restoring to batch {batch_info['batch_number']}:")
                print(f"      Quantity: +{quantity_to_restore}")
                
                batch = self.batch_collection.find_one({'_id': batch_id})
                
                if not batch:
                    logger.warning(f"      ⚠️  Batch {batch_id} not found, skipping")
                    continue
                
                new_quantity = batch['quantity_remaining'] + quantity_to_restore
                
                print(f"      Before: {batch['quantity_remaining']}")
                print(f"      After: {new_quantity}")
                
                # ✅ CREATE USAGE_HISTORY ENTRY FOR RESTORATION
                usage_entry = {
                    'timestamp': transaction_date,
                    'quantity_used': -quantity_to_restore,  # Negative = restoration
                    'remaining_after': new_quantity,
                    'adjustment_type': 'restoration',
                    'adjusted_by': transaction_info.get('adjusted_by') if transaction_info else None,
                    'approved_by': None,
                    'notes': transaction_info.get('reason', 'Stock restored from cancelled/voided transaction') if transaction_info else 'Stock restored',
                    'source': 'restoration'
                }
                
                # Update batch with restoration
                self.batch_collection.update_one(
                    {'_id': batch_id},
                    {
                        '$set': {
                            'quantity_remaining': new_quantity,
                            'status': 'active',  # Reactivate if was depleted
                            'updated_at': transaction_date
                        },
                        '$push': {
                            'usage_history': usage_entry
                        }
                    }
                )
                
                print(f"      ✅ Restored\n")
            
            print(f"{'='*60}")
            print(f"✅ Stock restoration complete")
            print(f"{'='*60}\n")
            
        except Exception as e:
            logger.error(f"❌ Stock restoration failed: {str(e)}")
            raise
        
