import unittest
import warnings
import sys
import os
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime

# Add backend to sys.path to ensure app module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestCategoryService(unittest.TestCase):

    def setUp(self):
        # Suppress DeprecationWarning from service code (datetime.utcnow)
        warnings.simplefilter('ignore', category=DeprecationWarning)

        # Patch app.utils to avoid ImportError during model imports
        self.utils_patcher = patch.dict('sys.modules', {
            'app.utils': MagicMock(),
            'app.utils.counters': MagicMock(),
            'notifications.services': MagicMock()
        })
        self.utils_patcher.start()

        # Import the module explicitly to ensure it's loaded before patching its members
        import app.services.category_service
        self.category_service_module = app.services.category_service

        # Patch external dependencies used in CategoryService
        self.audit_patcher = patch('app.services.category_service.AuditLogService')
        self.notification_patcher = patch('app.services.category_service.notification_service')
        self.counter_patcher = patch('app.services.category_service.counter_service')
        self.category_model_patcher = patch('app.services.category_service.Category')
        self.product_model_patcher = patch('app.services.category_service.Product')
        self.subcategory_item_patcher = patch('app.services.category_service.SubCategoryItem')

        self.MockAuditLogService = self.audit_patcher.start()
        self.mock_notification_service = self.notification_patcher.start()
        self.mock_counter_service = self.counter_patcher.start()
        self.MockCategory = self.category_model_patcher.start()
        self.MockProduct = self.product_model_patcher.start()
        self.MockSubCategoryItem = self.subcategory_item_patcher.start()

        # Setup default behavior for ensure_uncategorized_category_exists to avoid side effects during init
        # Assume it exists by default so __init__ doesn't try to create it
        self.MockCategory.get_by_id.return_value = MagicMock()
        
        # Instantiate service
        self.service = self.category_service_module.CategoryService()
        
        # Mock the audit service instance attached to self.service
        self.service.audit_service = self.MockAuditLogService.return_value

    def tearDown(self):
        self.audit_patcher.stop()
        self.notification_patcher.stop()
        self.counter_patcher.stop()
        self.category_model_patcher.stop()
        self.product_model_patcher.stop()
        self.subcategory_item_patcher.stop()
        self.utils_patcher.stop()

    def test_ensure_uncategorized_category_exists_already_exists(self):
        # Setup
        mock_category = MagicMock()
        mock_category.sub_categories = []
        mock_category.to_dict.return_value = {"category_id": "UNCTGRY-001"}
        self.MockCategory.get_by_id.return_value = mock_category
        
        # Execute
        result = self.service.ensure_uncategorized_category_exists()
        
        # Verify
        self.MockCategory.get_by_id.assert_called_with('UNCTGRY-001')
        # Should add default subcategory if missing
        mock_category.add_subcategory.assert_called_with(
            name='None',
            description='Default holding subcategory for uncategorized products'
        )
        self.assertEqual(result, {"category_id": "UNCTGRY-001"})

    def test_ensure_uncategorized_category_exists_creates_new(self):
        # Setup
        self.MockCategory.get_by_id.return_value = None
        self.MockCategory.get_by_name.return_value = None
        
        mock_new_category = MagicMock()
        mock_new_category.to_dict.return_value = {"category_id": "UNCTGRY-001", "name": "Uncategorized"}
        self.MockCategory.return_value = mock_new_category
        
        # Execute
        result = self.service.ensure_uncategorized_category_exists()
        
        # Verify
        self.MockCategory.assert_called_with(
            pk="categories",
            sk="UNCTGRY-001",
            category_name="Uncategorized",
            description="Default category for products without specific categorization",
            status="active",
            isDeleted=False,
            date_created=ANY,
            last_updated=ANY
        )
        mock_new_category.save.assert_called()
        mock_new_category.add_subcategory.assert_called()
        self.mock_notification_service.create_notification.assert_called()

    def test_create_category_success(self):
        # Setup
        category_data = {
            "category_name": "Test Category",
            "description": "Test Description",
            "image_url": "http://example.com/icon.png",
            "sub_categories": [{"name": "Sub 1", "description": "Sub Desc"}]
        }
        current_user = {"username": "admin"}
        
        self.MockCategory.get_by_name.return_value = None # No duplicate
        self.mock_counter_service.get_next_id.side_effect = ["CAT-0001", "SUB-00001"]
        
        mock_category_instance = MagicMock()
        mock_category_instance.to_dict.return_value = {"category_id": "CAT-0001", "category_name": "Test Category"}
        mock_category_instance.sub_categories = []
        self.MockCategory.return_value = mock_category_instance

        # Execute
        result = self.service.create_category(category_data, current_user)

        # Verify
        self.MockCategory.get_by_name.assert_called_with("Test Category")
        self.mock_counter_service.get_next_id.assert_any_call('category_seq', prefix='CAT-', width=4)
        
        self.MockCategory.assert_called_with(
            pk="categories",
            sk="CAT-0001",
            category_name="Test Category",
            description="Test Description",
            icon="http://example.com/icon.png",
            sort_order=0,
            status="active",
            isDeleted=False,
            date_created=ANY,
            last_updated=ANY
        )
        
        # Verify subcategory creation
        self.mock_counter_service.get_next_id.assert_any_call('subcategory_seq', prefix='SUB-', width=5)
        self.MockSubCategoryItem.assert_called_with(
            subcategory_id="SUB-00001",
            name="Sub 1",
            description="Sub Desc",
            created_at=ANY,
            status='active'
        )
        
        mock_category_instance.save.assert_called()
        self.mock_notification_service.create_notification.assert_called()
        self.service.audit_service.log_category_create.assert_called()
        
        self.assertEqual(result, {"category_id": "CAT-0001", "category_name": "Test Category"})

    def test_create_category_duplicate_name(self):
        # Setup
        category_data = {"category_name": "Existing Category"}
        existing_cat = MagicMock()
        existing_cat.isDeleted = False
        self.MockCategory.get_by_name.return_value = existing_cat

        # Execute & Verify
        with self.assertRaises(Exception) as context:
            self.service.create_category(category_data)
        
        self.assertIn("already exists", str(context.exception))

    def test_get_all_categories(self):
        # Setup
        mock_cat1 = MagicMock()
        mock_cat1.to_dict.return_value = {"category_id": "CAT-1", "sub_categories": [{"name": "Sub1"}]}
        mock_cat1.sk = "CAT-1"
        
        mock_cat2 = MagicMock()
        mock_cat2.to_dict.return_value = {"category_id": "CAT-2"}
        mock_cat2.sk = "CAT-2"
        
        self.MockCategory.get_all_categories.return_value = [mock_cat1, mock_cat2]
        
        # Mock product counts
        self.MockProduct.query_by_category.return_value = [] # Empty list for count 0

        # Execute
        result = self.service.get_all_categories()

        # Verify
        self.MockCategory.get_all_categories.assert_called_with(include_deleted=False)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['category_id'], "CAT-1")
        # Check if product count logic was called (it calls get_subcategory_product_count)
        self.MockProduct.query_by_category.assert_called()

    def test_update_category(self):
        # Setup
        category_id = "CAT-0001"
        update_data = {"category_name": "Updated Name"}
        current_user = {"username": "admin"}
        
        mock_category = MagicMock()
        mock_category.category_name = "Old Name"
        mock_category.to_dict.return_value = {"category_id": category_id, "category_name": "Updated Name"}
        self.MockCategory.get_by_id.return_value = mock_category

        # Execute
        result = self.service.update_category(category_id, update_data, current_user)

        # Verify
        self.MockCategory.get_by_id.assert_called_with(category_id)
        mock_category.update_category.assert_called_with(category_name="Updated Name")
        self.mock_notification_service.create_notification.assert_called()
        self.service.audit_service.log_action.assert_called()
        self.assertEqual(result['category_name'], "Updated Name")

    def test_soft_delete_category(self):
        # Setup
        category_id = "CAT-0001"
        current_user = {"username": "admin"}
        
        mock_category = MagicMock()
        mock_category.isDeleted = False
        mock_category.category_name = "Test Cat"
        mock_category.to_dict.return_value = {"category_id": category_id}
        self.MockCategory.get_by_id.return_value = mock_category

        # Execute
        result = self.service.soft_delete_category(category_id, current_user)

        # Verify
        self.assertTrue(result)
        mock_category.soft_delete.assert_called()
        self.mock_notification_service.create_notification.assert_called()
        self.service.audit_service.log_action.assert_called()

    def test_add_subcategory(self):
        # Setup
        category_id = "CAT-0001"
        subcategory_data = {"name": "New Sub", "description": "Desc"}
        current_user = {"username": "admin"}
        
        mock_category = MagicMock()
        mock_category.category_name = "Parent Cat"
        mock_category.sub_categories = []
        self.MockCategory.get_by_id.return_value = mock_category
        self.mock_counter_service.get_next_id.return_value = "SUB-00001"

        # Execute
        result = self.service.add_subcategory(category_id, subcategory_data, current_user)

        # Verify
        self.assertTrue(result)
        self.MockCategory.get_by_id.assert_called_with(category_id)
        
        self.MockSubCategoryItem.assert_called_with(
            subcategory_id="SUB-00001",
            name="New Sub",
            description="Desc",
            icon=None,
            sort_order=0,
            status="active",
            created_at=ANY
        )
        
        self.assertEqual(len(mock_category.sub_categories), 1)
        mock_category.save.assert_called()
        self.mock_notification_service.create_notification.assert_called()

    def test_remove_subcategory(self):
        # Setup
        category_id = "CAT-0001"
        subcategory_name = "Sub To Remove"
        
        mock_category = MagicMock()
        mock_sub = MagicMock()
        mock_sub.name = subcategory_name
        mock_sub.subcategory_id = "SUB-123"
        mock_category.sub_categories = [mock_sub]
        self.MockCategory.get_by_id.return_value = mock_category

        # Execute
        result = self.service.remove_subcategory(category_id, subcategory_name)

        # Verify
        self.assertTrue(result)
        mock_category.remove_subcategory.assert_called_with("SUB-123")
        self.mock_notification_service.create_notification.assert_called()

    def test_add_product_to_subcategory(self):
        # Setup
        category_id = "CAT-0001"
        subcategory_name = "Sub 1"
        product_id = "PROD-0001"
        
        mock_category = MagicMock()
        mock_sub = MagicMock()
        mock_sub.name = subcategory_name
        mock_category.sub_categories = [mock_sub]
        self.MockCategory.get_by_id.return_value = mock_category
        
        mock_product = MagicMock()
        mock_product.sk = product_id
        mock_product.product_name = "Test Product"
        self.MockProduct.get_by_id.return_value = mock_product

        # Execute
        result = self.service.add_product_to_subcategory(category_id, subcategory_name, product_id)

        # Verify
        self.assertTrue(result['success'])
        mock_product.update_product.assert_called_with(
            category_id=category_id,
            subcategory_name=subcategory_name
        )

    def test_remove_product_from_subcategory(self):
        # Setup
        category_id = "CAT-0001"
        subcategory_name = "Sub 1"
        product_id = "PROD-0001"
        
        mock_category = MagicMock()
        mock_category.sub_categories = [] # Mocking subcategories list is tricky if we don't iterate it in service
        # But the service does: if not category: raise...
        self.MockCategory.get_by_id.return_value = mock_category
        
        mock_product = MagicMock()
        mock_product.sk = product_id
        mock_product.product_name = "Test Product"
        self.MockProduct.get_by_id.return_value = mock_product

        # Execute
        result = self.service.remove_product_from_subcategory(category_id, subcategory_name, product_id)

        # Verify
        self.assertTrue(result['success'])
        # Should move to Uncategorized
        mock_product.update_product.assert_called_with(
            category_id="UNCTGRY-001",
            subcategory_name="General"
        )

if __name__ == '__main__':
    unittest.main()
