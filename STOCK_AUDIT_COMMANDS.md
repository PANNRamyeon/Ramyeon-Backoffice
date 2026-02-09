# Stock Audit Django Management Commands

## 🎯 Overview

Two Django management commands to compare and fix stock mismatches between what PANNRamyeonCorner displays and what's in the cloud database.

**Why in PANN_POS Backend?**
- ✅ Database connection already configured
- ✅ ProductService and BatchService available
- ✅ CustomerProductService simulates API
- ✅ No duplicate configuration needed
- ✅ Integrated with Django's management system

## 📦 Commands Available

### 1. `compare_stock` - Identify Mismatches
Compares product stock across three sources:
- Cloud MongoDB (direct database access)
- Customer API simulation (CustomerProductService)
- Batch FIFO system (calculated stock)

### 2. `fix_stock` - Auto-Fix Issues
Automatically fixes identified stock mismatches with dry-run safety.

## 🚀 Quick Start

### Step 1: Navigate to Backend
```bash
cd C:\Users\ngjam\Desktop\PANN_POS\backend
```

### Step 2: Install Additional Dependencies
```bash
pip install tabulate python-dateutil
```

Or add to `requirements.txt`:
```txt
tabulate==0.9.0
python-dateutil==2.8.2
```

### Step 3: Run Comparison
```bash
python manage.py compare_stock
```

### Step 4: Fix Issues (if found)
```bash
# Dry run first (safe)
python manage.py fix_stock --fix-all

# Apply fixes
python manage.py fix_stock --fix-all --live
```

## 📚 Complete Command Reference

### `compare_stock` Command

#### Basic Usage
```bash
# Compare all products
python manage.py compare_stock

# Export results to JSON
python manage.py compare_stock --export stock_report.json

# Show matching products too
python manage.py compare_stock --show-matches

# Check specific product
python manage.py compare_stock --product-id PROD-00001

# Combine options
python manage.py compare_stock --show-matches --export report.json
```

#### Output Example
```
================================================================================
📊 STOCK COMPARISON SUMMARY
================================================================================

✅ Matching Products: 45
❌ Mismatched Products: 3
⚠️  Missing from API: 2

================================================================================
❌ STOCK MISMATCHES FOUND
================================================================================
+------------------+----------+-------+-------+-----+-------+---------+------------------+
| Product Name     | SKU      | Cloud | Total | API | Batch | Batches | Type             |
+------------------+----------+-------+-------+-----+-------+---------+------------------+
| Shin Ramyun      | NOOD-001 | 100   | 100   | 95  | 100   | 2       | cloud_vs_api     |
| Kimchi           | SIDE-002 | 50    | 50    | 50  | 45    | 1       | cloud_vs_batch   |
+------------------+----------+-------+-------+-----+-------+---------+------------------+
```

### `fix_stock` Command

#### Basic Usage
```bash
# Dry run all fixes (safe, default)
python manage.py fix_stock --fix-all

# Fix batch mismatches only
python manage.py fix_stock --fix-batches

# Fix stock/total_stock field sync
python manage.py fix_stock --fix-fields

# Fix products missing from API
python manage.py fix_stock --fix-missing

# Apply fixes (LIVE MODE)
python manage.py fix_stock --fix-all --live

# Fix specific product
python manage.py fix_stock --product-id PROD-00001 --fix-all --live

# Fix from comparison report
python manage.py fix_stock --from-report stock_report.json --live
```

#### Dry Run Mode (Default & Safe)
```bash
# These won't modify the database
python manage.py fix_stock --fix-batches
python manage.py fix_stock --fix-fields
python manage.py fix_stock --fix-all
```

#### Live Mode (Actually Fixes)
```bash
# Must add --live flag to apply changes
python manage.py fix_stock --fix-all --live

# You'll be prompted to confirm:
# Are you sure you want to continue? (yes/no): yes
```

## 🔍 What Gets Checked & Fixed

### Comparison Checks

| Check | Description |
|-------|-------------|
| **cloud_vs_api** | Cloud database stock vs Customer API stock |
| **cloud_vs_batch** | Cloud database stock vs Batch system calculation |
| **stock_vs_total_stock** | Product's `stock` field vs `total_stock` field |
| **missing_from_api** | Products with stock > 0 but not visible to customers |

