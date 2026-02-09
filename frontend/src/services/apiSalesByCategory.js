import { api } from '../services/api'; // your existing Axios instance

class CategoryDisplayService {
  /**
   * Fetch all category sales data with enhanced metrics
   * (used for table + chart in SalesByCategory.vue)
   * 
   * @param {string} start_date - YYYY-MM-DD
   * @param {string} end_date - YYYY-MM-DD
   * @param {boolean} include_voided - include voided transactions (optional)
   * @param {boolean} include_trends - include trend analysis (optional)
   * @returns {Promise<Object[]>}
   */
  async getSalesByCategory(start_date, end_date, include_voided = false, include_trends = false) {
    try {
      const response = await api.get('/sales/category/', {
        params: {
          start_date,
          end_date,
          include_voided,
          include_trends
        }
      });
      return response.data || response;
    } catch (error) {
      console.error('❌ Error fetching category sales:', error);
      throw error;
    }
  }

  /**
   * Fetch top-selling categories with enhanced metrics
   * (used for top 5 list + chart)
   * 
   * @param {string} start_date - YYYY-MM-DD
   * @param {string} end_date - YYYY-MM-DD
   * @param {number} limit - number of categories to fetch
   * @returns {Promise<Object[]>}
   */
  async getTopCategories(start_date, end_date, limit = 5) {
    try {
      const response = await api.get('/sales/category/top/', {
        params: {
          start_date,
          end_date,
          limit
        }
      });
      return response.data || response;
    } catch (error) {
      console.error('❌ Error fetching top categories:', error);
      throw error;
    }
  }

  /**
   * Fetch detailed performance data for a specific category
   * 
   * @param {string} category_id - Category ID
   * @param {string} start_date - YYYY-MM-DD
   * @param {string} end_date - YYYY-MM-DD
   * @returns {Promise<Object>}
   */
  async getCategoryPerformance(category_id, start_date, end_date) {
    try {
      const response = await api.get(`/sales/category/${category_id}/`, {
        params: {
          start_date,
          end_date
        }
      });
      return response.data || response;
    } catch (error) {
      console.error('❌ Error fetching category performance:', error);
      throw error;
    }
  }

  /**
   * (Optional) Export category sales report
   */
  async exportCategorySales(start_date, end_date) {
    try {
      const response = await api.get('/sales/category/export/', {
        params: { start_date, end_date },
        responseType: 'blob'
      });
      return response;
    } catch (error) {
      console.error('❌ Error exporting category sales:', error);
      throw error;
    }
  }
}

// Export singleton instance
const categoryDisplayService = new CategoryDisplayService();
export default categoryDisplayService;
export { CategoryDisplayService };