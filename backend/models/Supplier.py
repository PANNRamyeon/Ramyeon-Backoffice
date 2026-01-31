"""
Supplier Model with Address Breakdown - For Manual Order Processing
PK = "suppliers", SK = "SUPP-###"
"""
from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, BooleanAttribute, 
    UTCDateTimeAttribute, ListAttribute, MapAttribute
)
from datetime import datetime
import os
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional, List
import time


class SupplierAddress(MapAttribute):
    """
    Complete address breakdown for manual order processing
    
    Essential for:
    1. Visiting suppliers in person
    2. Sending goods/orders physically
    3. Shipping/transport coordination
    4. Location-based supplier search
    """
    street = UnicodeAttribute(null=True)        # Building number and street
    building = UnicodeAttribute(null=True)      # Building name/floor
    area = UnicodeAttribute(null=True)          # Area/neighborhood
    city = UnicodeAttribute(null=True)          # City
    state = UnicodeAttribute(null=True)         # State/Province
    country = UnicodeAttribute(null=True)       # Country
    postal_code = UnicodeAttribute(null=True)   # ZIP/Postal code
    landmark = UnicodeAttribute(null=True)      # Nearby landmark
    address_type = UnicodeAttribute(default="primary")  # primary, warehouse, office, billing
    is_primary = BooleanAttribute(default=True)
    
    def to_string(self) -> str:
        """Convert to complete address string"""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.building:
            parts.append(self.building)
        if self.area:
            parts.append(self.area)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
        if self.postal_code:
            parts.append(f"Postal: {self.postal_code}")
        return ", ".join(filter(None, parts))


class ContactPerson(MapAttribute):
    """
    Multiple contact persons for different purposes
    
    Essential for manual order processing:
    1. Primary contact for orders
    2. Accounts contact for payments
    3. Warehouse contact for deliveries
    4. Technical contact for product queries
    """
    name = UnicodeAttribute()
    designation = UnicodeAttribute(null=True)   # e.g., "Sales Manager", "Warehouse Supervisor"
    department = UnicodeAttribute(null=True)    # e.g., "Sales", "Accounts", "Warehouse"
    email = UnicodeAttribute(null=True)
    phone = UnicodeAttribute(null=True)
    mobile = UnicodeAttribute(null=True)        # For WhatsApp/SMS
    is_primary = BooleanAttribute(default=False)
    contact_hours = UnicodeAttribute(null=True) # e.g., "9AM-5PM Mon-Fri"
    notes = UnicodeAttribute(null=True)         # e.g., "Best to call after 10AM"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'designation': self.designation,
            'department': self.department,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'is_primary': self.is_primary,
            'contact_hours': self.contact_hours,
            'notes': self.notes
        }


class SyncLogItem(MapAttribute):
    """
    Sync logs object - following ERD exactly
    """
    object = UnicodeAttribute(null=True)
    last_updated = UTCDateTimeAttribute(null=True)
    source = UnicodeAttribute(null=True)
    status = UnicodeAttribute(null=True)
    details = UnicodeAttribute(null=True)
    action = UnicodeAttribute(null=True)


