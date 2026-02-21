from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, 
    UTCDateTimeAttribute, ListAttribute, MapAttribute
)
from datetime import datetime
import logging
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SyncLogItem(MapAttribute):
    """ERD-compliant sync log"""
    object = UnicodeAttribute(null=True)
    last_updated = UTCDateTimeAttribute(null=True)
    source = UnicodeAttribute(null=True)
    status = UnicodeAttribute(null=True)
    details = UnicodeAttribute(null=True)
    action = UnicodeAttribute(null=True)


# ===== OPTIONAL ENHANCED CLASSES (nullable, not required) =====
class SupplierAddress(MapAttribute):
    """OPTIONAL: Detailed address breakdown"""
    street = UnicodeAttribute(null=True)
    building = UnicodeAttribute(null=True)
    area = UnicodeAttribute(null=True)
    city = UnicodeAttribute(null=True)
    state = UnicodeAttribute(null=True)
    country = UnicodeAttribute(null=True)
    postal_code = UnicodeAttribute(null=True)
    landmark = UnicodeAttribute(null=True)
    
    def to_string(self) -> str:
        """Convert to simple address string"""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.building:
            parts.append(self.building)
        if self.area:
            parts.append(self.area)
        if self.city:
            parts.append(self.city)
        return ", ".join(filter(None, parts))


class ContactPerson(MapAttribute):
    """OPTIONAL: Detailed contact person"""
    name = UnicodeAttribute(null=True)
    designation = UnicodeAttribute(null=True)
    phone = UnicodeAttribute(null=True)
    email = UnicodeAttribute(null=True)
    is_primary = BooleanAttribute(default=False)
# ===== END OPTIONAL CLASSES =====


class Supplier(Model):
    """
    SUPPLIER MODEL - Hybrid Approach
    
    Core ERD fields + Optional enhanced fields
    Single Table Design using RamyeonCornerDB
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME
        region = AWS_REGION
        
        read_capacity_units = 3
        write_capacity_units = 3
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="suppliers")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "SUPP-001" (3-digit)
    
    # ============= CORE ERD FIELDS (REQUIRED/SIMPLE) =============
    supplier_name = UnicodeAttribute()
    contact_person = UnicodeAttribute(null=True)  # Simple string
    email = UnicodeAttribute(null=True)
    phone_number = UnicodeAttribute(null=True)
    address = UnicodeAttribute(null=True)  # Simple string (ERD compliance)
    type = UnicodeAttribute(null=True)
    notes = UnicodeAttribute(null=True)
    isDeleted = BooleanAttribute(default=False)
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)
    created_by = UnicodeAttribute(null=True)
    sync_logs = ListAttribute(of=SyncLogItem, null=True)
    updated_by = UnicodeAttribute(null=True)
    isFavorite = BooleanAttribute(default=False)
    
    # ============= OPTIONAL ENHANCED FIELDS =============
    addresses = ListAttribute(of=SupplierAddress, null=True)  # Optional
    contact_persons = ListAttribute(of=ContactPerson, null=True)  # Optional
    
    # ============= OPTIONAL PRACTICAL FIELDS =============
    lead_time_days = UnicodeAttribute(null=True)  # "3-5 days"
    payment_terms = UnicodeAttribute(null=True)  # "COD", "30 days"
    delivery_method = UnicodeAttribute(null=True)  # "pickup", "delivery"
    
    @classmethod
    def create_supplier(cls, supplier_name: str, **kwargs) -> 'Supplier':
        """
        Create supplier - simple with just ERD fields
        Enhanced fields can be added later if needed
        """
        try:
            if not supplier_name or not supplier_name.strip():
                raise ValueError("supplier_name is required")
            
            # Generate 3-digit SK
            sk = generate_sk('SUPP-', 'supplier_seq', digits=3)
            
            # Core ERD fields only in constructor
            supplier = cls(
                pk="suppliers",
                sk=sk,
                supplier_name=supplier_name.strip(),
                contact_person=kwargs.get('contact_person'),
                email=kwargs.get('email'),
                phone_number=kwargs.get('phone_number'),
                address=kwargs.get('address'),  # Simple string
                type=kwargs.get('type'),
                notes=kwargs.get('notes'),
                # Enhanced fields remain None by default
                addresses=None,
                contact_persons=None,
                lead_time_days=kwargs.get('lead_time_days'),
                payment_terms=kwargs.get('payment_terms'),
                delivery_method=kwargs.get('delivery_method'),
                isDeleted=False,
                isFavorite=kwargs.get('isFavorite', False),
                created_by=kwargs.get('created_by'),
                updated_by=kwargs.get('updated_by'),
                sync_logs=kwargs.get('sync_logs')
            )
            supplier.save()
            
            logger.info(f"Supplier created: {sk} - '{supplier_name}'")
            return supplier
            
        except Exception as e:
            logger.error(f"Failed to create supplier: {str(e)}")
            raise
    
    # ===== OPTIONAL ENHANCED METHODS (use only if needed) =====
    
    def add_detailed_address(self, **address_data) -> Optional[SupplierAddress]:
        """
        OPTIONAL: Add detailed address breakdown
        """
        try:
            if not self.addresses:
                self.addresses = []
            
            address = SupplierAddress(**address_data)
            self.addresses.append(address)
            self.save()
            
            # Update simple address field with first detailed address
            if len(self.addresses) == 1 and not self.address:
                self.address = address.to_string()
                self.save()
            
            return address
        except Exception as e:
            logger.error(f"Failed to add detailed address: {str(e)}")
            return None
    
    def add_contact_person_detail(self, **contact_data) -> Optional[ContactPerson]:
        """
        OPTIONAL: Add detailed contact person
        """
        try:
            if not self.contact_persons:
                self.contact_persons = []
            
            contact = ContactPerson(**contact_data)
            self.contact_persons.append(contact)
            self.save()
            
            # Update simple contact field with first detailed contact
            if len(self.contact_persons) == 1 and not self.contact_person:
                self.contact_person = contact.name
                self.save()
            
            return contact
        except Exception as e:
            logger.error(f"Failed to add contact detail: {str(e)}")
            return None
    
    # ===== SIMPLE GETTERS (always work) =====
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Returns both ERD fields and any enhanced fields
        """
        data = {
            "supplier_id": self.sk,
            "supplier_name": self.supplier_name,
            "contact_person": self.contact_person,
            "email": self.email,
            "phone_number": self.phone_number,
            "address": self.address,  # Simple string
            "type": self.type,
            "notes": self.notes,
            "isDeleted": self.isDeleted,
            "isFavorite": self.isFavorite,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }
        
        # Add enhanced fields only if they exist
        if self.addresses:
            data["addresses"] = [addr.to_string() for addr in self.addresses]
        
        if self.contact_persons:
            data["contact_persons"] = [
                {"name": cp.name, "designation": cp.designation}
                for cp in self.contact_persons
            ]
        
        # Add practical fields if they exist
        if self.lead_time_days:
            data["lead_time_days"] = self.lead_time_days
        if self.payment_terms:
            data["payment_terms"] = self.payment_terms
        if self.delivery_method:
            data["delivery_method"] = self.delivery_method
        
        return data