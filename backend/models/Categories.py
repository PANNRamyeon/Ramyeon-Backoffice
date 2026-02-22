"""
Category Model - Following ERD Specification with Enhancements
PK = "category", SK = "CTGY-###" (3-digit format)
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute, Attribute
)
from pynamodb.exceptions import UpdateError
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION
from app.utils.counters import counter_service
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


# Custom DateTime Attribute to handle legacy date formats
class FlexibleDateTimeAttribute(Attribute):
    """
    A DateTime attribute that can handle multiple date formats for backward compatibility
    """
    attr_type = 'S'
    
    def serialize(self, value):
        """Convert datetime to string for storage"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        return str(value)
    
    def deserialize(self, value):
        """Convert string from storage to datetime"""
        if not value:
            return None
        
        # Handle the bad format with extra zeros: '000002025-10-08...'
        if value.startswith('0000'):
            value = value[4:]  # Remove extra zeros
        
        # Try different formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f+0000',
            '%Y-%m-%dT%H:%M:%S+0000',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        
        # If all formats fail, log and return current time
        logger.warning(f"Could not parse datetime: {value}, using current time")
        return datetime.utcnow()


# ============= NESTED MAP ATTRIBUTES =============
class SubCategoryItem(MapAttribute):
    """
    MapAttribute for sub_categories array items
    """
    subcategory_id = UnicodeAttribute()  # Generated with utils.generate_sk
    name = UnicodeAttribute()
    description = UnicodeAttribute(null=True)
    created_at = FlexibleDateTimeAttribute(default=datetime.utcnow)
    status = UnicodeAttribute(default="active")
    sort_order = NumberAttribute(default=0)
    icon = UnicodeAttribute(null=True)  # Icon/Image URL for subcategory


