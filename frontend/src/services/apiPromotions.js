// services/apiPromotions.js
import { api } from './api.js';

class PromotionApiService {
  handleResponse(response) {
    if (!response || !response.data) {
      return { success: false, message: "No response from server" };
    }
    return response.data;
  }

  handleError(error) {
    console.error("❌ API Error:", error);
    if (error.response) {
      const { data, status } = error.response;
      let message = data.message || data.detail || `Request failed with status ${status}`;
      let errors = [];
      if (data.errors && Array.isArray(data.errors)) {
        errors = data.errors;
        message += '\n' + data.errors.join('\n');
      }
      return { success: false, message, errors, status };
    }
    return { success: false, message: error.message || "An unknown error occurred", errors: [] };
  }

  // -------------------------------
  // Helper to normalise any date-like value to ISO 8601
  // -------------------------------
  _normalizeDate(value) {
    if (!value) return value;
    if (value instanceof Date) return value.toISOString();
    const date = new Date(value);
    if (!isNaN(date.getTime())) return date.toISOString();
    return value; // fallback (should never happen with proper input)
  }

  // -------------------------------
  // Transformation helpers
  // -------------------------------
  transformToBackend(frontendData) {
    let targetType = 'all';
    let targetIds = [];

    if (frontendData.affected_category) {
      if (frontendData.affected_category === 'all') {
        targetType = 'all';
        targetIds = [];
      } else {
        targetType = 'categories';
        targetIds = [frontendData.affected_category];
      }
    }

    // Build discount_value as a string
    let discountValue;
    if (frontendData.discount_type === 'percentage') {
      discountValue = `${parseFloat(frontendData.discount_value)}%`;
    } else {
      discountValue = parseFloat(frontendData.discount_value).toString();
    }

    const backendData = {
      name: frontendData.promotion_name,
      type: frontendData.discount_type,
      discount_value: discountValue,
      promotion_type: frontendData.discount_type,
      target_type: targetType,
      target_ids: targetIds,
      start_date: this._normalizeDate(frontendData.start_date),        // ✅ normalised
      end_date: this._normalizeDate(frontendData.end_date),            // ✅ normalised
      description: frontendData.description || '',
      usage_limit: frontendData.usage_limit ? parseInt(frontendData.usage_limit) : null,
      status: frontendData.status === 'scheduled' ? 'draft' : frontendData.status,
      recurrence_rule: frontendData.recurrence_rule || null,
      min_purchase_amount: frontendData.min_purchase_amount !== undefined ? parseFloat(frontendData.min_purchase_amount) : 100,
      per_customer_limit: frontendData.per_customer_limit ? parseInt(frontendData.per_customer_limit) : null,
    };

    return backendData;
  }

