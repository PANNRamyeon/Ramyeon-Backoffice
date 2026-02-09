// src/api/salesDisplay/SalesDisplayService.js
import { api } from '../services/api';

class SalesDisplayService {
  // 1. POS Item Summary
  async getPOSItemSummary(startDate, endDate) {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await api.get('sales-display/pos-item-summary/', { params });
    return response.data;
  }

  // 2. Online Item Summary
  async getOnlineItemSummary(startDate, endDate) {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await api.get('sales-display/online-item-summary/', { params });
    return response.data;
  }

  // 3. POS Sales List
  async getAllPOSSales() {
    const response = await api.get('sales-display/pos-sales/');
    return response.data;
  }

  // 4. Online Transactions
  async getAllOnlineTransactions() {
    const response = await api.get('sales-display/online-transactions/');
    return response.data;
  }

  // 5. Combined Display by Item
  async getSalesByItem(startDate, endDate, includeVoided = false) {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (includeVoided) params.include_voided = includeVoided;

    const response = await api.get('sales-display/by-item/', { params });
    return response.data;
  }
  
  async getSalesSummary(startDate, endDate) {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await api.get('sales-display/summary/', { params });
    return response.data;
  }
}

// Export a singleton instance and the class
const salesDisplayService = new SalesDisplayService();
export default salesDisplayService;
export { SalesDisplayService };