### Fix Options

| Option | What It Fixes | Safe |
|--------|---------------|------|
| `--fix-batches` | Syncs product stock with batch calculations | ✅ Yes |
| `--fix-fields` | Syncs `stock` and `total_stock` fields | ✅ Yes |
| `--fix-missing` | Sets status to 'active' for products with stock | ⚠️ Check first |
| `--fix-all` | Runs all fixes | ⚠️ Dry run first |

## 📊 Complete Workflow Example

### Scenario: After Bulk Product Import

```bash
# 1. Navigate to backend
cd C:\Users\ngjam\Desktop\PANN_POS\backend

# 2. Run comparison and export
python manage.py compare_stock --export post_import_report.json

# 3. Review the report
# Check console output and post_import_report.json

# 4. Dry run fixes
python manage.py fix_stock --fix-all

# 5. Review what would change
# Check console output

# 6. Apply fixes
python manage.py fix_stock --fix-all --live

# 7. Verify fixes worked
python manage.py compare_stock --export verification_report.json

# 8. Compare before/after
# Check that mismatches are resolved
```

### Scenario: Single Product Issue

```bash
# 1. Check specific product
python manage.py compare_stock --product-id PROD-00025

# Output shows:
#   Cloud Stock: 100
#   API Stock: 100
#   Batch Stock: 95
#   Type: cloud_vs_batch

# 2. Fix just that product (dry run)
python manage.py fix_stock --product-id PROD-00025 --fix-batches

# 3. Apply fix
python manage.py fix_stock --product-id PROD-00025 --fix-batches --live

# 4. Verify
python manage.py compare_stock --product-id PROD-00025
```

### Scenario: Daily Health Check

```bash
# Run daily at 2 AM (add to cron/task scheduler)
cd C:\Users\ngjam\Desktop\PANN_POS\backend
python manage.py compare_stock --export daily_report_$(date +%Y%m%d).json
```

## 🎓 Understanding Mismatch Types

### Type 1: `cloud_vs_api`
**Symptom:** Database shows different stock than customer API
```
Cloud: 100 units
API: 95 units
Batch: 100 units
```
**Cause:** API cache not updated, or recent sales not reflected
**Fix:** Usually cache issue, verify with batch system (which is correct)

### Type 2: `cloud_vs_batch`
**Symptom:** Product stock doesn't match batch calculation
```
Cloud: 50 units
API: 50 units
Batch: 45 units (TRUTH)
```
**Cause:** Product stock not updated when batches were consumed
**Fix:** `--fix-batches` syncs with batch system

### Type 3: `stock_vs_total_stock`
**Symptom:** Internal fields don't match
```
stock: 100
total_stock: 95
```
**Cause:** One field updated without the other
**Fix:** `--fix-fields` syncs both fields

### Type 4: Missing from API
**Symptom:** Product has stock but not visible to customers
```
Cloud Stock: 10 units
Status: inactive
```
**Cause:** Status not set to 'active'
**Fix:** `--fix-missing` sets status to 'active'

## 🛡️ Safety Features

### 1. Dry Run by Default
```bash
# This is safe - won't modify database
python manage.py fix_stock --fix-all

# Must explicitly add --live to modify
python manage.py fix_stock --fix-all --live
```

### 2. Confirmation Prompt
```bash
python manage.py fix_stock --fix-all --live

🚨 LIVE MODE - This will modify the database!
================================================================================

Are you sure you want to continue? (yes/no): 
```

### 3. Detailed Logging
Every fix shows:
- Product name and SKU
- Current values
- New values
- Success/failure status

### 4. Batch System as Source of Truth
- Batch calculations are considered accurate
- Stock is synced TO match batches
- Expired batches automatically excluded

## 📋 Best Practices

### Before Running Fixes

1. **Always dry run first**
   ```bash
   python manage.py fix_stock --fix-all
   ```

2. **Backup database**
   ```bash
   mongodump --uri="your-mongodb-uri" --out=backup_$(date +%Y%m%d)
   ```

3. **Test with one product**
   ```bash
   python manage.py fix_stock --product-id PROD-00001 --fix-all --live
   ```

4. **Review comparison report**
   ```bash
   python manage.py compare_stock --export report.json
   # Review report.json
   ```

### After Major Operations