  transformUpdateToBackend(frontendData = {}) {
    const backendData = {};

    if (Object.prototype.hasOwnProperty.call(frontendData, 'promotion_name')) {
      backendData.name = frontendData.promotion_name;
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'discount_type')) {
      backendData.type = frontendData.discount_type;
      backendData.promotion_type = frontendData.discount_type;
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'discount_value')) {
      const discountType = frontendData.discount_type || 'fixed_amount';
      const value = parseFloat(frontendData.discount_value);
      if (!isNaN(value)) {
        backendData.discount_value = discountType === 'percentage' ? `${value}%` : value.toString();
      }
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'affected_category')) {
      if (frontendData.affected_category === 'all') {
        backendData.target_type = 'all';
        backendData.target_ids = [];
      } else {
        backendData.target_type = 'categories';
        backendData.target_ids = [frontendData.affected_category];
      }
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'start_date')) {
      backendData.start_date = this._normalizeDate(frontendData.start_date);   // ✅
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'end_date')) {
      backendData.end_date = this._normalizeDate(frontendData.end_date);       // ✅
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'description')) {
      backendData.description = frontendData.description || '';
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'usage_limit')) {
      backendData.usage_limit = frontendData.usage_limit ? parseInt(frontendData.usage_limit) : null;
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'status')) {
      backendData.status = frontendData.status === 'scheduled' ? 'draft' : frontendData.status;
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'recurrence_rule')) {
      backendData.recurrence_rule = frontendData.recurrence_rule;
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'min_purchase_amount')) {
      backendData.min_purchase_amount = frontendData.min_purchase_amount === '' ? 0 : parseFloat(frontendData.min_purchase_amount);
    }
    if (Object.prototype.hasOwnProperty.call(frontendData, 'per_customer_limit')) {
      backendData.per_customer_limit = frontendData.per_customer_limit ? parseInt(frontendData.per_customer_limit) : null;
    }

    return backendData;
  }

  transformToFrontend(backendData) {
    let affectedCategory = 'all';
    if (backendData.target_type === 'categories' && backendData.target_ids?.length > 0) {
      affectedCategory = backendData.target_ids[0];
    }

    return {
      promotion_id: backendData.promotion_id || backendData._id,
      promotion_name: backendData.name,
      discount_type: backendData.type,
      discount_value: backendData.discount_value,
      start_date: backendData.start_date,
      end_date: backendData.end_date,
      status: backendData.status,
      is_deleted: backendData.isDeleted || false,
      last_updated: backendData.updated_at || backendData.last_updated,
      target_type: backendData.target_type,
      target_ids: backendData.target_ids || [],
      usage_limit: backendData.usage_limit,
      current_usage: backendData.current_usage || 0,
      description: backendData.description || '',
      affected_category: affectedCategory,
      recurrence_rule: backendData.recurrence_rule || null,
      min_purchase_amount: backendData.min_purchase_amount != null ? backendData.min_purchase_amount : 100,
      per_customer_limit: backendData.per_customer_limit || null,
    };
  }

  // -------------------------------
  // API Methods
  // -------------------------------
  async getAllPromotions(params = {}) {
    try {
      const backendParams = { ...params };
      if (params.discount_type && params.discount_type !== 'all') {
        backendParams.type = params.discount_type;
        delete backendParams.discount_type;
      }
      if (backendParams.status && backendParams.status === 'scheduled') {
        backendParams.status = 'draft';
      }

      const response = await api.get('/promotions/', { params: backendParams });
      const data = this.handleResponse(response);

      if (data.promotions && Array.isArray(data.promotions)) {
        const transformed = data.promotions.map(p => {
          try { return this.transformToFrontend(p); } catch { return p; }
        });
        return {
          success: data.success || true,
          promotions: transformed,
          pagination: data.pagination || {
            current_page: 1,
            total_pages: 1,
            total_items: data.promotions.length,
            items_per_page: params.limit || 20,
          },
        };
      }

      return {
        success: data.success || true,
        promotions: [],
        pagination: { current_page: 1, total_pages: 1, total_items: 0, items_per_page: params.limit || 20 },
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getPromotionById(promotionId) {
    try {
      const response = await api.get(`/promotions/${promotionId}/`);
      const data = this.handleResponse(response);
      if (data.promotion) {
        return { success: true, promotion: this.transformToFrontend(data.promotion) };
      }
      return data;
    } catch (error) {
      return this.handleError(error);
    }
  }

  async createPromotion(promotionData) {
    try {
      const backendData = this.transformToBackend(promotionData);
      const response = await api.post('/promotions/', backendData);
      const data = this.handleResponse(response);
      if (data.promotion) {
        return { success: true, promotion: this.transformToFrontend(data.promotion) };
      }
      return { success: true, promotion: data };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async updatePromotion(promotionId, promotionData) {
    try {
      const backendData = this.transformUpdateToBackend(promotionData);
      const response = await api.put(`/promotions/${promotionId}/`, backendData);
      const data = this.handleResponse(response);
      if (data.promotion) {
        return { success: true, promotion: this.transformToFrontend(data.promotion) };
      }
      return data;
    } catch (error) {
      return this.handleError(error);
    }
  }

  async deletePromotion(promotionId) {
    try {
      const response = await api.delete(`/promotions/${promotionId}/`);
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async deleteMultiplePromotions(promotionIds) {
    try {
      const deletePromises = promotionIds.map(id => this.deletePromotion(id));
      const results = await Promise.allSettled(deletePromises);
      return {
        success: true,
        results: results.map((result, index) => ({
          promotion_id: promotionIds[index],
          success: result.status === 'fulfilled',
          error: result.status === 'rejected' ? result.reason.message : null,
        })),
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async searchPromotions(searchQuery, filters = {}) {
    try {
      const params = { search_query: searchQuery, ...filters };
      if (filters.discount_type && filters.discount_type !== 'all') {
        params.type = filters.discount_type;
        delete params.discount_type;
      }
      const response = await api.get('/promotions/search/', { params });
      const data = this.handleResponse(response);
      return {
        success: data.success,
        promotions: (data.promotions || []).map(p => this.transformToFrontend(p)),
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async getActivePromotions() {
    try {
      const response = await api.get('/promotions/active/');
      const data = this.handleResponse(response);
      return {
        success: data.success,
        promotions: (data.promotions || []).map(p => this.transformToFrontend(p)),
      };
    } catch (error) {
      return this.handleError(error);
    }
  }

  async activatePromotion(promotionId) {
    try {
      const response = await api.post(`/promotions/${promotionId}/activate/`);
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async deactivatePromotion(promotionId) {
    try {
      const response = await api.post(`/promotions/${promotionId}/deactivate/`);
      return this.handleResponse(response);
    } catch (error) {
      return this.handleError(error);
    }
  }

  async exportPromotions(filters = {}, format = 'csv') {
    try {
      const data = await this.getAllPromotions(filters);
      const exportData = {
        promotions: data.promotions,
        exported_at: new Date().toISOString(),
        format: format,
      };
      return JSON.stringify(exportData, null, 2);
    } catch (error) {
      return this.handleError(error);
    }
  }
}

const promotionApiService = new PromotionApiService();
export default promotionApiService;