import unittest
import warnings
import sys
import os
from unittest.mock import MagicMock, patch, ANY
from pynamodb.exceptions import DoesNotExist, PutError, DeleteError, UpdateError

# Add backend to sys.path to ensure app module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestProductService(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', category=DeprecationWarning)
        
        # Patch app.utils to avoid ImportError from the Product model during service import.
        # This allows us to test the service in isolation.
        self.utils_patcher = patch.dict('sys.modules', {
            'app.utils': MagicMock(),
        })
        self.utils_patcher.start()

        # Import the service module after its dependencies have been patched
        import app.services.product_service
        self.product_service_module = app.services.product_service

        # Patch the Product model within the service module's namespace
        self.product_model_patcher = patch('app.services.product_service.Product')
        self.MockProduct = self.product_model_patcher.start()

        # Patch the logger to suppress output
        self.logger_patcher = patch('app.services.product_service.logger')
        self.mock_logger = self.logger_patcher.start()
        
        self.service = self.product_service_module.ProductService()

    def tearDown(self):
        self.product_model_patcher.stop()
        self.logger_patcher.stop()
        self.utils_patcher.stop()

    def test_create_product_success(self):
        """Test successful creation of a product."""
        product_data = {'product_name': 'Test Product', 'sku': 'TP-01'}
        mock_created_product = MagicMock()
        self.MockProduct.create_product.return_value = mock_created_product
        result = self.service.create_product(product_data)
        self.MockProduct.create_product.assert_called_once_with(**product_data)
        self.assertEqual(result, mock_created_product)

    def test_create_product_failure(self):
        """Test product creation failure."""
        product_data = {'product_name': 'Test Product'}
        self.MockProduct.create_product.side_effect = ValueError("Creation failed")
        with self.assertRaises(ValueError):
            self.service.create_product(product_data)

    def test_get_product_by_id_found(self):
        """Test retrieving a product by ID when it exists."""
        product_id = 'PROD-00001'
        mock_product = MagicMock()
        self.MockProduct.get_by_id.return_value = mock_product
        result = self.service.get_product_by_id(product_id)
        self.MockProduct.get_by_id.assert_called_once_with(product_id)
        self.assertEqual(result, mock_product)

    def test_get_product_by_id_not_found(self):
        """Test retrieving a product by ID when it does not exist."""
        product_id = 'PROD-00002'
        self.MockProduct.get_by_id.return_value = None
        result = self.service.get_product_by_id(product_id)
        self.assertIsNone(result)

    def test_get_all_products(self):
        """Test retrieving all active products."""
        mock_products_list = [MagicMock(), MagicMock()]
        self.MockProduct.get_all_active_products.return_value = mock_products_list
        result = self.service.get_all_products()
        self.assertEqual(result, mock_products_list)

    def test_update_product_success(self):
        """Test successful update of a product."""
        product_id = 'PROD-00001'
        update_data = {'product_name': 'Updated Name'}
        mock_product_instance = MagicMock()
        refreshed_mock_product = MagicMock()
        self.MockProduct.get_by_id.side_effect = [mock_product_instance, refreshed_mock_product]
        result = self.service.update_product(product_id, update_data)
        mock_product_instance.update_product.assert_called_once_with(**update_data)
        self.assertEqual(result, refreshed_mock_product)

    def test_update_product_not_found(self):
        """Test updating a product that does not exist."""
        product_id = 'PROD-00002'
        self.MockProduct.get_by_id.return_value = None
        with self.assertRaises(ValueError):
            self.service.update_product(product_id, {})

    def test_delete_product_soft_delete(self):
        """Test soft-deleting a product."""
        product_id = 'PROD-00001'
        mock_product_instance = MagicMock()
        self.MockProduct.get_by_id.return_value = mock_product_instance
        result = self.service.delete_product(product_id, hard_delete=False)
        self.assertTrue(result)
        mock_product_instance.soft_delete.assert_called_once()

    def test_delete_product_hard_delete(self):
        """Test hard-deleting a product."""
        product_id = 'PROD-00001'
        mock_product_instance = MagicMock()
        self.MockProduct.get_by_id.return_value = mock_product_instance
        result = self.service.delete_product(product_id, hard_delete=True)
        self.assertTrue(result)
        mock_product_instance.delete.assert_called_once()

if __name__ == '__main__':
    unittest.main()