# ============= MAIN CATEGORY MODEL =============
class Category(Model):
    """
    CATEGORY MODEL - Following ERD with Enhancements
    
    ERD Fields:
    - PK = category
    - SK = CTGY-### (3-digit)
    - category_name (String)
    - description (String)
    - status (String)
    - sub_categories (array)
    - isDeleted (boolean)
    - date_created (ISODATE)
    - last_updated (ISODATE)
    
    Enhanced with:
    - sort_order (Number) - for display ordering
    - icon (String) - for category icon/image URL
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        #if DYNAMODB_LOCAL:
        #    host = DYNAMODB_LOCAL_HOST
        
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, default="category", attr_name="PK")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "CTGY-001" (3-digit)
    
    # ============= CATEGORY DETAILS =============
    category_name = UnicodeAttribute()
    description = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="active")  # active, inactive, archived
    
    # ============= ENHANCED FIELDS =============
    sort_order = NumberAttribute(default=0)  # For display ordering
    icon = UnicodeAttribute(null=True)  # URL for category icon/image
    
    # ============= SUB-CATEGORIES =============
    sub_categories = ListAttribute(of=SubCategoryItem, default=list)
    
    # ============= STATUS AND METADATA =============
    isDeleted = BooleanAttribute(default=False)
    date_created = FlexibleDateTimeAttribute(default=datetime.utcnow)
    last_updated = FlexibleDateTimeAttribute(default=datetime.utcnow)
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_category(cls, category_name: str, description: str = None,
                       icon: str = None, sort_order: int = 0) -> 'Category':
        """
        Create a new category with auto-generated 4-digit SK
        
        Args:
            category_name: Name of the category (required)
            description: Category description (optional)
            icon: Icon/Image URL (optional)
            sort_order: Display order (default: 0)
        
        Returns:
            Category: Created and saved category instance
        """
        try:
            if not category_name or not category_name.strip():
                raise ValueError("category_name is required")
            
            # Generate 3-digit SK using the centralized counter service
            # Use 'category' (singular) to match the PK partition name
            sk = counter_service.get_next_id('category')
            
            # Create and save category
            category = cls(
                pk="category",
                sk=sk,
                category_name=category_name.strip(),
                description=description.strip() if description else None,
                icon=icon,
                sort_order=sort_order,
                status="active",
                isDeleted=False,
                date_created=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            category.save()
            
            logger.info(f"Category created: {sk} - '{category_name}'")
            return category
            
        except Exception as e:
            logger.error(f"Failed to create category: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, category_id: str) -> 'Category | None':
        """
        Get category by ID
        
        Args:
            category_id: Format "CTGY-001" or just "001"
        
        Returns:
            Category or None if not found
        """
        try:
            # Ensure proper format
            if not category_id.startswith('CTGY-'):
                category_id = f"CTGY-{category_id.zfill(3)}"  # Pad to 3 digits if needed
            
            return cls.get("category", category_id)
        except cls.DoesNotExist:
            logger.warning(f"Category not found: {category_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching category {category_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_name(cls, category_name: str) -> 'Category | None':
        """
        Get category by exact name match using GSI
        
        Args:
            category_name: Exact category name to find
        
        Returns:
            Category or None if not found
        """
        try:
            # Query main table with filter (efficient for low cardinality items like categories)
            for category in cls.query("category", filter_condition=(cls.category_name == category_name)):
                if not category.isDeleted:
                    return category
            return None
        except Exception as e:
            logger.error(f"Error finding category by name '{category_name}': {str(e)}")
            return None
    
    @classmethod
    def get_by_status(cls, status: str, include_deleted: bool = False) -> list:
        """
        Get categories by status using GSI
        
        Args:
            status: Status to filter by (active, inactive, archived)
            include_deleted: Include soft-deleted categories
        
        Returns:
            list: List of categories with given status
        """
        try:
            categories = []
            condition = cls.status == status
            if not include_deleted:
                condition = condition & (cls.isDeleted == False)
            
            for category in cls.query("category", filter_condition=condition):
                categories.append(category)
            return categories
        except Exception as e:
            logger.error(f"Error getting categories by status {status}: {str(e)}")
            return []
    
    @classmethod
    def get_active_categories(cls) -> list:
        """
        Get all active, non-deleted categories
        
        Returns:
            list: List of active categories
        """
        return cls.get_by_status("active")
    
    @classmethod
    def get_all_categories(cls, include_deleted: bool = False) -> list:
        """
        Get all categories
        
        Args:
            include_deleted: Include soft-deleted categories
        
        Returns:
            list: List of all categories
        """
        try:
            categories = []
            for category in cls.query("category"):
                if include_deleted or not category.isDeleted:
                    categories.append(category)
            return categories
        except Exception as e:
            logger.error(f"Error getting all categories: {str(e)}")
            return []
    
    @classmethod
    def get_category_count(cls, include_deleted: bool = False) -> int:
        """
        Get total number of categories
        
        Args:
            include_deleted: Include soft-deleted categories
        
        Returns:
            int: Number of categories
        """
        try:
            count = 0
            for category in cls.query("category"):
                if include_deleted or not category.isDeleted:
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Error counting categories: {str(e)}")
            return 0
    
    @classmethod
    def search_categories(cls, search_term: str, limit: int = 10) -> list:
        """
        Search categories by name (partial, case-insensitive)
        
        Args:
            search_term: Search term
            limit: Maximum number of categories to return
        
        Returns:
            list: List of matching categories
        """
        try:
            categories = []
            search_term_lower = search_term.lower()
            
            # Scan all active categories
            for category in cls.query("categories", limit=1000):
                if category.isDeleted:
                    continue
                
                if (search_term_lower in category.category_name.lower() or 
                    (category.description and search_term_lower in category.description.lower())):
                    categories.append(category)
                    if len(categories) >= limit:
                        break
            
            return categories
        except Exception as e:
            logger.error(f"Error searching categories: {str(e)}")
            return []
    
    @classmethod
    def get_categories_with_subcategories(cls, min_subcategories: int = 1) -> list:
        """
        Get categories that have at least N subcategories
        
        Args:
            min_subcategories: Minimum number of subcategories
        
        Returns:
            list: List of categories meeting the criteria
        """
        try:
            categories = []
            for category in cls.query("category"):
                if (not category.isDeleted and 
                    len(category.sub_categories) >= min_subcategories):
                    categories.append(category)
            return categories
        except Exception as e:
            logger.error(f"Error getting categories with subcategories: {str(e)}")
            return []
    
    @classmethod
    def get_category_hierarchy(cls) -> dict:
        """
        Get full category hierarchy with subcategories
        
        Returns:
            dict: Hierarchical structure of categories
        """
        try:
            hierarchy = {
                "categories": [],
                "total_categories": 0,
                "total_subcategories": 0
            }
            
            for category in cls.get_active_categories():
                category_data = {
                    "category_id": category.sk,
                    "category_name": category.category_name,
                    "description": category.description,
                    "icon": category.icon,
                    "sort_order": category.sort_order,
                    "subcategories": []
                }
                
                # Sort subcategories by sort_order, then name
                sorted_subcategories = sorted(
                    category.sub_categories,
                    key=lambda x: (x.sort_order, x.name)
                )
                
                for subcategory in sorted_subcategories:
                    if subcategory.status == "active":
                        category_data["subcategories"].append({
                            "subcategory_id": subcategory.subcategory_id,
                            "name": subcategory.name,
                            "description": subcategory.description,
                            "icon": subcategory.icon,
                            "sort_order": subcategory.sort_order
                        })
                        hierarchy["total_subcategories"] += 1
                
                hierarchy["categories"].append(category_data)
                hierarchy["total_categories"] += 1
            
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error getting category hierarchy: {str(e)}")
            return {"categories": [], "total_categories": 0, "total_subcategories": 0}
    
    # ============= INSTANCE METHODS =============
    
    def update_category(self, **kwargs) -> 'Category':
        """
        Update category fields
        
        Args:
            **kwargs: Fields to update (category_name, description, status, 
                     sort_order, icon)
        
        Returns:
            Category: Updated category instance
        """
        try:
            updated = False
            allowed_fields = {
                'category_name', 'description', 'status', 
                'sort_order', 'icon'
            }
            
            for key, value in kwargs.items():
                if key in allowed_fields and hasattr(self, key):
                    if key == 'category_name' and value:
                        value = value.strip()
                        if not value:
                            raise ValueError("category_name cannot be empty")
                    
                    current_value = getattr(self, key)
                    if current_value != value:
                        setattr(self, key, value)
                        updated = True
            
            if updated:
                self.last_updated = datetime.utcnow()
                self.save()
                logger.info(f"Category {self.sk} updated")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to update category {self.sk}: {str(e)}")
            raise
    
    def add_subcategory(self, name: str, description: str = None,
                       icon: str = None, sort_order: int = 0,
                       status: str = "active") -> SubCategoryItem:
        """
        Add a new subcategory to this category
        
        Args:
            name: Name of the subcategory
            description: Description of the subcategory
            icon: Icon/Image URL for subcategory
            sort_order: Display order (default: 0)
            status: Status (active, inactive)
        
        Returns:
            SubCategoryItem: Created subcategory
        """
        try:
            if not name or not name.strip():
                raise ValueError("Subcategory name is required")
            
            # Check for duplicate subcategory name in this category
            existing_names = {sc.name.lower() for sc in self.sub_categories}
            if name.lower() in existing_names:
                raise ValueError(f"Subcategory '{name}' already exists in this category")
            
            # Generate subcategory ID using the centralized counter service
            subcategory_id = counter_service.get_next_id('subcategories')
            
            subcategory = SubCategoryItem(
                subcategory_id=subcategory_id,
                name=name.strip(),
                description=description.strip() if description else None,
                icon=icon,
                sort_order=sort_order,
                status=status,
                created_at=datetime.utcnow()
            )
            
            self.sub_categories.append(subcategory)
            self.last_updated = datetime.utcnow()
            self.save()
            
            logger.info(f"Subcategory '{name}' added to category {self.sk}")
            return subcategory
            
        except Exception as e:
            logger.error(f"Failed to add subcategory to category {self.sk}: {str(e)}")
            raise
    
    def update_subcategory(self, subcategory_id: str, **kwargs) -> SubCategoryItem:
        """
        Update an existing subcategory
        
        Args:
            subcategory_id: ID of the subcategory to update
            **kwargs: Fields to update (name, description, icon, sort_order, status)
        
        Returns:
            SubCategoryItem: Updated subcategory
        
        Raises:
            ValueError: If subcategory not found
        """
        try:
            for i, subcategory in enumerate(self.sub_categories):
                if subcategory.subcategory_id == subcategory_id:
                    updated = False
                    allowed_fields = {'name', 'description', 'icon', 'sort_order', 'status'}
                    
                    for key, value in kwargs.items():
                        if key in allowed_fields and hasattr(subcategory, key):
                            if key == 'name' and value:
                                value = value.strip()
                                if not value:
                                    raise ValueError("Subcategory name cannot be empty")
                                
                                # Check for duplicate name (excluding current subcategory)
                                existing_names = {
                                    sc.name.lower() 
                                    for sc in self.sub_categories 
                                    if sc.subcategory_id != subcategory_id
                                }
                                if value.lower() in existing_names:
                                    raise ValueError(f"Subcategory name '{value}' already exists")
                            
                            current_value = getattr(subcategory, key)
                            if current_value != value:
                                setattr(subcategory, key, value)
                                updated = True
                    
                    if updated:
                        self.last_updated = datetime.utcnow()
                        self.save()
                        logger.info(f"Subcategory {subcategory_id} updated in category {self.sk}")
                    
                    return subcategory
            
            raise ValueError(f"Subcategory {subcategory_id} not found")
            
        except Exception as e:
            logger.error(f"Failed to update subcategory {subcategory_id}: {str(e)}")
            raise
    
    def remove_subcategory(self, subcategory_id: str) -> bool:
        """
        Remove a subcategory from this category (hard delete)
        
        Args:
            subcategory_id: ID of the subcategory to remove
        
        Returns:
            bool: True if removed, False if not found
        """
        try:
            initial_count = len(self.sub_categories)
            self.sub_categories = [
                sc for sc in self.sub_categories 
                if sc.subcategory_id != subcategory_id
            ]
            
            if len(self.sub_categories) < initial_count:
                self.last_updated = datetime.utcnow()
                self.save()
                logger.info(f"Subcategory {subcategory_id} removed from category {self.sk}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove subcategory {subcategory_id}: {str(e)}")
            raise
    
    def get_subcategory(self, subcategory_id: str) -> SubCategoryItem | None:
        """
        Get a specific subcategory by ID
        
        Args:
            subcategory_id: ID of the subcategory
        
        Returns:
            SubCategoryItem or None if not found
        """
        for subcategory in self.sub_categories:
            if subcategory.subcategory_id == subcategory_id:
                return subcategory
        return None
    
    def get_active_subcategories(self) -> list:
        """
        Get all active subcategories in this category
        
        Returns:
            list: List of active subcategories
        """
        return [
            sc for sc in self.sub_categories 
            if sc.status == "active"
        ]
    
    def search_subcategories(self, search_term: str) -> list:
        """
        Search subcategories by name (partial, case-insensitive)
        
        Args:
            search_term: Search term
        
        Returns:
            list: List of matching subcategories
        """
        search_term_lower = search_term.lower()
        return [
            sc for sc in self.sub_categories
            if (search_term_lower in sc.name.lower() or
                (sc.description and search_term_lower in sc.description.lower()))
        ]
    
    def activate_category(self) -> 'Category':
        """
        Activate this category
        """
        self.status = "active"
        self.isDeleted = False
        self.last_updated = datetime.utcnow()
        self.save()
        logger.info(f"Category {self.sk} activated")
        return self
    
    def deactivate_category(self) -> 'Category':
        """
        Deactivate this category
        """
        self.status = "inactive"
        self.last_updated = datetime.utcnow()
        self.save()
        logger.info(f"Category {self.sk} deactivated")
        return self
    
    def soft_delete(self) -> 'Category':
        """
        Soft delete this category (mark as deleted)
        Also deactivate all subcategories
        """
        self.isDeleted = True
        self.status = "deleted"
        
        # Deactivate all subcategories
        for subcategory in self.sub_categories:
            subcategory.status = "inactive"
        
        self.last_updated = datetime.utcnow()
        self.save()
        logger.info(f"Category {self.sk} soft deleted")
        return self
    
    def restore_category(self) -> 'Category':
        """
        Restore a soft-deleted category
        """
        self.isDeleted = False
        self.status = "active"
        self.last_updated = datetime.utcnow()
        self.save()
        logger.info(f"Category {self.sk} restored")
        return self
    
    def get_summary(self) -> dict:
        """
        Get summary of this category
        
        Returns:
            dict: Category summary
        """
        total_subcategories = len(self.sub_categories)
        active_subcategories = len(self.get_active_subcategories())
        
        return {
            "category_id": self.sk,
            "category_name": self.category_name,
            "description": self.description,
            "status": self.status,
            "isDeleted": self.isDeleted,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "total_subcategories": total_subcategories,
            "active_subcategories": active_subcategories,
            "date_created": self.date_created.isoformat() if self.date_created else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
    
    def to_dict(self, include_subcategories: bool = True) -> dict:
        """
        Convert category to dictionary for API response
        
        Args:
            include_subcategories: Include subcategories in the output
        
        Returns:
            dict: Dictionary representation
        """
        try:
            category_dict = {
                "category_id": self.sk,
                "category_name": self.category_name,
                "description": self.description,
                "status": self.status,
                "isDeleted": self.isDeleted,
                "icon": self.icon,
                "sort_order": self.sort_order,
                "date_created": self.date_created.isoformat() if self.date_created else None,
                "last_updated": self.last_updated.isoformat() if self.last_updated else None
            }
            
            if include_subcategories:
                # Sort subcategories by sort_order, then name
                sorted_subcategories = sorted(
                    self.sub_categories,
                    key=lambda x: (x.sort_order, x.name)
                )
                
                category_dict["sub_categories"] = [
                    {
                        "subcategory_id": sc.subcategory_id,
                        "name": sc.name,
                        "description": sc.description,
                        "icon": sc.icon,
                        "sort_order": sc.sort_order,
                        "status": sc.status,
                        "created_at": sc.created_at.isoformat() if sc.created_at else None
                    }
                    for sc in sorted_subcategories
                ]
            
            return category_dict
            
        except Exception as e:
            logger.error(f"Error converting category to dict: {str(e)}")
            return {}
    
    def save(self, condition=None, **kwargs):
        """Override save to update last_updated timestamp"""
        self.last_updated = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


# ============= CATEGORY VALIDATION =============
def validate_category_name(name: str) -> tuple[bool, str]:
    """
    Validate category name
    
    Args:
        name: Category name to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not name or not name.strip():
        return False, "Category name is required"
    
    name = name.strip()
    if len(name) > 100:
        return False, "Category name must be 100 characters or less"
    
    if len(name) < 2:
        return False, "Category name must be at least 2 characters"
    
    return True, ""