Run comparison after:
- Bulk product imports
- Batch stock updates
- Major sales events
- Database migrations
- Code deployments

### Scheduled Monitoring

```bash
# Add to cron (Linux/Mac)
0 2 * * * cd /path/to/PANN_POS/backend && python manage.py compare_stock --export daily_report.json

# Or Windows Task Scheduler
# Schedule: Daily at 2:00 AM
# Action: python manage.py compare_stock --export daily_report.json
```

## 🔧 Integration with Existing Services

### Uses Existing PANN_POS Services

```python
# compare_stock.py uses:
from app.services.product_service import ProductService
from app.services.batch_service import BatchService
from app.kpi_views.customer_product_views import CustomerProductService

# fix_stock.py uses:
from app.services.product_service import ProductService
from app.services.batch_service import BatchService
```

### Benefits of Integration

✅ No duplicate database connections  
✅ Reuses existing business logic  
✅ Consistent with rest of system  
✅ Access to all Django features  
✅ Integrated logging and error handling  

## 🎯 Common Use Cases

### Use Case 1: Post-Import Audit
```bash
# After importing 100 new products
python manage.py compare_stock --export post_import.json
python manage.py fix_stock --fix-batches --live
python manage.py compare_stock --export verification.json
```

### Use Case 2: Troubleshooting Customer Complaint
```
Customer: "Product shows 0 stock but I can't order it"

# Check the product
python manage.py compare_stock --product-id PROD-00042

# Shows: Cloud=0, API=Not Visible, Batch=0
# Product is correctly out of stock
```

### Use Case 3: Weekly Health Check
```bash
# Every Monday
python manage.py compare_stock --show-matches --export weekly_$(date +%Y%m%d).json

# If mismatches found:
python manage.py fix_stock --fix-all --live
```

### Use Case 4: After System Update
```bash
# After deploying new batch system code
python manage.py compare_stock --export after_update.json

# Verify all batch calculations match
# Fix any discrepancies
python manage.py fix_stock --fix-batches --live
```

## 📞 Troubleshooting

### Issue: Command Not Found
```bash
# Error: Unknown command: 'compare_stock'

# Solution: Ensure you're in the backend directory
cd C:\Users\ngjam\Desktop\PANN_POS\backend

# Verify command exists
python manage.py help compare_stock
```

### Issue: Import Errors
```bash
# Error: ModuleNotFoundError: No module named 'tabulate'

# Solution: Install dependencies
pip install tabulate python-dateutil
```

### Issue: Database Connection Error
```bash
# Error: ServerSelectionTimeoutError

# Solution: Check Django settings for MongoDB configuration
# Verify MongoDB URI in settings.py
```

### Issue: All Products Show Mismatches
```bash
# All products show cloud_vs_batch mismatch

# Solution: Batch system might need recalculation
python manage.py fix_stock --fix-batches --live
```

## 📈 Expected Results

### After First Run
- Clear visibility into stock health
- Identified mismatches categorized
- JSON report for record-keeping

### After Fixes
- Stock values synced across systems
- Customer API shows correct values
- Batch system matches database

### Ongoing
- Early detection of sync issues
- Prevention of customer-facing errors
- Data integrity maintained

## 🎊 Quick Reference Card

```bash
# COMPARISON
python manage.py compare_stock                      # Check all
python manage.py compare_stock --export report.json # Save report
python manage.py compare_stock --product-id PROD-01 # Check one

# FIXING (DRY RUN - SAFE)
python manage.py fix_stock --fix-all                # Check all fixes
python manage.py fix_stock --fix-batches            # Check batch sync
python manage.py fix_stock --fix-fields             # Check field sync

# FIXING (LIVE - APPLIES CHANGES)
python manage.py fix_stock --fix-all --live         # Apply all fixes
python manage.py fix_stock --fix-batches --live     # Apply batch sync
python manage.py fix_stock --from-report r.json --live # Fix from report
```

---

**Location:** `C:\Users\ngjam\Desktop\PANN_POS\backend\app\management\commands\`  
**Files:** `compare_stock.py`, `fix_stock.py`  
**Dependencies:** `tabulate`, `python-dateutil`  
**Django Version:** Compatible with PANN_POS backend  

**Next Step:** Run `python manage.py compare_stock` to start! 🚀


