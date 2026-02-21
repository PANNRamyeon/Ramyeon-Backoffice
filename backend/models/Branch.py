"""
Branch Model - Following ERD Specification with Address & Timestamp
PK = "branches", SK = "BRAN-##" (2-digit format)
Single Table Design using RamyeonCornerDB
"""
from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from app.utils import generate_sk, DYNAMO_TABLE_NAME, AWS_REGION
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Branch(Model):
    """
    BRANCH MODEL - Enhanced for Practical Use
    
    Core ERD Fields:
    - PK = branches
    - SK = BRAN-## (2-digit)
    - branch_name (String)
    
    Enhanced with:
    - address (String) - for location identifier
    - created_at (ISODATE) - for audit trail
    """
    
    class Meta:
        table_name = DYNAMO_TABLE_NAME  # RamyeonCornerDB (single table)
        region = AWS_REGION
        
        #if DYNAMODB_LOCAL:
        #    host = DYNAMODB_LOCAL_HOST
        
        # Minimal capacity for branch operations
        read_capacity_units = 3
        write_capacity_units = 3
    
    # ============= PRIMARY KEYS =============
    pk = UnicodeAttribute(hash_key=True, attr_name="PK", default="branches")
    sk = UnicodeAttribute(range_key=True, attr_name="SK")  # "BRAN-01" (2-digit)
    
    # ============= CORE ERD FIELDS =============
    branch_name = UnicodeAttribute()
    
    # ============= ENHANCED FIELDS =============
    address = UnicodeAttribute(null=True)  # For location identification
    created_at = UTCDateTimeAttribute(default_for_new=datetime.utcnow)  # For audit trail
    
    # ============= CLASS METHODS =============
    
    @classmethod
    def create_branch(cls, branch_name: str, address: str = None) -> 'Branch':
        """
        Create a new branch with auto-generated 2-digit SK
        
        Args:
            branch_name: Name of the branch (required)
            address: Physical address (optional)
        
        Returns:
            Branch: Created and saved branch instance
        
        Raises:
            ValueError: If branch_name is not provided
        """
        try:
            if not branch_name or not branch_name.strip():
                raise ValueError("branch_name is required")
            
            # Generate 2-digit SK using utils.py
            sk = generate_sk('BRAN-', 'branch_seq')
            
            # Create and save branch
            branch = cls(
                pk="branches",
                sk=sk,
                branch_name=branch_name.strip(),
                address=address.strip() if address else None,
                created_at=datetime.utcnow()
            )
            branch.save()
            
            logger.info(f"Branch created: {sk} - '{branch_name}' at {address or 'No address'}")
            return branch
            
        except Exception as e:
            logger.error(f"Failed to create branch: {str(e)}")
            raise
    
    @classmethod
    def get_by_id(cls, branch_id: str) -> 'Branch | None':
        """
        Get branch by ID
        
        Args:
            branch_id: Format "BRAN-01" or just "01"
        
        Returns:
            Branch or None if not found
        """
        try:
            # Ensure proper format
            if not branch_id.startswith('BRAN-'):
                branch_id = f"BRAN-{branch_id.zfill(2)}"  # Pad to 2 digits if needed
            
            return cls.get("branches", branch_id)
        except cls.DoesNotExist:
            logger.warning(f"Branch not found: {branch_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching branch {branch_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_name(cls, branch_name: str) -> 'Branch | None':
        """
        Get branch by exact name match
        
        Args:
            branch_name: Exact branch name to find
        
        Returns:
            Branch or None if not found
        """
        try:
            # Scan operation (acceptable for < 100 branches)
            for branch in cls.scan(cls.branch_name == branch_name):
                return branch
            return None
        except Exception as e:
            logger.error(f"Error finding branch by name '{branch_name}': {str(e)}")
            return None
    
    @classmethod
    def search_by_name(cls, search_term: str, limit: int = 10) -> list:
        """
        Search branches by name (partial, case-insensitive)
        
        Args:
            search_term: Search term
            limit: Maximum number of branches to return
        
        Returns:
            list: List of matching branches
        """
        try:
            branches = []
            search_term_lower = search_term.lower()
            
            # Scan all branches (acceptable for < 100 branches)
            for branch in cls.query("branches", limit=100):  # Max 99 branches
                if search_term_lower in branch.branch_name.lower():
                    branches.append(branch)
                    if len(branches) >= limit:
                        break
            
            return branches
        except Exception as e:
            logger.error(f"Error searching branches: {str(e)}")
            return []
    
    @classmethod
    def search_by_address(cls, search_term: str, limit: int = 10) -> list:
        """
        Search branches by address (partial, case-insensitive)
        
        Args:
            search_term: Search term for address
            limit: Maximum number of branches to return
        
        Returns:
            list: List of matching branches
        """
        try:
            branches = []
            search_term_lower = search_term.lower()
            
            # Scan all branches
            for branch in cls.query("branches", limit=100):
                if branch.address and search_term_lower in branch.address.lower():
                    branches.append(branch)
                    if len(branches) >= limit:
                        break
            
            return branches
        except Exception as e:
            logger.error(f"Error searching branches by address: {str(e)}")
            return []
    
    @classmethod
    def get_all_branches(cls) -> list:
        """
        Get all branches
        
        Returns:
            list: List of all branches
        """
        try:
            return list(cls.query("branches"))
        except Exception as e:
            logger.error(f"Error getting all branches: {str(e)}")
            return []
    
    @classmethod
    def get_branch_count(cls) -> int:
        """
        Get total number of branches
        
        Returns:
            int: Number of branches
        """
        try:
            count = 0
            for _ in cls.query("branches"):
                count += 1
            return count
        except Exception as e:
            logger.error(f"Error counting branches: {str(e)}")
            return 0
    
    @classmethod
    def get_branch_ids(cls) -> list:
        """
        Get list of all branch IDs
        
        Returns:
            list: List of branch IDs (SK values)
        """
        try:
            return [branch.sk for branch in cls.query("branches")]
        except Exception as e:
            logger.error(f"Error getting branch IDs: {str(e)}")
            return []
    
    @classmethod
    def get_branch_names(cls) -> list:
        """
        Get list of all branch names
        
        Returns:
            list: List of branch names
        """
        try:
            return [branch.branch_name for branch in cls.query("branches")]
        except Exception as e:
            logger.error(f"Error getting branch names: {str(e)}")
            return []
    
    @classmethod
    def branch_exists(cls, branch_name: str) -> bool:
        """
        Check if a branch with given name already exists
        
        Args:
            branch_name: Branch name to check
        
        Returns:
            bool: True if branch exists, False otherwise
        """
        try:
            return cls.get_by_name(branch_name) is not None
        except Exception as e:
            logger.error(f"Error checking branch existence: {str(e)}")
            return False
    
    @classmethod
    def get_branches_without_address(cls) -> list:
        """
        Get all branches that don't have an address set
        
        Returns:
            list: List of branches without address
        """
        try:
            branches = []
            for branch in cls.query("branches"):
                if not branch.address:
                    branches.append(branch)
            return branches
        except Exception as e:
            logger.error(f"Error getting branches without address: {str(e)}")
            return []
    
    @classmethod
    def get_branches_by_creation_date(cls, 
                                     start_date: datetime = None, 
                                     end_date: datetime = None) -> list:
        """
        Get branches created within a date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            list: List of branches created in the date range
        """
        try:
            branches = []
            for branch in cls.query("branches"):
                # Filter by date range if provided
                if start_date and end_date:
                    if start_date <= branch.created_at <= end_date:
                        branches.append(branch)
                elif start_date and branch.created_at >= start_date:
                    branches.append(branch)
                elif end_date and branch.created_at <= end_date:
                    branches.append(branch)
                else:
                    branches.append(branch)
            return branches
        except Exception as e:
            logger.error(f"Error getting branches by creation date: {str(e)}")
            return []
    
    # ============= INSTANCE METHODS =============
    
    def update_branch(self, branch_name: str = None, address: str = None) -> 'Branch':
        """
        Update branch name and/or address
        
        Args:
            branch_name: New branch name (optional)
            address: New address (optional)
        
        Returns:
            Branch: Updated branch instance
        """
        try:
            updated = False
            
            if branch_name is not None:
                if not branch_name.strip():
                    raise ValueError("branch_name cannot be empty")
                self.branch_name = branch_name.strip()
                updated = True
            
            if address is not None:
                self.address = address.strip() if address.strip() else None
                updated = True
            
            if updated:
                self.save()
                logger.info(f"Branch {self.sk} updated: name={branch_name or 'unchanged'}, address={address or 'unchanged'}")
            
            return self
        except Exception as e:
            logger.error(f"Failed to update branch: {str(e)}")
            raise
    
    def update_name(self, new_name: str) -> 'Branch':
        """
        Update branch name only
        
        Args:
            new_name: New branch name
        
        Returns:
            Branch: Updated branch instance
        """
        return self.update_branch(branch_name=new_name)
    
    def update_address(self, new_address: str) -> 'Branch':
        """
        Update branch address only
        
        Args:
            new_address: New address
        
        Returns:
            Branch: Updated branch instance
        """
        return self.update_branch(address=new_address)
    
    def get_location_info(self) -> dict:
        """
        Get location information for mapping/display
        
        Returns:
            dict: Location information
        """
        return {
            "branch_id": self.sk,
            "branch_name": self.branch_name,
            "address": self.address,
            "created_date": self.created_at.date().isoformat() if self.created_at else None,
            "age_days": (datetime.utcnow().date() - self.created_at.date()).days if self.created_at else None
        }
    
    def delete_branch(self):
        """
        Delete this branch from the database
        """
        try:
            self.delete()
            logger.info(f"Branch deleted: {self.sk} - '{self.branch_name}'")
        except Exception as e:
            logger.error(f"Failed to delete branch {self.sk}: {str(e)}")
            raise
    
    def to_dict(self) -> dict:
        """
        Convert branch to dictionary for API response
        
        Returns:
            dict: Dictionary representation
        """
        try:
            return {
                "branch_id": self.sk,
                "branch_name": self.branch_name,
                "address": self.address,
                "created_at": self.created_at.isoformat() if self.created_at else None
            }
        except Exception as e:
            logger.error(f"Error converting branch to dict: {str(e)}")
            return {}
    
    def to_simple_dict(self) -> dict:
        """
        Minimal dictionary representation (for basic listings)
        
        Returns:
            dict: Basic branch info
        """
        try:
            return {
                "id": self.sk,
                "name": self.branch_name,
                "address": self.address or "No address"
            }
        except Exception as e:
            logger.error(f"Error converting branch to simple dict: {str(e)}")
            return {}
    
    def to_audit_dict(self) -> dict:
        """
        Dictionary for audit trail purposes
        
        Returns:
            dict: Audit trail representation
        """
        try:
            return {
                "entity_type": "branch",
                "branch_id": self.sk,
                "branch_name": self.branch_name,
                "address": self.address,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "audit_timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error converting branch to audit dict: {str(e)}")
            return {}


# ============= BRANCH VALIDATION =============
def validate_branch_id(branch_id: str) -> bool:
    """
    Validate if a branch ID is in correct format
    
    Args:
        branch_id: Branch ID to validate
    
    Returns:
        bool: True if valid format, False otherwise
    """
    try:
        if not branch_id:
            return False
        
        # Check format: BRAN-## where ## are exactly 2 digits
        if not branch_id.startswith('BRAN-'):
            return False
        
        number_part = branch_id[5:]  # Remove "BRAN-"
        if len(number_part) != 2:
            return False
        
        # Check if it's a valid number (01-99)
        number = int(number_part)
        return 1 <= number <= 99
        
    except (ValueError, IndexError):
        return False


def format_branch_id(number: int) -> str:
    """
    Format a number as a branch ID
    
    Args:
        number: Number to format (1-99)
    
    Returns:
        str: Formatted branch ID (BRAN-##)
    
    Raises:
        ValueError: If number is not between 1 and 99
    """
    if not 1 <= number <= 99:
        raise ValueError("Branch number must be between 1 and 99")
    
    return f"BRAN-{number:02d}"


def validate_branch_data(branch_name: str, address: str = None) -> tuple[bool, str]:
    """
    Validate branch data before creation
    
    Args:
        branch_name: Branch name to validate
        address: Address to validate (optional)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not branch_name or not branch_name.strip():
        return False, "Branch name is required"
    
    if len(branch_name.strip()) > 100:
        return False, "Branch name must be 100 characters or less"
    
    if address and len(address.strip()) > 200:
        return False, "Address must be 200 characters or less"
    
    return True, ""


# ============= BULK OPERATIONS =============
def create_initial_branches(branch_data: list[dict]) -> dict:
    """
    Create multiple branches at once (for initialization)
    
    Args:
        branch_data: List of dictionaries with 'name' and optional 'address'
    
    Returns:
        dict: Summary of creation results
    """
    created_branches = []
    errors = []
    
    for data in branch_data:
        try:
            name = data.get('name')
            address = data.get('address')
            
            if not name:
                errors.append(f"Missing branch name in data: {data}")
                continue
            
            # Check if branch already exists
            if Branch.branch_exists(name):
                errors.append(f"Branch '{name}' already exists")
                continue
            
            branch = Branch.create_branch(name, address)
            created_branches.append(branch.to_dict())
            
        except Exception as e:
            errors.append(f"Failed to create branch from data {data}: {str(e)}")
    
    return {
        "created": created_branches,
        "total_created": len(created_branches),
        "errors": errors,
        "success": len(errors) == 0
    }


def update_branches_address(branch_updates: list[dict]) -> dict:
    """
    Update addresses for multiple branches
    
    Args:
        branch_updates: List of dicts with 'branch_id' and 'address'
    
    Returns:
        dict: Summary of update results
    """
    updated = []
    errors = []
    
    for update in branch_updates:
        try:
            branch_id = update.get('branch_id')
            address = update.get('address')
            
            if not branch_id:
                errors.append(f"Missing branch_id in update: {update}")
                continue
            
            branch = Branch.get_by_id(branch_id)
            if not branch:
                errors.append(f"Branch not found: {branch_id}")
                continue
            
            branch.update_address(address)
            updated.append({
                "branch_id": branch_id,
                "new_address": address
            })
            
        except Exception as e:
            errors.append(f"Failed to update branch {update.get('branch_id')}: {str(e)}")
    
    return {
        "updated": updated,
        "total_updated": len(updated),
        "errors": errors,
        "success": len(errors) == 0
    }


# ============= BRANCH MANAGER =============
class BranchManager:
    """
    Manager class for branch-related operations
    """
    
    @staticmethod
    def get_branch_summary() -> dict:
        """
        Get summary statistics for all branches
        
        Returns:
            dict: Branch summary
        """
        try:
            branches = Branch.get_all_branches()
            total = len(branches)
            with_address = sum(1 for b in branches if b.address)
            without_address = total - with_address
            
            # Group by creation month
            from collections import defaultdict
            by_month = defaultdict(int)
            for branch in branches:
                if branch.created_at:
                    month_key = branch.created_at.strftime("%Y-%m")
                    by_month[month_key] += 1
            
            return {
                "total_branches": total,
                "with_address": with_address,
                "without_address": without_address,
                "address_coverage": (with_address / total * 100) if total > 0 else 0,
                "branches_by_month": dict(by_month),
                "oldest_branch": min(branches, key=lambda x: x.created_at).sk if branches else None,
                "newest_branch": max(branches, key=lambda x: x.created_at).sk if branches else None
            }
            
        except Exception as e:
            logger.error(f"Error getting branch summary: {str(e)}")
            return {}
    
    @staticmethod
    def export_branches_to_csv_format() -> list:
        """
        Export branches in CSV-friendly format
        
        Returns:
            list: List of dictionaries for CSV export
        """
        try:
            branches = Branch.get_all_branches()
            csv_data = []
            
            for branch in branches:
                csv_data.append({
                    "branch_id": branch.sk,
                    "branch_name": branch.branch_name,
                    "address": branch.address or "",
                    "created_at": branch.created_at.isoformat() if branch.created_at else "",
                    "created_date": branch.created_at.date().isoformat() if branch.created_at else ""
                })
            
            return csv_data
            
        except Exception as e:
            logger.error(f"Error exporting branches: {str(e)}")
            return []
    
    @staticmethod
    def find_nearby_branches(location_keywords: list, limit: int = 5) -> list:
        """
        Find branches by location keywords in address
        
        Args:
            location_keywords: List of location keywords (e.g., ["downtown", "main st"])
            limit: Maximum number of branches to return
        
        Returns:
            list: List of matching branches
        """
        try:
            branches = Branch.get_all_branches()
            matching_branches = []
            
            for branch in branches:
                if not branch.address:
                    continue
                
                address_lower = branch.address.lower()
                for keyword in location_keywords:
                    if keyword.lower() in address_lower:
                        matching_branches.append(branch)
                        break
                
                if len(matching_branches) >= limit:
                    break
            
            return matching_branches
            
        except Exception as e:
            logger.error(f"Error finding nearby branches: {str(e)}")
            return []