def validate_category_id(category_id: str) -> bool:
    """
    Validate if a category ID is in correct format
    
    Args:
        category_id: Category ID to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        if not category_id:
            return False
        
        # Check format: CTGY-### where ### are exactly 3 digits
        if not category_id.startswith('CTGY-'):
            return False
        
        number_part = category_id[5:]  # Remove "CTGY-"
        if len(number_part) != 3:
            return False
        
        # Check if it's a valid number (001-999)
        number = int(number_part)
        return 1 <= number <= 999
        
    except (ValueError, IndexError):
        return False


# ============= CATEGORY MANAGER =============
class CategoryManager:
    """
    Manager class for category-related operations
    """
    
    @staticmethod
    def get_category_tree() -> dict:
        """
        Get hierarchical category tree for navigation
        
        Returns:
            dict: Category tree structure
        """
        try:
            categories = Category.get_active_categories()
            
            # Sort categories by sort_order, then name
            sorted_categories = sorted(
                categories,
                key=lambda x: (x.sort_order, x.category_name)
            )
            
            tree = []
            for category in sorted_categories:
                # Sort subcategories by sort_order, then name
                sorted_subcategories = sorted(
                    category.get_active_subcategories(),
                    key=lambda x: (x.sort_order, x.name)
                )
                
                tree.append({
                    "category": category.to_dict(include_subcategories=False),
                    "subcategories": [
                        {
                            "subcategory_id": sc.subcategory_id,
                            "name": sc.name,
                            "description": sc.description,
                            "icon": sc.icon,
                            "sort_order": sc.sort_order
                        }
                        for sc in sorted_subcategories
                    ]
                })
            
            return {
                "tree": tree,
                "total_categories": len(categories),
                "total_subcategories": sum(len(c.get_active_subcategories()) for c in categories)
            }
            
        except Exception as e:
            logger.error(f"Error building category tree: {str(e)}")
            return {"tree": [], "total_categories": 0, "total_subcategories": 0}
    
    @staticmethod
    def find_subcategory_by_id(subcategory_id: str) -> tuple[Category | None, SubCategoryItem | None]:
        """
        Find a subcategory by ID across all categories
        
        Args:
            subcategory_id: Subcategory ID to find
        
        Returns:
            tuple: (category, subcategory) or (None, None) if not found
        """
        try:
            categories = Category.get_all_categories(include_deleted=False)
            
            for category in categories:
                subcategory = category.get_subcategory(subcategory_id)
                if subcategory:
                    return category, subcategory
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error finding subcategory {subcategory_id}: {str(e)}")
            return None, None
    
    @staticmethod
    def get_category_statistics() -> dict:
        """
        Get category statistics
        
        Returns:
            dict: Category statistics
        """
        try:
            categories = Category.get_all_categories(include_deleted=False)
            
            total_categories = len(categories)
            total_subcategories = sum(len(c.sub_categories) for c in categories)
            active_subcategories = sum(len(c.get_active_subcategories()) for c in categories)
            
            categories_with_icon = sum(1 for c in categories if c.icon)
            categories_without_icon = total_categories - categories_with_icon
            
            # Status distribution
            status_counts = {}
            for category in categories:
                status_counts[category.status] = status_counts.get(category.status, 0) + 1
            
            return {
                "total_categories": total_categories,
                "total_subcategories": total_subcategories,
                "active_subcategories": active_subcategories,
                "categories_with_icon": categories_with_icon,
                "categories_without_icon": categories_without_icon,
                "icon_coverage": (categories_with_icon / total_categories * 100) if total_categories > 0 else 0,
                "avg_subcategories_per_category": (total_subcategories / total_categories) if total_categories > 0 else 0,
                "status_distribution": status_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting category statistics: {str(e)}")
            return {}
    
    @staticmethod
    def reorder_categories(new_order: List[Dict[str, Any]]) -> bool:
        """
        Reorder categories based on provided list
        
        Args:
            new_order: List of dicts with 'category_id' and 'sort_order'
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = True
            errors = []
            
            for item in new_order:
                category_id = item.get('category_id')
                sort_order = item.get('sort_order')
                
                if category_id is None or sort_order is None:
                    errors.append(f"Invalid item: {item}")
                    continue
                
                category = Category.get_by_id(category_id)
                if not category:
                    errors.append(f"Category not found: {category_id}")
                    continue
                
                try:
                    category.update_category(sort_order=sort_order)
                except Exception as e:
                    errors.append(f"Failed to update category {category_id}: {str(e)}")
                    success = False
            
            if errors:
                logger.warning(f"Errors during category reordering: {errors}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error reordering categories: {str(e)}")
            return False