class Supplier(Model):
    """
    SUPPLIER MODEL with Complete Address Breakdown
    
    PK/SK Pattern:
    - PK: "suppliers" (table name/entity type)
    - SK: "SUPP-###" (3-digit auto-increment: 001, 002, etc.)
    
    Enhanced with proper address structure for manual order processing
    """
    
    class Meta:
        table_name = os.environ.get('SUPPLIER_TABLE_NAME', 'Suppliers')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        if os.environ.get('DYNAMODB_LOCAL', 'false').lower() == 'true':
            host = os.environ.get('DYNAMODB_LOCAL_HOST', 'http://localhost:8000')
        read_capacity_units = 5
        write_capacity_units = 5
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True)   # Partition Key: "suppliers"
    sk = UnicodeAttribute(range_key=True)  # Sort Key: "SUPP-001"
    
    # ============= SUPPLIER IDENTIFICATION =============
    supplier_id = UnicodeAttribute()  # "SUPP-001"
    supplier_number = UnicodeAttribute()  # "001"
    
    # ============= BASIC INFORMATION (ERD FIELDS) =============
    supplier_name = UnicodeAttribute()  # String (Required)
    contact_person = UnicodeAttribute(null=True)  # String (Legacy - keep for backward compatibility)
    email = UnicodeAttribute(null=True)  # String
    phone_number = UnicodeAttribute(null=True)  # String
    address = UnicodeAttribute(null=True)  # String (Legacy - full address string)
    type = UnicodeAttribute(null=True)  # String
    notes = UnicodeAttribute(null=True)  # String
    
    # ============= ENHANCED ADDRESS STRUCTURE =============
    # For manual order processing - physical visits/shipments
    addresses = ListAttribute(of=SupplierAddress, null=True)  # Multiple addresses
    
    # ============= ENHANCED CONTACT MANAGEMENT =============
    contact_persons = ListAttribute(of=ContactPerson, null=True)  # Multiple contacts
    
    # ============= MANUAL ORDER PROCESSING FIELDS =============
    # Essential for manual supplier management
    lead_time_days = UnicodeAttribute(null=True)  # String: "3-5", "7", "14"
    minimum_order = UnicodeAttribute(null=True)  # String: "100 units", "$500"
    payment_terms = UnicodeAttribute(null=True)  # String: "COD", "30 days", "50% advance"
    delivery_method = UnicodeAttribute(null=True)  # String: "pickup", "supplier_delivers", "third_party"
    visiting_hours = UnicodeAttribute(null=True)  # String: "9AM-5PM Mon-Sat"
    warehouse_location = UnicodeAttribute(null=True)  # String: Specific location in warehouse
    
    # ============= STATUS AND FLAGS (ERD FIELDS) =============
    isDeleted = BooleanAttribute(default=False)  # boolean
    isFavorite = BooleanAttribute(default=False)  # boolean
    
    # ============= TIMESTAMPS (ERD FIELDS) =============
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    updated_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # ISODATE
    
    # ============= AUDIT TRAIL (ERD FIELDS) =============
    created_by = UnicodeAttribute(null=True)  # String
    updated_by = UnicodeAttribute(null=True)  # String
    
    # ============= SYNC LOGS (ERD FIELDS) =============
    sync_logs = ListAttribute(of=SyncLogItem, null=True)
    
    # ============= COUNTER CONFIGURATION =============
    ID_PREFIX = "SUPP-"
    DIGITS = 3  # 3-digit format: SUPP-001 to SUPP-999
    DEFAULT_START_NUMBER = 1
    
    # ============= COUNTER MANAGEMENT =============
    
    @classmethod
    def _get_dynamodb_client(cls):
        """Get DynamoDB client"""
        return boto3.resource(
            'dynamodb', 
            region_name=cls.Meta.region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
    
    @classmethod
    def _format_supplier_id(cls, number: int) -> str:
        """Format supplier ID with prefix and 3 digits"""
        return f"{cls.ID_PREFIX}{number:0{cls.DIGITS}d}"
    
    @classmethod
    def _get_next_supplier_id(cls) -> Dict[str, Any]:
        """Get next auto-incrementing supplier ID"""
        dynamodb = cls._get_dynamodb_client()
        table = dynamodb.Table(cls.Meta.table_name)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = table.update_item(
                    Key={'pk': 'COUNTERS', 'sk': 'SUPPLIER'},
                    UpdateExpression='SET #value = if_not_exists(#value, :start) + :inc',
                    ExpressionAttributeNames={'#value': 'value'},
                    ExpressionAttributeValues={
                        ':start': cls.DEFAULT_START_NUMBER - 1,
                        ':inc': 1
                    },
                    ReturnValues='UPDATED_NEW'
                )
                
                new_number = response['Attributes']['value']
                supplier_id = cls._format_supplier_id(new_number)
                supplier_number_str = f"{new_number:0{cls.DIGITS}d}"
                
                return {
                    "supplier_id": supplier_id,
                    "supplier_number": supplier_number_str,
                    "numeric_number": new_number
                }
                
            except ClientError:
                time.sleep(0.1 * (attempt + 1))
                continue
        
        # Fallback
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        return {
            "supplier_id": f"{cls.ID_PREFIX}T{timestamp}",
            "supplier_number": f"T{timestamp}",
            "numeric_number": timestamp
        }
    
    # ============= ADDRESS MANAGEMENT METHODS =============
    
    def add_address(self, 
                   street: str = None,
                   building: str = None,
                   area: str = None,
                   city: str = None,
                   state: str = None,
                   country: str = None,
                   postal_code: str = None,
                   landmark: str = None,
                   address_type: str = "primary",
                   is_primary: bool = False) -> SupplierAddress:
        """
        Add a new address to supplier
        
        Args:
            street: Street address
            building: Building name/floor
            area: Area/neighborhood
            city: City
            state: State/Province
            country: Country
            postal_code: ZIP/Postal code
            landmark: Nearby landmark
            address_type: Type of address
            is_primary: Whether this is primary address
        
        Returns: Created address object
        """
        if not self.addresses:
            self.addresses = []
        
        # If setting as primary, remove primary flag from others
        if is_primary:
            for addr in self.addresses:
                addr.is_primary = False
        
        address = SupplierAddress(
            street=street,
            building=building,
            area=area,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            landmark=landmark,
            address_type=address_type,
            is_primary=is_primary
        )
        
        self.addresses.append(address)
        self.save()
        
        # Update legacy address field for backward compatibility
        if is_primary:
            self.address = address.to_string()
            self.save()
        
        return address
    
    def get_primary_address(self) -> Optional[SupplierAddress]:
        """Get primary address"""
        if not self.addresses:
            return None
        
        for addr in self.addresses:
            if addr.is_primary:
                return addr
        
        return self.addresses[0] if self.addresses else None
    
    def update_primary_address(self, **address_data) -> SupplierAddress:
        """Update primary address with new data"""
        primary = self.get_primary_address()
        
        if primary:
            for key, value in address_data.items():
                if hasattr(primary, key):
                    setattr(primary, key, value)
        else:
            # Create new primary address
            primary = self.add_address(is_primary=True, **address_data)
        
        # Update legacy address field
        self.address = primary.to_string()
        self.save()
        
        return primary
    
    def get_address_by_type(self, address_type: str) -> List[SupplierAddress]:
        """Get addresses by type"""
        if not self.addresses:
            return []
        
        return [addr for addr in self.addresses if addr.address_type == address_type]
    
    # ============= CONTACT MANAGEMENT METHODS =============
    
    def add_contact_person(self,
                          name: str,
                          designation: str = None,
                          department: str = None,
                          email: str = None,
                          phone: str = None,
                          mobile: str = None,
                          is_primary: bool = False,
                          contact_hours: str = None,
                          notes: str = None) -> ContactPerson:
        """
        Add a new contact person
        
        Args:
            name: Full name
            designation: Job title
            department: Department
            email: Email address
            phone: Office phone
            mobile: Mobile phone
            is_primary: Primary contact flag
            contact_hours: Best contact hours
            notes: Additional notes
        
        Returns: Created contact person
        """
        if not self.contact_persons:
            self.contact_persons = []
        
        # If setting as primary, remove primary flag from others
        if is_primary:
            for contact in self.contact_persons:
                contact.is_primary = False
        
        contact = ContactPerson(
            name=name,
            designation=designation,
            department=department,
            email=email,
            phone=phone,
            mobile=mobile,
            is_primary=is_primary,
            contact_hours=contact_hours,
            notes=notes
        )
        
        self.contact_persons.append(contact)
        self.save()
        
        # Update legacy contact_person field for backward compatibility
        if is_primary:
            self.contact_person = name
            self.save()
        
        return contact
    
    def get_primary_contact(self) -> Optional[ContactPerson]:
        """Get primary contact person"""
        if not self.contact_persons:
            return None
        
        for contact in self.contact_persons:
            if contact.is_primary:
                return contact
        
        return self.contact_persons[0] if self.contact_persons else None
    
    def get_contacts_by_department(self, department: str) -> List[ContactPerson]:
        """Get contacts by department"""
        if not self.contact_persons:
            return []
        
        return [contact for contact in self.contact_persons 
                if contact.department == department]
    
    # ============= MANUAL ORDER PROCESSING METHODS =============
    
    def get_order_instructions(self) -> Dict[str, str]:
        """
        Get complete order instructions for manual processing
        
        Returns: Dictionary with all order-related information
        """
        primary_address = self.get_primary_address()
        primary_contact = self.get_primary_contact()
        
        instructions = {
            'supplier_name': self.supplier_name,
            'supplier_id': self.supplier_id,
            'type': self.type,
            'lead_time': self.lead_time_days,
            'minimum_order': self.minimum_order,
            'payment_terms': self.payment_terms,
            'delivery_method': self.delivery_method,
            'visiting_hours': self.visiting_hours,
            'warehouse_location': self.warehouse_location,
            'notes': self.notes,
        }
        
        if primary_address:
            instructions['address'] = {
                'full': primary_address.to_string(),
                'street': primary_address.street,
                'building': primary_address.building,
                'area': primary_address.area,
                'city': primary_address.city,
                'state': primary_address.state,
                'country': primary_address.country,
                'postal_code': primary_address.postal_code,
                'landmark': primary_address.landmark,
                'address_type': primary_address.address_type
            }
        
        if primary_contact:
            instructions['primary_contact'] = primary_contact.to_dict()
        
        # Add all contact persons
        if self.contact_persons:
            instructions['all_contacts'] = [
                contact.to_dict() for contact in self.contact_persons
            ]
        
        return instructions
    
    def get_printable_order_form(self) -> str:
        """
        Generate printable order form with supplier details
        
        Returns: Formatted string for printing
        """
        primary_address = self.get_primary_address()
        primary_contact = self.get_primary_contact()
        
        form_lines = [
            "=" * 60,
            f"SUPPLIER ORDER FORM - {self.supplier_name.upper()}",
            "=" * 60,
            f"Supplier ID: {self.supplier_id}",
            f"Type: {self.type or 'N/A'}",
            "",
            "=== CONTACT INFORMATION ===",
        ]
        
        if primary_contact:
            form_lines.extend([
                f"Primary Contact: {primary_contact.name}",
                f"Designation: {primary_contact.designation or 'N/A'}",
                f"Department: {primary_contact.department or 'N/A'}",
                f"Phone: {primary_contact.phone or 'N/A'}",
                f"Mobile: {primary_contact.mobile or 'N/A'}",
                f"Email: {primary_contact.email or 'N/A'}",
                f"Best Contact Hours: {primary_contact.contact_hours or 'N/A'}",
                f"Notes: {primary_contact.notes or 'N/A'}",
            ])
        else:
            form_lines.append("No primary contact specified")
        
        form_lines.extend([
            "",
            "=== ADDRESS ===",
        ])
        
        if primary_address:
            form_lines.extend([
                f"Full Address: {primary_address.to_string()}",
                f"Street: {primary_address.street or 'N/A'}",
                f"Building: {primary_address.building or 'N/A'}",
                f"Area: {primary_address.area or 'N/A'}",
                f"City: {primary_address.city or 'N/A'}",
                f"State: {primary_address.state or 'N/A'}",
                f"Country: {primary_address.country or 'N/A'}",
                f"Postal Code: {primary_address.postal_code or 'N/A'}",
                f"Landmark: {primary_address.landmark or 'N/A'}",
            ])
        else:
            form_lines.append("No address specified")
        
        form_lines.extend([
            "",
            "=== ORDER DETAILS ===",
            f"Lead Time: {self.lead_time_days or 'N/A'} days",
            f"Minimum Order: {self.minimum_order or 'N/A'}",
            f"Payment Terms: {self.payment_terms or 'N/A'}",
            f"Delivery Method: {self.delivery_method or 'N/A'}",
            f"Visiting Hours: {self.visiting_hours or 'N/A'}",
            f"Warehouse Location: {self.warehouse_location or 'N/A'}",
            "",
            "=== ORDER ITEMS ===",
            "Item | Quantity | Unit Price | Total",
            "-" * 40,
            "",
            "",
            "=== SIGNATURES ===",
            "Ordered By: ___________________ Date: ___________",
            "Received By: __________________ Date: ___________",
            "=" * 60,
        ])
        
        return "\n".join(form_lines)
    
    # ============= BASIC METHODS =============
    
    @classmethod
    def create_supplier(cls, supplier_data: Dict[str, Any]) -> 'Supplier':
        """Create supplier from data"""
        if 'supplier_name' not in supplier_data:
            raise ValueError("supplier_name is required")
        
        id_info = cls._get_next_supplier_id()
        supplier_id = id_info["supplier_id"]
        supplier_number = id_info["supplier_number"]
        
        supplier_data_with_ids = {
            "pk": "suppliers",
            "sk": supplier_id,
            "supplier_id": supplier_id,
            "supplier_number": supplier_number,
            **supplier_data
        }
        
        return cls(**supplier_data_with_ids)
    
    @classmethod
    def get_by_id(cls, supplier_id: str) -> Optional['Supplier']:
        """Get supplier by ID"""
        try:
            return cls.get("suppliers", supplier_id)
        except cls.DoesNotExist:
            return None
    
    def save(self, *args, **kwargs):
        """Override save to update timestamps"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        data = {
            'supplier_id': self.supplier_id,
            'supplier_number': self.supplier_number,
            'supplier_name': self.supplier_name,
            'contact_person': self.contact_person,
            'email': self.email,
            'phone_number': self.phone_number,
            'address': self.address,
            'type': self.type,
            'notes': self.notes,
            'isDeleted': self.isDeleted,
            'isFavorite': self.isFavorite,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'lead_time_days': self.lead_time_days,
            'minimum_order': self.minimum_order,
            'payment_terms': self.payment_terms,
            'delivery_method': self.delivery_method,
            'visiting_hours': self.visiting_hours,
            'warehouse_location': self.warehouse_location,
        }
        
        # Add timestamps
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        
        # Add enhanced addresses
        if self.addresses:
            data['addresses'] = []
            for addr in self.addresses:
                addr_dict = {
                    'street': addr.street,
                    'building': addr.building,
                    'area': addr.area,
                    'city': addr.city,
                    'state': addr.state,
                    'country': addr.country,
                    'postal_code': addr.postal_code,
                    'landmark': addr.landmark,
                    'address_type': addr.address_type,
                    'is_primary': addr.is_primary,
                    'full_address': addr.to_string()
                }
                data['addresses'].append(addr_dict)
        
        # Add enhanced contacts
        if self.contact_persons:
            data['contact_persons'] = [cp.to_dict() for cp in self.contact_persons]
        
        # Add sync logs if exists
        if self.sync_logs:
            data['sync_logs'] = []
            for log_item in self.sync_logs:
                log_dict = {'action': log_item.action}
                if log_item.object:
                    log_dict['object'] = log_item.object
                if log_item.last_updated:
                    log_dict['last_updated'] = log_item.last_updated.isoformat()
                if log_item.source:
                    log_dict['source'] = log_item.source
                if log_item.status:
                    log_dict['status'] = log_item.status
                if log_item.details:
                    log_dict['details'] = log_item.details
                data['sync_logs'].append(log_dict)
        
        return data


# ============= MANUAL ORDER PROCESSING UTILITY =============
class ManualOrderProcessor:
    """
    Utility for manual supplier order processing
    """
    
    @staticmethod
    def get_supplier_order_kit(supplier_id: str) -> Dict[str, Any]:
        """
        Get complete order kit for manual processing
        
        Args:
            supplier_id: Supplier ID
        
        Returns: Complete order kit with all details
        """
        supplier = Supplier.get_by_id(supplier_id)
        if not supplier:
            return {'error': 'Supplier not found'}
        
        return {
            'supplier': supplier.to_dict(),
            'order_instructions': supplier.get_order_instructions(),
            'printable_form': supplier.get_printable_order_form(),
            'order_checklist': ManualOrderProcessor._get_order_checklist(),
            'contact_sheet': ManualOrderProcessor._get_contact_sheet(supplier)
        }
    
    @staticmethod
    def _get_order_checklist() -> List[str]:
        """Get order processing checklist"""
        return [
            "☐ Check supplier visiting hours",
            "☐ Prepare purchase order document",
            "☐ Confirm payment terms",
            "☐ Check minimum order quantity",
            "☐ Arrange transportation if needed",
            "☐ Bring supplier contact details",
            "☐ Bring map/directions to address",
            "☐ Prepare payment method (cash/cheque)",
            "☐ Bring company identification",
            "☐ Note down order confirmation number",
            "☐ Get delivery date confirmation",
            "☐ Get receipt/order confirmation"
        ]
    
    @staticmethod
    def _get_contact_sheet(supplier: Supplier) -> Dict[str, Any]:
        """Get contact sheet for order processing"""
        primary_contact = supplier.get_primary_contact()
        primary_address = supplier.get_primary_address()
        
        return {
            'emergency_contacts': [
                {
                    'name': primary_contact.name if primary_contact else 'N/A',
                    'phone': primary_contact.mobile if primary_contact else supplier.phone_number,
                    'role': 'Primary Contact'
                }
            ],
            'address': primary_address.to_string() if primary_address else supplier.address,
            'visiting_hours': supplier.visiting_hours,
            'special_instructions': supplier.notes or 'No special instructions'
        }


# ============= USAGE EXAMPLES =============
if __name__ == "__main__":
    print("Supplier Model with Address Breakdown for Manual Orders")
    print("=" * 70)
    
    # Initialize
    if not Supplier.exists():
        Supplier.create_table(wait=True)
        print("Table created")
    
    # Example 1: Create supplier with complete address breakdown
    print("\n1. Creating supplier with detailed address:")
    
    supplier = Supplier.create_supplier({
        "supplier_name": "ABC Hardware Supplies",
        "type": "hardware",
        "notes": "Visit personally for bulk orders",
        "created_by": "USER-001"
    })
    
    # Add complete address breakdown
    supplier.add_address(
        street="123 Industrial Street",
        building="Unit 5, Level 2",
        area="Industrial Zone",
        city="Quezon City",
        state="Metro Manila",
        country="Philippines",
        postal_code="1100",
        landmark="Beside SM Hypermarket",
        address_type="warehouse",
        is_primary=True
    )
    
    # Add secondary address (office)
    supplier.add_address(
        street="456 Business Avenue",
        building="Suite 301",
        area="Central Business District",
        city="Makati",
        state="Metro Manila",
        country="Philippines",
        postal_code="1200",
        address_type="office"
    )
    
    # Add multiple contact persons
    supplier.add_contact_person(
        name="John Supplier",
        designation="Sales Manager",
        department="Sales",
        phone="+632-123-4567",
        mobile="+63-912-345-6789",
        email="john@abchardware.com",
        is_primary=True,
        contact_hours="9AM-5PM Mon-Fri",
        notes="Best to call in the morning"
    )
    
    supplier.add_contact_person(
        name="Maria Warehouse",
        designation="Warehouse Supervisor",
        department="Warehouse",
        mobile="+63-917-890-1234",
        contact_hours="8AM-4PM Mon-Sat",
        notes="Handles order pickups"
    )
    
    # Add order processing details
    supplier.lead_time_days = "3-5"
    supplier.minimum_order = "₱5,000"
    supplier.payment_terms = "Cash on Delivery"
    supplier.delivery_method = "Customer pickup or supplier delivery"
    supplier.visiting_hours = "9AM-6PM Mon-Sat"
    supplier.warehouse_location = "Back warehouse, Gate 3"
    
    supplier.save()
    
    print(f"Created: {supplier.supplier_id}")
    print(f"Name: {supplier.supplier_name}")
    print(f"Primary Address: {supplier.get_primary_address().to_string()}")
    print(f"Primary Contact: {supplier.get_primary_contact().name}")
    
    # Example 2: Get order instructions
    print("\n2. Getting order instructions:")
    instructions = supplier.get_order_instructions()
    print(f"Lead Time: {instructions['lead_time']}")
    print(f"Payment Terms: {instructions['payment_terms']}")
    print(f"Address: {instructions.get('address', {}).get('full', 'N/A')}")
    
    # Example 3: Generate printable order form
    print("\n3. Printable Order Form (first few lines):")
    form = supplier.get_printable_order_form()
    print("\n".join(form.split("\n")[:15]))
    
    # Example 4: Get complete order kit
    print("\n4. Complete Order Processing Kit:")
    order_kit = ManualOrderProcessor.get_supplier_order_kit(supplier.supplier_id)
    print(f"Kit contains: {list(order_kit.keys())}")
    
    # Example 5: Get contacts by department
    print("\n5. Warehouse Contacts:")
    warehouse_contacts = supplier.get_contacts_by_department("Warehouse")
    for contact in warehouse_contacts:
        print(f"  - {contact.name}: {contact.mobile} ({contact.notes})")
    
    # Example 6: Update primary address
    print("\n6. Updating primary address:")
    supplier.update_primary_address(
        building="Unit 8, Level 3",
        landmark="Opposite Robinsons Mall"
    )
    print(f"Updated address: {supplier.get_primary_address().to_string()}")
    
    # Example 7: Convert to API response
    print("\n7. API Response Structure:")
    api_data = supplier.to_dict()
    print(f"Has addresses: {len(api_data.get('addresses', []))} addresses")
    print(f"Has contact_persons: {len(api_data.get('contact_persons', []))} contacts")
    print(f"Order details included: {'lead_time_days' in api_data}")