from datetime import datetime

from ...database import db_manager

class PromoConnection:
    def __init__(self):
        self.db = db_manager.get_database()
        self.promotions_collection = self.db.promotions
        self.categories_collection = self.db.categories
        self.products_collection = self.db.products  # Fixed typo
        self.sales_collection = self.db.sales

    def convert_object_id(self, document):
        """Convert ObjectId to string for JSON serialization - Enhanced version"""
        if document is None:
            return document
        
        if isinstance(document, list):
            return [self.convert_object_id(item) for item in document]
        
        if isinstance(document, dict):
            converted = {}
            for key, value in document.items():
                if isinstance(value, (dict, list)):
                    converted[key] = self.convert_object_id(value)
                else:
                    converted[key] = value
            return converted
        
        return document

    # ================================================================
    # STOCK NOTIFICATION METHODS
    # ================================================================

    def check_low_stock_warnings(self, checkout_data, current_user=None):
        """Check if any products will go below low stock threshold and send notifications"""
        warnings = []
        
        for item in checkout_data:
            product = self.products_collection.find_one({'_id': item['product_id']})
            
            if product:
                current_stock = product.get('stock', 0)
                quantity_sold = item['quantity']
                low_stock_threshold = product.get('low_stock_threshold', 5)
                
                new_stock = current_stock - quantity_sold
                product_name = product.get('product_name', 'Unknown Product')
                
                # Check for different stock warning levels
                if new_stock <= 0:
                    warning_msg = f"⚠️ {product_name} will be OUT OF STOCK!"
                    warnings.append(warning_msg)
                    
                    # Send OUT OF STOCK notification
                    self._send_stock_notification(
                        'out_of_stock', 
                        product, 
                        current_stock, 
                        new_stock, 
                        quantity_sold,
                        current_user
                    )
                    
                elif new_stock <= low_stock_threshold:
                    warning_msg = f"🔶 {product_name} will be LOW STOCK ({new_stock} remaining)"
                    warnings.append(warning_msg)
                    
                    # Send LOW STOCK notification
                    self._send_stock_notification(
                        'low_stock', 
                        product, 
                        current_stock, 
                        new_stock, 
                        quantity_sold,
                        current_user
                    )
        
        return warnings

    def _send_stock_notification(self, alert_type, product, current_stock, new_stock, quantity_sold, current_user=None):
        """Send notification for stock-related alerts"""
        try:
            product_name = product.get('product_name', 'Unknown Product')
            product_id = str(product.get('_id', ''))
            low_stock_threshold = product.get('low_stock_threshold', 5)
            
            # Configure notification based on alert type
            if alert_type == 'out_of_stock':
                title = "⚠️ PRODUCT OUT OF STOCK"
                message = f"'{product_name}' is now OUT OF STOCK after selling {quantity_sold} units"
                priority = "urgent"
                
            elif alert_type == 'low_stock':
                title = "🔶 LOW STOCK ALERT"
                message = f"'{product_name}' is running low on stock. Only {new_stock} units remaining (threshold: {low_stock_threshold})"
                priority = "high"
                
            else:
                return  # Unknown alert type
            
            # Common metadata for both alert types
            metadata = {
                "product_id": product_id,
                "product_name": product_name,
                "sku": product.get('SKU', ''),
                "category_id": product.get('category_id', ''),
                "current_stock": current_stock,
                "new_stock": new_stock,
                "quantity_sold": quantity_sold,
                "low_stock_threshold": low_stock_threshold,
                "alert_type": alert_type,
                "action_type": "stock_alert",
                "cashier_id": current_user.get('_id') if current_user else None,
                "cashier_name": current_user.get('username') if current_user else None,
                "cost_price": product.get('cost_price', 0),
                "selling_price": product.get('selling_price', 0),
                "supplier_id": product.get('supplier_id'),
                "reorder_suggested": new_stock <= low_stock_threshold
            }
            
            # Import notification service
            from notifications.services import notification_service
            
            # Send the notification
            notification_service.create_notification(
                title=title,
                message=message,
                priority=priority,
                notification_type="inventory",  # Different type for inventory alerts
                metadata=metadata
            )
            
            print(f"📢 Stock notification sent: {title} for {product_name}")
            
        except Exception as notification_error:
            # Log the notification error but don't fail the main operation
            print(f"❌ Failed to create {alert_type} notification for product {product.get('product_name', 'Unknown')}: {notification_error}")

    def check_all_low_stock_products(self):
        """Check all products for low stock and send batch notification - Fixed version"""
        try:
            # Find all products that are at or below their low stock threshold
            low_stock_products = list(self.products_collection.find({
                "$expr": {
                    "$lte": ["$stock", "$low_stock_threshold"]
                },
                "isDeleted": {"$ne": True}
            }))
            
            # 🔧 FIX: Convert ObjectIds to strings
            low_stock_products = [self.convert_object_id(product) for product in low_stock_products]
            
            if low_stock_products:
                # Send batch notification
                product_names = [p.get('product_name', 'Unknown') for p in low_stock_products]
                
                try:
                    from notifications.services import notification_service
                    
                    notification_service.create_notification(
                        title=f"📊 INVENTORY REPORT: {len(low_stock_products)} Products Need Restocking",
                        message=f"The following products are running low: {', '.join(product_names[:5])}{'...' if len(product_names) > 5 else ''}",
                        priority="medium",
                        notification_type="inventory",
                        metadata={
                            "alert_type": "batch_low_stock_report",
                            "low_stock_count": len(low_stock_products),
                            "product_ids": [str(p['_id']) for p in low_stock_products],
                            "product_names": product_names,
                            "action_type": "inventory_report"
                        }
                    )
                except Exception as notification_error:
                    print(f"❌ Failed to send notification: {notification_error}")
                    # Continue without notification
                    
            return low_stock_products
            
        except Exception as e:
            print(f"❌ Error checking all low stock products: {e}")
            return []

    def validate_stock_availability(self, checkout_data):
        """Ensure all items have sufficient stock before processing sale"""
        for item in checkout_data:
            product = self.products_collection.find_one({'_id': item['product_id']})
            
            if not product:
                return {
                    'valid': False,
                    'message': f"Product {item['product_id']} not found"
                }
            
            current_stock = product.get('stock', 0)
            requested_quantity = item['quantity']
            
            if current_stock < requested_quantity:
                return {
                    'valid': False,
                    'message': f"Insufficient stock for {product['product_name']}. Available: {current_stock}, Requested: {requested_quantity}"
                }
        
        return {'valid': True, 'message': 'All items available'}

    # ================================================================
    # RECEIPT AND INVENTORY METHODS
    # ================================================================

    def generate_receipt(self, sales_record):
        """Generate receipt data"""
        return {
            'receipt_id': sales_record['sale_id'],
            'items': sales_record['items'],
            'subtotal': sales_record['total_amount'],
            'discount': sales_record['total_discount'],
            'total': sales_record['final_amount'],
            'timestamp': sales_record['transaction_date']
        }

    def update_inventory(self, checkout_data):
        """Reduce product quantities after sale"""
        try:
            for item in checkout_data:
                print(f"🔄 Processing item: {item}")
                
                # Get product details
                product_id = item["product_id"]
                quantity_sold = item["quantity"]
                
                print(f"📦 Reducing stock for product {product_id} by {quantity_sold}")
                
                # Update inventory - use 'stock' field
                result = self.products_collection.update_one(
                    {'_id': product_id},
                    {'$inc': {'stock': -quantity_sold}}
                )
                
                # Check if update was successful
                if result.modified_count == 1:
                    print(f"✅ Stock updated for product {product_id}")
                else:
                    print(f"⚠️ Warning: Product {product_id} not found or not updated")
                    
        except Exception as e:
            print(f"❌ Error updating inventory: {str(e)}")
            raise Exception(f"Error updating inventory: {str(e)}")

    # ================================================================
    # SALES AND TRANSACTION METHODS
    # ================================================================

    def create_sales(self, sales_data):
        """Creates a sales transaction record in the database"""
        try:
            required_fields = ['items','total_amount']
            for field in required_fields:
                if field not in sales_data:
                    return{
                        'success': False,
                        'message': f'Missing required field: {field}',
                        'data': None
                    }
                
            sales_record ={
                'sale_id': str(sales_data.get("product_id")),  # Generate unique sale ID
                'items': sales_data['items'],  # List of purchased items
                'total_amount': sales_data['total_amount'],
                'total_discount': sales_data.get('total_discount', 0),
                'final_amount': sales_data.get('final_amount', sales_data['total_amount']),
                'promotion_applied': sales_data.get('promotion_applied', None),
                'payment_method': sales_data.get('payment_method', 'cash'),
                'cashier_id': sales_data.get('cashier_id', None),
                'customer_id': sales_data.get('customer_id', None),
                'transaction_date': datetime.utcnow(),
                'status': 'completed',
                'created_at': datetime.utcnow(),
                'last_updated': datetime.utcnow()
            }

            result = self.sales_collection.insert_one(sales_record)

            if result.inserted_id:
                sales_record['_id'] = str(result.inserted_id)
                print(f"✅ Sales transaction created: {sales_record['sale_id']}")
                print(f"💰 Total amount: ₱{sales_record['final_amount']}")
                if sales_record['total_discount'] > 0:
                    print(f"💸 Discount applied: ₱{sales_record['total_discount']}")
                
                return {
                    'success': True,
                    'message': 'Sales transaction created successfully',
                    'data': sales_record
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to create sales transaction',
                    'data': None
                }

        except Exception as e:
            print(f"❌ Error creating sales transaction: {str(e)}")
            raise Exception(f"Error creating sales transaction: {str(e)}")

    def pos_transaction(self, checkout_data, promotion_name=None, cashier_id=None):
        """Complete POS transaction: apply promotions + save sales record + check stock + update inventory"""
        try:
            # Get current user info for notifications
            current_user = None
            if cashier_id:
                current_user = {'_id': cashier_id, 'username': f'cashier_{cashier_id}'}
            
            # Step 1: Validate stock availability
            stock_validation = self.validate_stock_availability(checkout_data)
            if not stock_validation['valid']:
                return {
                    'success': False,
                    'message': stock_validation['message'],
                    'data': None
                }
            
            # Step 2: Check for low stock warnings BEFORE processing sale
            stock_warnings = self.check_low_stock_warnings(checkout_data, current_user)
            
            # Step 3: Apply promotions and calculate totals
            if promotion_name:
                checkoutResult = self.checkout_list(checkout_data, promotion_name)
                total_amount = checkoutResult['final_total']
                discount = checkoutResult['total_discount']
                promo_applied = promotion_name if checkoutResult['success'] else None
            else:
                total_amount = sum(item['price'] * item['quantity'] for item in checkout_data)
                discount = 0
                promo_applied = None

            # Step 4: Prepare sales data
            sales_data = {
                'items': checkout_data,
                'total_amount': sum(item['price'] * item['quantity'] for item in checkout_data),
                'total_discount': discount,
                'final_amount': total_amount,
                'promotion_applied': promo_applied,
                'cashier_id': cashier_id,
                'payment_method': 'cash'
            }

            # Step 5: Save transaction
            sales_result = self.create_sales(sales_data)

            # Step 6: Update inventory after successful sale
            if sales_result['success']:
                self.update_inventory(checkout_data)
                print("📦 Inventory updated successfully")

            # Step 7: Generate receipt
            receipt = None
            if sales_result['success']:
                receipt = self.generate_receipt(sales_result['data'])

            # Step 8: Prepare response
            response = {
                'success': sales_result["success"],
                'message': 'Transaction Complete',
                'checkout_details': {
                    'final_total': total_amount,
                    'total_discount': discount,
                    'promotion_applied': promo_applied
                },
                'sales_record': sales_result['data'],
                'receipt': receipt
            }
            
            # Add stock warnings to response
            if stock_warnings:
                response['stock_warnings'] = stock_warnings
                response['warnings_count'] = len(stock_warnings)
                print(f"⚠️ {len(stock_warnings)} stock warnings generated")
            
            return response
            
        except Exception as e:
            raise Exception(f"Error completing POS transaction: {str(e)}")

    def checkout_list(self, checkout_data, promotion_name):
        """Checks the categories of the products, and see if the products are in the Promotion"""
        try:
            promotion = self.promotions_collection.find_one({
                'promotion_name': promotion_name,
                'status': 'active',
                'isDeleted':{'$ne': True}
            })
            
            if not promotion:
                regular_total = sum(item['price'] * item['quantity'] for item in checkout_data)
                return{
                    'success': False,
                    'final_total': regular_total,
                    'total_discount': 0
                }

            connection_result = self.promotion_product_category_connection(promotion)

            if not connection_result['success']:
                regular_total = sum(item['price'] * item['quantity'] for item in checkout_data)
                return {
                    'success': False,
                    'final_total': regular_total,
                    'total_discount': 0
                }

            affected_subcategories = [sub['sub_category_name'] for sub in connection_result['data']['affected_subcategories']]
        
            # Process checkout items
            final_total = 0
            total_discount = 0
            for item in checkout_data:
                product_id = item['product_id']
                quantity = item['quantity']
                price = item['price']
                item_total = price * quantity
                        
                # Check if this product is in any affected subcategory
                product = self.products_collection.find_one({
                    '_id': product_id,
                    'isDeleted': {'$ne': True}
                })
                        
                if product and product.get('sub_category') in affected_subcategories:
                    # Apply discount
                    if promotion['discount_type'] == 'percentage':
                        discount = item_total * (promotion['discount_value'] / 100)
                    elif promotion['discount_type'] == 'fixed':
                        discount = min(promotion['discount_value'], item_total)
                    else:
                        discount = 0
                            
                    final_total += (item_total - discount)
                    total_discount += discount
                else:
                    final_total += item_total
        
            return {
                'success': True,
                'final_total': final_total,
                'total_discount': total_discount
            }
        except Exception as e:
            print(f"❌ Error creating promotion-category connection: {str(e)}")
            raise Exception(f"Error creating promotion-category connection: {str(e)}")

    def promotion_product_category_connection(self, promotion_data):
        """Creates a connection between these three collections"""
        try:
            promotion_id = promotion_data.get('_id')
            applicable_products = promotion_data.get('applicable_products',[])
            
            if not applicable_products:
                print("No products found")
                return{
                    'success': False,
                    'message': 'No products found in promotion',
                    'data': None
                }
            
            matching_categories = []
            affected_subcategories = []

            for category_name in applicable_products:
                category = self.categories_collection.find_one({
                    'category_name': category_name,
                    'isDeleted': {'$ne':True}
                })

                if category:
                    category = self.convert_object_id(category)
                    matching_categories.append(category)

                    sub_categories = category.get('sub_categories',[])
                    
                    for sub_cat in sub_categories:
                        sub_cat_data={
                            'parent_category_id': category['_id'],
                            'parent_category_name': category['category_name'],
                            'sub_category_name': sub_cat.get('sub_category_name'),
                            'sub_category_id': sub_cat.get('_id') or sub_cat.get('sub_category_id'),
                            'description': sub_cat.get('description', ''),
                            'status': sub_cat.get('status', 'active')
                        }
                        affected_subcategories.append(sub_cat_data)

                else:
                    print(f"Category not Found: {category_name}")

            promotion_connection = {
                'promotion_id': str(promotion_id),
                'promotion_name': promotion_data.get('promotion_name'),
                'discount_type': promotion_data.get('discount_type'),
                'discount_value': promotion_data.get('discount_value'),
                'start_date': promotion_data.get('start_date'),
                'end_date': promotion_data.get('end_date'),
                'status': promotion_data.get('status'),
                'applicable_products': applicable_products,
                'matching_categories': matching_categories,
                'affected_subcategories': affected_subcategories,
                'total_categories_found': len(matching_categories),
                'total_subcategories_affected': len(affected_subcategories),
                'connection_created_at': datetime.utcnow(),
                'last_updated': datetime.utcnow()
            }  
            return {
                'success': True,
                'message': 'Promotion-category connection created successfully',
                'data': promotion_connection
            }
        except Exception as e:
            print(f"❌ Error creating promotion-category connection: {str(e)}")
            raise Exception(f"Error creating promotion-category connection: {str(e)}")