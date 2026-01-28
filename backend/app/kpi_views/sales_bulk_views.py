from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from ..services.saleslog_service import SalesLogService

from datetime import datetime
import logging
import csv
import io
import re

logger = logging.getLogger(__name__)

class SalesLogBulkImportView(APIView):
    """
    CSV-only bulk import view for sales transactions
    Features: CSV import with comprehensive item code processing and validation
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sales_service = SalesLogService()
        
        # Configuration constants
        self.BATCH_SIZE = 50
        self.MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        self.DEFAULT_CUSTOMER_ID = "6841a20f37eca0bad1552dd5"
        self.DEFAULT_USER_ID = "6841a20f37eca0bad1552dd5"
        
        # Item code validation
        self.CODE_MIN_LENGTH = 2
        self.CODE_MAX_LENGTH = 20
        self.CODE_PATTERN = r'^[A-Za-z0-9_-]{2,20}$'

    # ====================================================================
    # MAIN ENTRY POINT - CSV ONLY
    # ====================================================================

    def post(self, request):
        """Main entry point for CSV import only"""
        try:
            if 'file' not in request.FILES:
                return Response({
                    'error': 'No CSV file provided. Please upload a CSV file.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return self.import_from_csv(request)
                
        except Exception as e:
            logger.error(f"Error in CSV import: {str(e)}")
            return Response({
                'error': f'CSV import failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ====================================================================
    # CSV IMPORT METHODS
    # ====================================================================

    def import_from_csv(self, request):
        """Process CSV import with comprehensive validation"""
        try:
            csv_file = request.FILES['file']
            
            # Validate CSV file
            validation_error = self._validate_csv_file(csv_file)
            if validation_error:
                return validation_error
            
            # Read and parse CSV
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            # Convert to list for processing
            transactions = list(csv_data)
            total_rows = len(transactions)
            
            if total_rows == 0:
                return Response({
                    'error': 'CSV file contains no data rows'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Starting CSV import: {total_rows} transactions from '{csv_file.name}'")
            
            # Pre-validate transactions
            validation_results = self._validate_transactions(transactions)
            
            # Process transactions
            results = self._process_transactions(transactions)
            
            # Add validation warnings
            if validation_results['warnings']:
                results['warnings'] = validation_results['warnings']
            
            logger.info(f"CSV import completed: {results['summary']['successful']} successful, {results['summary']['failed']} failed")
            
            return Response(results, status=status.HTTP_201_CREATED)
            
        except UnicodeDecodeError:
            logger.error("CSV file encoding error")
            return Response({
                'error': 'Invalid file encoding. Please ensure the CSV file is UTF-8 encoded.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error importing CSV: {str(e)}")
            return Response({
                'error': f'CSV import failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _validate_csv_file(self, csv_file):
        """Validate CSV file requirements"""
        # Check file extension
        if not csv_file.name.lower().endswith('.csv'):
            return Response({
                'error': 'File must be a CSV (.csv extension required)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check file size
        if csv_file.size > self.MAX_FILE_SIZE:
            return Response({
                'error': f'File size must be less than {self.MAX_FILE_SIZE // (1024*1024)}MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if file is empty
        if csv_file.size == 0:
            return Response({
                'error': 'File is empty'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return None

    def _validate_transactions(self, transactions):
        """Pre-validate transactions and generate warnings"""
        warnings = []
        
        # Check for duplicate codes
        duplicate_codes = self._check_duplicate_codes(transactions)
        if duplicate_codes:
            warnings.append({
                'type': 'duplicate_codes',
                'count': len(duplicate_codes),
                'message': f"Found {len(duplicate_codes)} duplicate item codes",
                'details': duplicate_codes[:5]
            })
        
        # Check for missing required fields
        missing_fields = self._check_missing_fields(transactions)
        if missing_fields:
            warnings.append({
                'type': 'missing_fields',
                'count': len(missing_fields),
                'message': f"Found {len(missing_fields)} rows with missing required fields",
                'details': missing_fields[:5]
            })
        
        # Check for invalid codes
        invalid_codes = self._check_invalid_codes(transactions)
        if invalid_codes:
            warnings.append({
                'type': 'invalid_codes',
                'count': len(invalid_codes),
                'message': f"Found {len(invalid_codes)} rows with invalid item codes",
                'details': invalid_codes[:5]
            })
        
        return {'warnings': warnings}

    # ====================================================================
    # TRANSACTION PROCESSING
    # ====================================================================

    def _process_transactions(self, transactions):
        """Process transactions in batches"""
        created_invoices = []
        failed_transactions = []
        total_transactions = len(transactions)
        
        logger.info(f"Processing {total_transactions} transactions in batches of {self.BATCH_SIZE}")
        
        # Process in batches
        for batch_start in range(0, total_transactions, self.BATCH_SIZE):
            batch_end = min(batch_start + self.BATCH_SIZE, total_transactions)
            batch = transactions[batch_start:batch_end]
            
            # Process each transaction in batch
            for index, transaction in enumerate(batch):
                row_number = batch_start + index + 1
                
                try:
                    # Map transaction to invoice
                    invoice_data = self._map_transaction_to_invoice(
                        transaction, row_number
                    )
                    
                    # Create invoice
                    created_invoice = self.sales_service.create_invoice(invoice_data)
                    created_invoices.append(created_invoice)
                    
                except Exception as e:
                    failed_transactions.append({
                        'row': row_number,
                        'data': self._sanitize_transaction_data(transaction),
                        'error': str(e)
                    })
                    logger.warning(f"Failed to process row {row_number}: {str(e)}")
        
        # Generate results
        return self._generate_results(total_transactions, created_invoices, failed_transactions)

    def _map_transaction_to_invoice(self, transaction, row_number):
        """Map CSV transaction to invoice format"""
        
        # Extract and validate basic fields
        raw_code = transaction.get('Code', transaction.get('code', ''))
        product = str(transaction.get('Product', transaction.get('product', ''))).strip()
        uom = str(transaction.get('UOM', transaction.get('uom', 'pc'))).strip()
        
        # Validate required fields
        if not product:
            raise ValueError("Product name is required")
        
        # Process item code
        item_code, was_generated = self._process_item_code(raw_code, product, row_number)
        
        # Parse numeric fields
        quantity = self._parse_number(transaction.get('Quantity', transaction.get('quantity', 1)))
        total_before_tax = self._parse_number(transaction.get('Total before tax', transaction.get('total_before_tax', 0)))
        total = self._parse_number(transaction.get('Total', transaction.get('total', 0)))
        
        # Validate numeric fields
        if quantity <= 0:
            quantity = 1
            logger.warning(f"Row {row_number}: Invalid quantity, defaulting to 1")
        
        if total == 0 and total_before_tax > 0:
            total = total_before_tax
        
        if total <= 0:
            raise ValueError(f"Invalid total amount: {total}")
        
        # Calculate tax
        tax_amount = max(0, total - total_before_tax)
        tax_rate = tax_amount / total_before_tax if total_before_tax > 0 else 0
        
        # Create item list
        item_list = [{
            'item_code': item_code,
            'item_name': product,
            'quantity': quantity,
            'unit_of_measure': uom,
            'unit_price': round(total_before_tax / quantity, 2) if quantity > 0 else 0,
            'total_price': round(total_before_tax, 2),
            'tax_amount': round(tax_amount, 2),
            'imported_from_csv': True,
            'original_code': raw_code,
            'code_was_generated': was_generated,
            'import_row_number': row_number
        }]
        
        # Create invoice data
        invoice_data = {
            'customer_id': self.DEFAULT_CUSTOMER_ID,
            'user_id': self.DEFAULT_USER_ID,
            'transaction_date': datetime.utcnow(),
            'total_amount': round(total, 2),
            'status': 'completed',
            'payment_method': 'cash',
            'sales_type': 'dine_in',
            'tax_rate': round(tax_rate, 4),
            'tax_amount': round(tax_amount, 2),
            'is_taxable': tax_amount > 0,
            'notes': f'Code: {item_code} | {product}',
            'item_list': item_list,
            'sync_logs': [{
                'source': 'csv',
                'imported_at': datetime.utcnow().isoformat(),
                'csv_code': raw_code,
                'processed_code': item_code,
                'csv_product': product,
                'csv_row': row_number,
                'code_generated': was_generated
            }]
        }
        
        return invoice_data

    # ====================================================================
    # ITEM CODE PROCESSING
    # ====================================================================

    def _process_item_code(self, code, product_name, row_number):
        """Process and validate item code"""
        raw_code = str(code).strip() if code else ''
        
        # Generate code if empty
        if not raw_code:
            generated_code = self._generate_item_code(product_name, row_number)
            return generated_code, True
        
        # Validate existing code
        if not self._is_valid_code_format(raw_code):
            fixed_code = self._fix_item_code(raw_code)
            if self._is_valid_code_format(fixed_code):
                return fixed_code, False
            else:
                generated_code = self._generate_item_code(product_name, row_number)
                return generated_code, True
        
        return raw_code.upper(), False

    def _generate_item_code(self, product_name, row_number):
        """Generate item code from product name"""
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', product_name)
        
        if len(clean_name) >= 3:
            words = re.findall(r'[A-Z][a-z]*|[a-z]+|\d+', product_name)
            
            if len(words) >= 2:
                prefix = (words[0][:2] + words[1][:2]).upper()
                code = f"{prefix}{row_number:02d}"
            else:
                prefix = clean_name[:4].upper()
                code = f"{prefix}{row_number:02d}"
        else:
            code = f"ITEM{row_number:03d}"
        
        if len(code) > self.CODE_MAX_LENGTH:
            code = code[:self.CODE_MAX_LENGTH-2] + f"{row_number:02d}"
        
        return code

    def _fix_item_code(self, code):
        """Fix invalid item codes"""
        fixed = re.sub(r'[^A-Za-z0-9_-]', '', code)
        
        if len(fixed) < self.CODE_MIN_LENGTH:
            fixed = fixed + 'X' * (self.CODE_MIN_LENGTH - len(fixed))
        
        if len(fixed) > self.CODE_MAX_LENGTH:
            fixed = fixed[:self.CODE_MAX_LENGTH]
        
        return fixed.upper()

    def _is_valid_code_format(self, code):
        """Validate item code format"""
        return bool(re.match(self.CODE_PATTERN, code))

    # ====================================================================
    # VALIDATION HELPERS
    # ====================================================================

    def _check_duplicate_codes(self, transactions):
        """Check for duplicate item codes"""
        codes_seen = {}
        duplicates = []
        
        for index, transaction in enumerate(transactions):
            code = str(transaction.get('Code', transaction.get('code', ''))).strip().upper()
            
            if code:
                if code in codes_seen:
                    duplicates.append({
                        'code': code,
                        'rows': [codes_seen[code], index + 1]
                    })
                else:
                    codes_seen[code] = index + 1
        
        return duplicates

    def _check_missing_fields(self, transactions):
        """Check for missing required fields"""
        missing_fields = []
        
        for index, transaction in enumerate(transactions):
            missing = []
            
            product = str(transaction.get('Product', transaction.get('product', ''))).strip()
            if not product:
                missing.append('Product')
            
            quantity = transaction.get('Quantity', transaction.get('quantity', ''))
            if not quantity:
                missing.append('Quantity')
            
            total = transaction.get('Total', transaction.get('total', ''))
            total_before_tax = transaction.get('Total before tax', transaction.get('total_before_tax', ''))
            if not total and not total_before_tax:
                missing.append('Total')
            
            if missing:
                missing_fields.append({
                    'row': index + 1,
                    'missing_fields': missing
                })
        
        return missing_fields

    def _check_invalid_codes(self, transactions):
        """Check for invalid item codes"""
        invalid_codes = []
        
        for index, transaction in enumerate(transactions):
            code = str(transaction.get('Code', transaction.get('code', ''))).strip()
            
            if code and not self._is_valid_code_format(code):
                invalid_codes.append({
                    'row': index + 1,
                    'invalid_code': code
                })
        
        return invalid_codes

    # ====================================================================
    # UTILITY METHODS
    # ====================================================================

    def _parse_number(self, value):
        """Parse number from string with error handling"""
        if value is None:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        str_value = str(value).strip()
        if not str_value:
            return 0.0
        
        # Clean formatting
        cleaned = re.sub(r'[,$\s₱]', '', str_value)
        
        # Handle parentheses (negative)
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        # Remove non-numeric characters except decimal and minus
        cleaned = re.sub(r'[^\d.-]', '', cleaned)
        
        # Handle multiple decimals
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse number: '{value}', defaulting to 0.0")
            return 0.0

    def _sanitize_transaction_data(self, transaction):
        """Sanitize transaction data for error reporting"""
        if not isinstance(transaction, dict):
            return str(transaction)
        
        return {
            'Code': transaction.get('Code', transaction.get('code', '')),
            'Product': transaction.get('Product', transaction.get('product', '')),
            'Quantity': transaction.get('Quantity', transaction.get('quantity', '')),
            'Total': transaction.get('Total', transaction.get('total', ''))
        }

    def _generate_results(self, total_transactions, created_invoices, failed_transactions):
        """Generate import results"""
        success_rate = (len(created_invoices) / total_transactions * 100) if total_transactions > 0 else 0
        
        return {
            'message': 'CSV import completed',
            'summary': {
                'total_processed': total_transactions,
                'successful': len(created_invoices),
                'failed': len(failed_transactions),
                'success_rate': round(success_rate, 2)
            },
            'created_invoices': created_invoices,
            'failed_transactions': failed_transactions,
            'import_statistics': {
                'batch_size_used': self.BATCH_SIZE,
                'processing_time': datetime.utcnow().isoformat(),
                'source': 'csv'
            }
        }


# ====================================================================
# CSV TEMPLATE GENERATION
# ====================================================================

class SalesLogTemplateView(APIView):
    """Generate CSV template for sales import"""
    
    def get(self, request):
        """Download CSV template with examples"""
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="sales_import_template.csv"'
            
            writer = csv.writer(response)
            
            # Write header
            writer.writerow([
                'Code', 'Product', 'Quantity', 'UOM', 
                'Total before tax', 'Total'
            ])
            
            # Write sample data
            sample_data = [
                ['NAD017', 'Alaska Fortified', '8', 'pc', '240.00', '240.00'],
                ['SB025', 'Anjo Tonmen Seafood', '1', 'pc', '75.00', '75.00'],
                ['SF013', 'Bae Hong Dong', '5', 'pc', '350.00', '350.00'],
                ['TO017', 'Beef Loaf', '2', 'pc', '10.00', '10.00'],
                ['SF050', 'Bibim Paldo', '3', 'pc', '161.00', '161.00'],
                ['NAD052', 'Binggrae Asstd', '40', 'pc', '2,800.00', '2,800.00'],
                ['', 'Auto-Generated Code Example', '2', 'kg', '50.00', '55.00'],
            ]
            
            for row in sample_data:
                writer.writerow(row)
            
            logger.info("CSV template generated successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error generating template: {str(e)}")
            return Response({
                'error': f'Failed to generate template: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class SalesLogExportView(APIView):
    """Export sales transactions to CSV"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sales_service = SalesLogService()
    
    def get(self, request):
        """Export sales transactions to CSV with optional filtering"""
        try:
            # Get filter parameters from query string
            filters = {
                'start_date': request.GET.get('start_date'),
                'end_date': request.GET.get('end_date'),
                'sales_type': request.GET.get('sales_type'),
                'payment_method': request.GET.get('payment_method'),
                'customer_id': request.GET.get('customer_id'),
                'status': request.GET.get('status', 'completed')
            }
            
            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}
            
            logger.info(f"Exporting sales transactions with filters: {filters}")
            
            # Get transactions from service
            transactions = self.sales_service.get_transactions_for_export(filters)
            
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            
            # Generate filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'sales_export_{timestamp}.csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Write CSV data
            writer = csv.writer(response)
            
            # Write header
            writer.writerow([
                'Transaction ID',
                'Transaction Date',
                'Customer ID', 
                'Item Code',
                'Item Name',
                'Quantity',
                'Unit Price',
                'Total Price',
                'Payment Method',
                'Sales Type',
                'Status',
                'Tax Amount',
                'Total Amount'
            ])
            
            # Write data rows
            for transaction in transactions:
                transaction_id = str(transaction.get('_id', ''))
                transaction_date = transaction.get('transaction_date', '')
                customer_id = str(transaction.get('customer_id', ''))
                payment_method = transaction.get('payment_method', '')
                sales_type = transaction.get('sales_type', '')
                status_val = transaction.get('status', '')
                tax_amount = transaction.get('tax_amount', 0)
                total_amount = transaction.get('total_amount', 0)
                
                # Handle item list
                item_list = transaction.get('item_list', [])
                if not isinstance(item_list, list):
                    item_list = [item_list] if item_list else []
                
                # Write one row per item
                for item in item_list:
                    writer.writerow([
                        transaction_id,
                        transaction_date,
                        customer_id,
                        item.get('item_code', ''),
                        item.get('item_name', ''),
                        item.get('quantity', 0),
                        item.get('unit_price', 0),
                        item.get('total_price', 0),
                        payment_method,
                        sales_type,
                        status_val,
                        tax_amount,
                        total_amount
                    ])
            
            logger.info(f"Successfully exported {len(transactions)} transactions")
            return response
            
        except Exception as e:
            logger.error(f"Error exporting transactions: {str(e)}")
            return Response({
                'error': f'Export failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)