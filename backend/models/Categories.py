from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from datetime import datetime
from typing import Optional, List, Dict, Any


class SubCategoryItem(MapAttribute):
    """MapAttribute for sub_categories items"""
    subcategory_id = UnicodeAttribute()
    name = UnicodeAttribute()
    description = UnicodeAttribute(null=True)
    created_at = UTCDateTimeAttribute(default=datetime.utcnow)
    status = UnicodeAttribute(default="active")


class Category(Model):
    """
    Category model for DynamoDB
    PK = categories (partition key)
    SK = CAT-#### (sort key)
    """
    class Meta:
        table_name = "your-table-name"  # Replace with your table name
        region = "your-region"  # Replace with your AWS region
        # Add billing_mode, read_capacity_units, write_capacity_units if needed

    # Primary Key Attributes
    PK = UnicodeAttribute(hash_key=True, default="categories")
    SK = UnicodeAttribute(range_key=True)

    # Category Details
    category_name = UnicodeAttribute()
    description = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="active")
    
    # Subcategories
    sub_categories = ListAttribute(of=SubCategoryItem, default=list)
    
    # Status and Metadata
    isDeleted = BooleanAttribute(default=False)
    date_created = UTCDateTimeAttribute(default=datetime.utcnow)
    last_updated = UTCDateTimeAttribute(default=datetime.utcnow)

    @classmethod
    def create_category(cls, category_id: str, **kwargs):
        """Helper method to create a new category with proper SK format"""
        sk = f"CAT-{category_id}"
        return cls(SK=sk, **kwargs)

    @classmethod
    def get_category(cls, category_id: str):
        """Helper method to retrieve a category by ID"""
        sk = f"CAT-{category_id}"
        return cls.get("categories", sk)

    @classmethod
    def get_category_by_sk(cls, sk: str):
        """Helper method to retrieve a category by SK"""
        return cls.get("categories", sk)

    @classmethod
    def query_active_categories(cls):
        """Query all active, non-deleted categories"""
        return cls.query(
            "categories",
            cls.SK.startswith("CAT-"),
            filter_condition=(cls.isDeleted == False) & (cls.status == "active")
        )

    @classmethod
    def query_by_status(cls, status: str):
        """Query categories by status"""
        # This requires a GSI on status
        return cls.query(
            status,
            cls.SK.startswith("CAT-"),
            index_name="CategoryStatusIndex",  # You'll need to create this GSI
            filter_condition=cls.isDeleted == False
        )

    @classmethod
    def query_all_categories(cls):
        """Query all non-deleted categories"""
        return cls.query(
            "categories",
            cls.SK.startswith("CAT-"),
            filter_condition=cls.isDeleted == False
        )

    def add_subcategory(self, subcategory_id: str, name: str, 
                       description: Optional[str] = None, 
                       status: str = "active"):
        """
        Add a new subcategory to the category
        
        Args:
            subcategory_id: Unique identifier for the subcategory
            name: Name of the subcategory
            description: Description of the subcategory
            status: Status of the subcategory
        """
        # Check if subcategory ID already exists
        existing = [sc for sc in self.sub_categories if sc.subcategory_id == subcategory_id]
        if existing:
            raise ValueError(f"Subcategory with ID '{subcategory_id}' already exists")
        
        subcategory = SubCategoryItem(
            subcategory_id=subcategory_id,
            name=name,
            description=description,
            status=status
        )
        
        self.sub_categories.append(subcategory)
        self.last_updated = datetime.utcnow()
        self.save()
        return subcategory

    def update_subcategory(self, subcategory_id: str, **kwargs):
        """
        Update an existing subcategory
        
        Args:
            subcategory_id: ID of the subcategory to update
            **kwargs: Fields to update (name, description, status)
        """
        for subcategory in self.sub_categories:
            if subcategory.subcategory_id == subcategory_id:
                for key, value in kwargs.items():
                    if hasattr(subcategory, key):
                        setattr(subcategory, key, value)
                
                self.last_updated = datetime.utcnow()
                self.save()
                return subcategory
        
        raise ValueError(f"Subcategory with ID '{subcategory_id}' not found")

    def remove_subcategory(self, subcategory_id: str):
        """
        Remove a subcategory from the category
        
        Args:
            subcategory_id: ID of the subcategory to remove
        """
        initial_count = len(self.sub_categories)
        self.sub_categories = [
            sc for sc in self.sub_categories 
            if sc.subcategory_id != subcategory_id
        ]
        
        if len(self.sub_categories) == initial_count:
            raise ValueError(f"Subcategory with ID '{subcategory_id}' not found")
        
        self.last_updated = datetime.utcnow()
        self.save()

    def get_subcategory(self, subcategory_id: str) -> Optional[SubCategoryItem]:
        """Get a specific subcategory by ID"""
        for subcategory in self.sub_categories:
            if subcategory.subcategory_id == subcategory_id:
                return subcategory
        return None

    def get_active_subcategories(self) -> List[SubCategoryItem]:
        """Get all active subcategories"""
        return [sc for sc in self.sub_categories if sc.status == "active"]

    def get_subcategories_by_name(self, name: str) -> List[SubCategoryItem]:
        """Get subcategories by name (partial match)"""
        name_lower = name.lower()
        return [
            sc for sc in self.sub_categories 
            if name_lower in sc.name.lower()
        ]

    def activate_category(self):
        """Activate the category"""
        self.status = "active"
        self.isDeleted = False
        self.last_updated = datetime.utcnow()
        self.save()

    def deactivate_category(self):
        """Deactivate the category"""
        self.status = "inactive"
        self.last_updated = datetime.utcnow()
        self.save()

    def soft_delete(self):
        """Soft delete the category"""
        self.isDeleted = True
        self.status = "deleted"
        self.last_updated = datetime.utcnow()
        self.save()

    def get_category_summary(self) -> Dict[str, Any]:
        """Get summary of the category including subcategory counts"""
        total_subcategories = len(self.sub_categories)
        active_subcategories = len(self.get_active_subcategories())
        
        return {
            "category_id": self.SK.replace("CAT-", ""),
            "category_name": self.category_name,
            "status": self.status,
            "isDeleted": self.isDeleted,
            "total_subcategories": total_subcategories,
            "active_subcategories": active_subcategories,
            "date_created": self.date_created.isoformat() if self.date_created else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "subcategories": [
                {
                    "subcategory_id": sc.subcategory_id,
                    "name": sc.name,
                    "status": sc.status
                }
                for sc in self.sub_categories[:10]  # Limit to first 10 for summary
            ]
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Convert category to full dictionary including all subcategory details"""
        category_dict = {
            "category_id": self.SK.replace("CAT-", ""),
            "category_name": self.category_name,
            "description": self.description,
            "status": self.status,
            "isDeleted": self.isDeleted,
            "date_created": self.date_created.isoformat() if self.date_created else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "sub_categories": []
        }
        
        for subcategory in self.sub_categories:
            subcategory_dict = {
                "subcategory_id": subcategory.subcategory_id,
                "name": subcategory.name,
                "description": subcategory.description,
                "created_at": subcategory.created_at.isoformat() if subcategory.created_at else None,
                "status": subcategory.status
            }
            category_dict["sub_categories"].append(subcategory_dict)
        
        return category_dict