from models.Product import Product
from pynamodb.exceptions import DoesNotExist, PutError, DeleteError, UpdateError
import logging

logger = logging.getLogger(__name__)

class ProductService:
    """
    Service layer for interacting with the Product model (DynamoDB).
    Provides basic CRUD operations.
    """

    @staticmethod
    def create_product(data: dict):
        """
        Creates a new product.
        
        Args:
            data (dict): A dictionary containing product attributes. 
                         Must match the arguments for Product.create_product.
                         Required keys: product_name, sku, category_id, cost_price, selling_price, unit.
        
        Returns:
            Product: The created product object.
        
        Raises:
            ValueError: If required data is missing or if creation fails.
        """
        try:
            # The create_product method on the model already handles validation and creation logic.
            product = Product.create_product(**data)
            logger.info(f"Successfully created product {product.sk}")
            return product
        except (PutError, ValueError) as e:
            logger.error(f"Error creating product: {str(e)}")
            raise ValueError(f"Could not create product: {str(e)}") from e

    @staticmethod
    def get_product_by_id(product_id: str):
        """
        Retrieves a single product by its ID (e.g., 'PROD-00001').

        Args:
            product_id (str): The unique identifier of the product.

        Returns:
            Product: The found product object, or None if not found.
        """
        try:
            product = Product.get_by_id(product_id)
            return product
        except DoesNotExist:
            logger.warning(f"Product with ID {product_id} not found.")
            return None
        except Exception as e:
            logger.error(f"Error retrieving product {product_id}: {str(e)}")
            raise

    @staticmethod
    def get_all_products():
        """
        Retrieves all active (not soft-deleted) products.

        Returns:
            list[Product]: A list of all active product objects.
        """
        try:
            return Product.get_all_active_products()
        except Exception as e:
            logger.error(f"Error retrieving all products: {str(e)}")
            return []

    @staticmethod
    def update_product(product_id: str, data: dict):
        """
        Updates an existing product.

        Args:
            product_id (str): The ID of the product to update.
            data (dict): A dictionary with the fields to update.

        Returns:
            Product: The updated product object.

        Raises:
            ValueError: If the product is not found or the update fails.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")
        
        try:
            # The update_product method in the model handles the update logic
            product.update_product(**data)
            logger.info(f"Successfully updated product {product_id}")
            # Re-fetch the instance to ensure the returned object is up-to-date
            return ProductService.get_product_by_id(product_id)
        except UpdateError as e:
            logger.error(f"Error updating product {product_id}: {str(e)}")
            raise ValueError(f"Could not update product: {str(e)}") from e

    @staticmethod
    def delete_product(product_id: str, hard_delete: bool = False, deleted_by: str = "system", reason: str = "Deleted via service"):
        """
        Deletes a product, either by soft-deleting or permanently removing it.

        Args:
            product_id (str): The ID of the product to delete.
            hard_delete (bool): If True, permanently delete the product. 
                                If False (default), soft-delete the product.
            deleted_by (str): Identifier for who performed the deletion (for soft-delete).
            reason (str): Reason for the deletion (for soft-delete).


        Returns:
            bool: True if deletion was successful, False otherwise.
        
        Raises:
            ValueError: If the product is not found.
        """
        product = ProductService.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        try:
            if hard_delete:
                # This is the standard pynamodb delete method
                product.delete()
                logger.info(f"Successfully hard-deleted product {product_id}")
            else:
                # This uses the custom soft_delete method from the model
                product.soft_delete(deleted_by=deleted_by, reason=reason)
                logger.info(f"Successfully soft-deleted product {product_id}")
            return True
        except (DeleteError, UpdateError, ValueError) as e:
            logger.error(f"Error deleting product {product_id}: {str(e)}")
            return False