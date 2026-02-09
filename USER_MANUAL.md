# PANN POS Back Office – User Guide

This guide explains how store owners and supervisors can manage the business using the **PANN POS Back Office** (web dashboard).

---

## 1. Signing In

1. Open your browser and go to the back-office URL (for example, `https://backoffice.yourdomain.com` or the address given by IT).
2. Enter your email/username and password.
3. Click **Log In**.  
   - If you see a blank screen or are redirected to the login page again, check that your browser allows cookies and that you entered the correct password.

> **Tip:** Click your name in the upper-right corner to log out when you are done.

---

## 2. Layout Overview

Once logged in, you will see:

- **Sidebar (left):** Quick links to Dashboard, Accounts, Customers, Inventory, Suppliers, Promotions, Reports, Logs, Notifications, and your Profile.
- **Top Bar:** Displays the page title, search/filters (when available), notification bell, and user menu.
- **Main Area:** Shows the information or tools for the page you picked.

Use the sidebar to move between sections. The active page is highlighted.

---

## 3. Dashboard

The Dashboard gives a quick health check of the business.

- **Summary Cards:** Show total profit, monthly revenue, total products, and number of orders.
- **Sales Trend Chart:** Change the view (daily/weekly/monthly/yearly) to see sales over time.
- **Target Sales Indicator:** Shows progress toward the reorder target so you know when to place a purchase order.

You do not need to update anything here; check it daily to track performance.

---

## 4. Managing Users (Accounts)

**Menu:** Accounts → User Management

Use this page to add or update staff logins.

- **Add User:** Click **ADD USER**, choose a role (Admin, Manager, Cashier, etc.), and fill in the form.  
  Make sure the email is correct because it’s used for verification.
- **Edit or View:** Use the eye (view) or pencil (edit) button in the Actions column.
- **Deactivate or Delete:** Select users using the checkboxes, then choose the proper action. Deactivate instead of deleting if you want to keep their history.
- **Export List:** Click **Export** on the action bar to download all users as a spreadsheet.

Only administrators should manage user accounts.

---

## 5. Customers

**Menu:** Customers

- View all customers captured from POS or online orders.
- Search by name, email, or loyalty ID.
- Click a row to see contact details, loyalty points, and order history.
- Update customer records with the **Edit** button, or archive inactive customers.

---

## 6. Inventory Management

### 6.1 Products List

**Menu:** Inventory → Products

- Shows all active items with price, stock, and status.
- Use the search bar or filters (category, stock level, status).
- **Add Product:** Click **Add Product** to create a new item (name, SKU, price, VAT, category, stock tracking).
- **Edit:** Use the pencil icon.
- **Bulk Actions:** Select multiple rows to update status (e.g., mark as inactive).

### 6.2 Bulk Product Entry

**Menu:** Inventory → Bulk Product Entry

- Import multiple products using the provided CSV template.
- Download the template, fill it out, then upload it.
- Review the preview list before confirming the import.

### 6.3 Product Details

Click any product to open its detail page.

- View full description, pricing, stock levels, batches, and sales history.
- Update product pictures and assigned categories.
- Adjust stock manually and see who made the change.

### 6.4 Categories

**Menu:** Inventory → Categories

- Organize products by category and subcategory.
- Drag and drop to reorder categories (affects POS layout).
- Click **Add Category** to create new groups.
- Use **Uncategorized Products** to find items that need a category.

---

## 7. Suppliers and Purchase Orders

**Menu:** Suppliers

- View all suppliers with contact info.
- Click a supplier to see product lists, purchase history, and notes.
- **Orders History:** Shows past purchase orders and their status.
- Create new purchase orders (if enabled) to restock inventory.
- Export supplier lists for accounting.

---

## 8. Promotions

**Menu:** Promotions

- Set up discounts or bundles for POS and online channels.
- Choose promotion type (percentage, fixed amount, buy X get Y).
- Set the schedule (start/end dates) and targeted products/categories.
- Activate or deactivate promotions as needed.

---

## 9. Reports

### Sales by Item

**Menu:** Reports → Sales by Item

- Filter by date range, branch (if applicable), or payment type.
- Download the report as CSV for accounting or analysis.

### Sales by Category

**Menu:** Reports → Sales by Category

- Shows which categories perform best.
- Use filters similar to the item report.
- Export as CSV to share with management.

You can also check other reports (if available) for online vs POS comparisons, loyalty summaries, etc.

---

## 10. Notifications & Logs

### Notifications

**Menu:** Notifications → All Notifications

- Lists system messages such as new online orders, low stock alerts, or failed syncs.
- Click **Mark as Read** to clear the badge total.
- Use the filters to view by priority or type.

### System Logs

**Menu:** Logs

- Shows technical logs for troubleshooting (admin use).
- Filter by date or event type.
- Export logs to share with developers when reporting issues.

---

## 11. Profile & Password

**Menu:** Profile (click your name or Profile link)

- Review your own account information.
- Change your password under **Security**.
- Toggle dark/light theme for the dashboard.

If you cannot update your email or role, ask an administrator—they control account permissions.

---

## 12. Tips & Best Practices

- **Regular Backups:** IT should back up MongoDB and application data regularly.
- **Stock Accuracy:** Update product stock after inventory counts or supplier deliveries.
- **Promotions:** Disable promotions once campaigns end to avoid accidental discounts.
- **User Access:** Remove or deactivate users who no longer work in the business.
- **Reports:** Download sales reports at the end of each day/week for financial tracking.
- **Sync with POS:** The back office and POS share the same database. Changes here appear in the POS shortly after saving.

---

## 13. Troubleshooting

| Problem | What to Try |
| --- | --- |
| Cannot log in | Make sure caps lock is off; if forgotten, ask another admin to reset your password. |
| Page stuck loading | Refresh the browser (F5) or sign out and back in. Check internet connection. |
| Stock numbers look wrong | Verify recent purchase orders or run the stock sync command provided by IT. |
| Promotion didn’t apply | Confirm the promotion is active and includes the correct products/dates. |
| No email notifications | Ensure your account’s email is correct and verified. Check spam folder. |

If issues persist, take a screenshot of the error and contact IT support with the time and what you were doing.

---

**You’re ready to run the business using the PANN POS Back Office!** Keep this guide handy for daily tasks and training new team members.

