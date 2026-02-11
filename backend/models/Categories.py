"""
Category Model - Following ERD Specification with Enhancements
PK = "categories", SK = "CAT-####" (4-digit format)
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, BooleanAttribute,
    ListAttribute, MapAttribute, UTCDateTimeAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION, DYNAMODB_LOCAL, DYNAMODB_LOCAL_HOST
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


# ============= NESTED MAP ATTRIBUTES =============
class SubCategoryItem(MapAttribute):
    """MapAttribute for sub_categories array items"""
    subcategory_id = UnicodeAttribute()
    name = UnicodeAttribute()
    description = UnicodeAttribute(null=True)
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    status = UnicodeAttribute(default="active")
    sort_order = NumberAttribute(default=0)
    icon = UnicodeAttribute(null=True)
    products = ListAttribute(default=list)  # Added for product IDs/names


# ============= GLOBAL SECONDARY INDEXES =============
class CategoryStatusIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = 'category-status-index'
        projection = AllProjection()
        read_capacity_units = 3
        write_capacity_units = 3
    status = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)


class CategoryNameIndex(GlobalSecondaryIndex):
    class Meta:
        index_name = 'category-name-index'
        projection = AllProjection()
        read_capacity_units = 3
        write_capacity_units = 3
    category_name = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)


# ============= MAIN CATEGORY MODEL =============
class Category(Model):
    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        read_capacity_units = 5
        write_capacity_units = 5

    pk = UnicodeAttribute(hash_key=True, default="categories")
    sk = UnicodeAttribute(range_key=True)  # "CAT-0001"

    status_index = CategoryStatusIndex()
    name_index = CategoryNameIndex()

    category_name = UnicodeAttribute()
    description = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="active")
    sort_order = NumberAttribute(default=0)
    icon = UnicodeAttribute(null=True)

    sub_categories = ListAttribute(of=SubCategoryItem, default=list)

    isDeleted = BooleanAttribute(default=False)
    date_created = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    last_updated = UTCDateTimeAttribute(default_for_new=datetime.utcnow)

    # ============= CLASS METHODS =============
    @classmethod
    def create_category(cls, category_name: str, description: str = None,
                       icon: str = None, sort_order: int = 0) -> 'Category':
        try:
            if not category_name or not category_name.strip():
                raise ValueError("category_name is required")
            sk = generate_sk('CAT-', 'category_seq')
            category = cls(
                pk="categories",
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
    def get_by_id(cls, category_id: str) -> Optional['Category']:
        if not category_id.startswith('CAT-'):
            category_id = f"CAT-{category_id.zfill(4)}"
        try:
            return cls.get("categories", category_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_name(cls, category_name: str) -> Optional['Category']:
        for cat in cls.name_index.query(category_name):
            if not cat.isDeleted:
                return cat
        return None

    @classmethod
    def get_by_status(cls, status: str, include_deleted: bool = False) -> list:
        cats = []
        for cat in cls.status_index.query(status):
            if include_deleted or not cat.isDeleted:
                cats.append(cat)
        return cats

    @classmethod
    def get_active_categories(cls) -> list:
        return cls.get_by_status("active")

    @classmethod
    def get_all_categories(cls, include_deleted: bool = False) -> list:
        cats = []
        for cat in cls.query("categories"):
            if include_deleted or not cat.isDeleted:
                cats.append(cat)
        return cats

    @classmethod
    def search_categories(cls, search_term: str, limit: int = 10) -> list:
        search_term_lower = search_term.lower()
        cats = []
        for cat in cls.query("categories", limit=1000):
            if cat.isDeleted:
                continue
            if (search_term_lower in cat.category_name.lower() or
                (cat.description and search_term_lower in cat.description.lower())):
                cats.append(cat)
                if len(cats) >= limit:
                    break
        return cats

    @classmethod
    def get_category_hierarchy(cls) -> dict:
        hierarchy = {"categories": [], "total_categories": 0, "total_subcategories": 0}
        for cat in cls.get_active_categories():
            cat_data = {
                "category_id": cat.sk,
                "category_name": cat.category_name,
                "description": cat.description,
                "icon": cat.icon,
                "sort_order": cat.sort_order,
                "subcategories": []
            }
            sorted_subs = sorted(cat.sub_categories, key=lambda x: (x.sort_order, x.name))
            for sub in sorted_subs:
                if sub.status == "active":
                    cat_data["subcategories"].append({
                        "subcategory_id": sub.subcategory_id,
                        "name": sub.name,
                        "description": sub.description,
                        "icon": sub.icon,
                        "sort_order": sub.sort_order
                    })
                    hierarchy["total_subcategories"] += 1
            hierarchy["categories"].append(cat_data)
            hierarchy["total_categories"] += 1
        return hierarchy

    # ============= INSTANCE METHODS =============
    def update_category(self, **kwargs) -> 'Category':
        allowed = {'category_name', 'description', 'status', 'sort_order', 'icon'}
        updated = False
        for key, value in kwargs.items():
            if key in allowed and hasattr(self, key):
                if key == 'category_name' and value:
                    value = value.strip()
                    if not value:
                        raise ValueError("category_name cannot be empty")
                if getattr(self, key) != value:
                    setattr(self, key, value)
                    updated = True
        if updated:
            self.last_updated = datetime.utcnow()
            self.save()
        return self

    def add_subcategory(self, name: str, description: str = None,
                       icon: str = None, sort_order: int = 0,
                       status: str = "active") -> SubCategoryItem:
        if not name or not name.strip():
            raise ValueError("Subcategory name is required")
        existing_names = {sc.name.lower() for sc in self.sub_categories}
        if name.lower() in existing_names:
            raise ValueError(f"Subcategory '{name}' already exists")
        sub_id = generate_sk('SUB-', 'subcategory_seq')
        sub = SubCategoryItem(
            subcategory_id=sub_id,
            name=name.strip(),
            description=description.strip() if description else None,
            icon=icon,
            sort_order=sort_order,
            status=status,
            created_at=datetime.utcnow(),
            products=[]
        )
        self.sub_categories.append(sub)
        self.last_updated = datetime.utcnow()
        self.save()
        return sub

    def update_subcategory(self, subcategory_id: str, **kwargs) -> SubCategoryItem:
        for i, sub in enumerate(self.sub_categories):
            if sub.subcategory_id == subcategory_id:
                updated = False
                allowed = {'name', 'description', 'icon', 'sort_order', 'status'}
                for key, value in kwargs.items():
                    if key in allowed and hasattr(sub, key):
                        if key == 'name' and value:
                            value = value.strip()
                            if not value:
                                raise ValueError("Subcategory name cannot be empty")
                            # check duplicate excluding current
                            existing = {sc.name.lower() for sc in self.sub_categories if sc.subcategory_id != subcategory_id}
                            if value.lower() in existing:
                                raise ValueError(f"Subcategory name '{value}' already exists")
                        if getattr(sub, key) != value:
                            setattr(sub, key, value)
                            updated = True
                if updated:
                    self.last_updated = datetime.utcnow()
                    self.save()
                return sub
        raise ValueError(f"Subcategory {subcategory_id} not found")

    def remove_subcategory(self, subcategory_id: str) -> bool:
        init_len = len(self.sub_categories)
        self.sub_categories = [sc for sc in self.sub_categories if sc.subcategory_id != subcategory_id]
        if len(self.sub_categories) < init_len:
            self.last_updated = datetime.utcnow()
            self.save()
            return True
        return False

    def get_subcategory(self, subcategory_id: str) -> Optional[SubCategoryItem]:
        for sc in self.sub_categories:
            if sc.subcategory_id == subcategory_id:
                return sc
        return None

    def get_active_subcategories(self) -> list:
        return [sc for sc in self.sub_categories if sc.status == "active"]

    def soft_delete(self) -> 'Category':
        self.isDeleted = True
        self.status = "deleted"
        for sc in self.sub_categories:
            sc.status = "inactive"
        self.last_updated = datetime.utcnow()
        self.save()
        return self

    def restore_category(self) -> 'Category':
        self.isDeleted = False
        self.status = "active"
        self.last_updated = datetime.utcnow()
        self.save()
        return self

    def to_dict(self, include_subcategories: bool = True) -> dict:
        d = {
            "category_id": self.sk,
            "category_name": self.category_name,
            "description": self.description,
            "status": self.status,
            "isDeleted": self.isDeleted,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "date_created": self.date_created.isoformat() if self.date_created else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
        if include_subcategories:
            sorted_subs = sorted(self.sub_categories, key=lambda x: (x.sort_order, x.name))
            d["sub_categories"] = [
                {
                    "subcategory_id": sc.subcategory_id,
                    "name": sc.name,
                    "description": sc.description,
                    "icon": sc.icon,
                    "sort_order": sc.sort_order,
                    "status": sc.status,
                    "created_at": sc.created_at.isoformat() if sc.created_at else None,
                }
                for sc in sorted_subs
            ]
        return d

    def save(self, condition=None, **kwargs):
        self.last_updated = datetime.utcnow()
        return super().save(condition=condition, **kwargs)


def validate_category_id(category_id: str) -> bool:
    try:
        if not category_id.startswith('CAT-'):
            return False
        num = category_id[4:]
        return len(num) == 4 and 1 <= int(num) <= 9999
    except:
        return False


class CategoryManager:
    @staticmethod
    def get_category_tree() -> dict:
        cats = Category.get_active_categories()
        cats.sort(key=lambda x: (x.sort_order, x.category_name))
        tree = []
        for cat in cats:
            subs = cat.get_active_subcategories()
            subs.sort(key=lambda x: (x.sort_order, x.name))
            tree.append({
                "category": cat.to_dict(include_subcategories=False),
                "subcategories": [
                    {
                        "subcategory_id": sc.subcategory_id,
                        "name": sc.name,
                        "description": sc.description,
                        "icon": sc.icon,
                        "sort_order": sc.sort_order
                    }
                    for sc in subs
                ]
            })
        total_subs = sum(len(c.get_active_subcategories()) for c in cats)
        return {"tree": tree, "total_categories": len(cats), "total_subcategories": total_subs}

    @staticmethod
    def get_category_statistics() -> dict:
        cats = Category.get_all_categories(include_deleted=False)
        total = len(cats)
        status_counts = {}
        icon_count = 0
        sub_counts = []
        for cat in cats:
            status_counts[cat.status] = status_counts.get(cat.status, 0) + 1
            if cat.icon:
                icon_count += 1
            sub_counts.append(len(cat.sub_categories))
        return {
            "total_categories": total,
            "categories_with_icon": icon_count,
            "categories_without_icon": total - icon_count,
            "icon_coverage": (icon_count / total * 100) if total else 0,
            "avg_subcategories_per_category": (sum(sub_counts) / total) if total else 0,
            "status_distribution": status_counts
        }