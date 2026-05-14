"""
PosPage Model
PK = "PAGES", SK = "PAGE-##" (2-digit format)
Represents a custom POS shortcut page. Products can belong to multiple pages.
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, ListAttribute
from pynamodb.exceptions import DoesNotExist
from app.utils import DYNAMO_TABLE_NAME, AWS_REGION
from app.utils.counters import counter_service
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class PosPage(Model):
    """
    POS Page — a custom grouping of products for quick access on the cashier screen.
    Products can belong to more than one page (many-to-many via stored product_ids list).

    PK = "PAGES"
    SK = "PAGE-##"  (2-digit, e.g. PAGE-01)
    """

    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        read_capacity_units = 5
        write_capacity_units = 5

    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, default="PAGES", attr_name="PK")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # PAGE-01

    # ============= PAGE DETAILS =============
    page_name = UnicodeAttribute()
    icon = UnicodeAttribute(default="Package")

    # ============= PRODUCT REFERENCES =============
    # List of product IDs (PROD-XXXXX). Products may exist in multiple pages.
    product_ids = ListAttribute(default=list)

    # ============= METADATA =============
    created_at = UnicodeAttribute(default=lambda: datetime.utcnow().isoformat())
    updated_at = UnicodeAttribute(default=lambda: datetime.utcnow().isoformat())

    # ============= CLASS METHODS =============

    @classmethod
    def create_page(cls, page_name: str, icon: str = "Package") -> "PosPage":
        page_id = counter_service.get_next_id("pos_pages")
        page = cls()
        page.pk = "PAGES"
        page.sk = page_id
        page.page_name = page_name.strip()
        page.icon = icon
        page.product_ids = []
        page.created_at = datetime.utcnow().isoformat()
        page.updated_at = datetime.utcnow().isoformat()
        page.save()
        logger.info(f"Created PosPage {page_id}: '{page_name}'")
        return page

    @classmethod
    def get_all_pages(cls) -> List["PosPage"]:
        return list(cls.query("PAGES"))

    @classmethod
    def get_page(cls, page_id: str) -> Optional["PosPage"]:
        try:
            return cls.get("PAGES", page_id)
        except DoesNotExist:
            return None

    # ============= INSTANCE METHODS =============

    def add_products(self, product_ids: list) -> None:
        current = [str(p) for p in (self.product_ids or [])]
        for pid in product_ids:
            if str(pid) not in current:
                current.append(str(pid))
        self.product_ids = current
        self.updated_at = datetime.utcnow().isoformat()
        self.save()

    def remove_products(self, product_ids: list) -> None:
        remove_set = {str(p) for p in product_ids}
        self.product_ids = [p for p in (self.product_ids or []) if str(p) not in remove_set]
        self.updated_at = datetime.utcnow().isoformat()
        self.save()

    def to_dict(self) -> dict:
        return {
            "page_id": self.sk,
            "page_name": self.page_name,
            "icon": self.icon,
            "product_ids": [str(p) for p in (self.product_ids or [])],
            "product_count": len(self.product_ids or []),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
