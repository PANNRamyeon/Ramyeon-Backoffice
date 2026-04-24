import { api } from './api.js';

class CategoryApiService {
  handleError(error) {
    const message = error.response?.data?.error ||
                   error.response?.data?.message ||
                   error.message ||
                   'An unexpected error occurred';
    throw new Error(message);
  }

  // ================ CORE CATEGORY METHODS ================

  async CategoryData(params = {}) {
    try {
      const response = await api.get('/categories/', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching all category data:', error);
      this.handleError(error);
    }
  }

  async getAllCategories(params = {}) {
    try {
      const response = await api.get('/categories/', { params });
      if (response.data?.categories) return response.data.categories;
      if (Array.isArray(response.data)) return response.data;
      return [];
    } catch (error) {
      console.error('Error fetching categories:', error);
      return [];
    }
  }

  async getActiveCategories() {
    try {
      const response = await api.get('/categories/', { params: { active_only: true } });
      return response.data?.categories || [];
    } catch (error) {
      console.error('Error fetching active categories:', error);
      return [];
    }
  }

  async getCategoryById(categoryId, includeDeleted = false) {
    try {
      const params = includeDeleted ? { include_deleted: true } : {};
      const response = await api.get(`/categories/${categoryId}/`, { params });
      return response.data;
    } catch (error) {
      console.error(`Error fetching category ${categoryId}:`, error);
      return null;
    }
  }

  async getSubcategories(categoryId) {
    try {
      const response = await api.get(`/categories/${categoryId}/subcategories/`);
      return response.data?.subcategories || [];
    } catch (error) {
      console.error(`Error fetching subcategories for ${categoryId}:`, error);
      this.handleError(error);
    }
  }

  // ================ CREATE / UPDATE ================

  async AddCategoryData(params = {}) {
    try {
      const categoryData = {
        category_name: params.category_name,
        description: params.description || '',
        status: params.status || 'active',
        sub_categories: params.sub_categories || []
      };

      const imageFields = ['image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at'];
      if (params.image_url) {
        imageFields.forEach(f => { if (params[f] != null) categoryData[f] = params[f]; });
      }

      const response = await api.post('/categories/', categoryData);
      return response.data;
    } catch (error) {
      console.error(`Error creating category ${params.category_name}:`, error);
      throw error;
    }
  }

  async UpdateCategoryData(params = {}) {
    try {
      const updateData = {
        category_name: params.category_name,
        description: params.description || '',
        status: params.status || 'active',
        sub_categories: params.sub_categories || []
      };

      if (params.image_url) {
        const imageFields = ['image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at'];
        imageFields.forEach(f => { if (params[f] != null) updateData[f] = params[f]; });
      } else if (params.image_url === null || params.image_url === '') {
        ['image_url', 'image_filename', 'image_size', 'image_type', 'image_uploaded_at']
          .forEach(f => { updateData[f] = null; });
      }

      // Strip undefined values
      Object.keys(updateData).forEach(k => {
        if (updateData[k] === undefined) delete updateData[k];
      });

      const response = await api.put(`/categories/${params.id}/`, updateData);
      return response.data;
    } catch (error) {
      console.error(`Error updating category ${params.id}:`, error);
      throw error;
    }
  }

  // ================ SUBCATEGORY MANAGEMENT ================

  async AddSubCategoryData(categoryId, subcategoryData) {
    try {
      const response = await api.post(`/categories/${categoryId}/subcategories/`, {
        subcategory: subcategoryData
      });
      return response.data;
    } catch (error) {
      console.error('Error adding subcategory:', error);
      throw error;
    }
  }

  async RemoveSubCategoryData(categoryId, subcategoryName) {
    try {
      const response = await api.delete(`/categories/${categoryId}/subcategories/`, {
        data: { subcategory_name: subcategoryName }
      });
      return response.data;
    } catch (error) {
      console.error('Error removing subcategory:', error);
      this.handleError(error);
    }
  }

  // ================ PRODUCTS IN CATEGORIES ================

  async FindProdcategory(params = {}) {
    try {
      if (!params.id) throw new Error('Category ID is required');

      let response;
      if (params.subcategory_name) {
        response = await api.get(
          `/categories/${params.id}/subcategories/${encodeURIComponent(params.subcategory_name)}/products/`
        );
      } else {
        response = await api.get(`/products/category/${params.id}/`);
      }

      if (Array.isArray(response.data)) return response.data;
      if (Array.isArray(response.data?.products)) return response.data.products;
      if (Array.isArray(response.data?.data)) return response.data.data;
      return [];
    } catch (error) {
      console.error(`Error fetching products for category ${params.id}:`, error);
      this.handleError(error);
    }
  }

  // ================ PRODUCT-CATEGORY RELATIONSHIP ================

  async MoveProductToCategory(params = {}) {
    try {
      if (!params.product_id) throw new Error('Product ID is required');
      if (!params.new_category_id) throw new Error('New category ID is required');

      const response = await api.put(`/categories/${params.new_category_id}/products/`, {
        product_id: params.product_id,
        new_category_id: params.new_category_id,
        new_subcategory_name: params.new_subcategory_name || null
      });
      return response.data;
    } catch (error) {
      console.error('Error moving product to category:', error);
      this.handleError(error);
    }
  }

  async BulkMoveProductsToCategory(params = {}) {
    try {
      if (!params.product_ids || !Array.isArray(params.product_ids)) throw new Error('Product IDs array is required');
      if (!params.new_category_id) throw new Error('New category ID is required');

      const response = await api.post(`/categories/${params.new_category_id}/products/`, {
        product_ids: params.product_ids,
        new_category_id: params.new_category_id,
        new_subcategory_name: params.new_subcategory_name || null
      });
      return response.data;
    } catch (error) {
      console.error('Error in bulk move to category:', error);
      this.handleError(error);
    }
  }

  // ================ DELETE METHODS ================

  async SoftDeleteCategory(categoryId) {
    try {
      const response = await api.delete(`/categories/${categoryId}/soft-delete/`);
      return response.data;
    } catch (error) {
      console.error('Error soft deleting category:', error);
      this.handleError(error);
    }
  }

  async HardDeleteCategory(categoryId) {
    try {
      const response = await api.delete(`/categories/${categoryId}/hard-delete/`);
      return response.data;
    } catch (error) {
      console.error('Error hard deleting category:', error);
      this.handleError(error);
    }
  }

  async RestoreCategory(categoryId) {
    try {
      const response = await api.post(`/categories/${categoryId}/restore/`);
      return response.data;
    } catch (error) {
      console.error('Error restoring category:', error);
      this.handleError(error);
    }
  }

  async GetCategoryDeleteInfo(categoryId) {
    try {
      const response = await api.get(`/categories/${categoryId}/delete-info/`);
      return response.data;
    } catch (error) {
      console.error('Error fetching category delete info:', error);
      this.handleError(error);
    }
  }

  // ================ UNCATEGORIZED ================

  async GetUncategorizedCategory() {
    try {
      const response = await api.get('/categories/uncategorized/');
      return response.data;
    } catch (error) {
      console.error('Error getting Uncategorized category:', error);
      this.handleError(error);
    }
  }

  async MoveProductToUncategorized(params = {}) {
    try {
      if (!params.product_id) throw new Error('Product ID is required');

      const uncategorized = await this.GetUncategorizedCategory();
      const uncategorizedId = uncategorized?.uncategorized_category?.category_id;
      if (!uncategorizedId) throw new Error('Could not resolve Uncategorized category ID');

      return await this.MoveProductToCategory({
        product_id: params.product_id,
        new_category_id: uncategorizedId,
        new_subcategory_name: 'None'
      });
    } catch (error) {
      console.error('Error moving product to Uncategorized:', error);
      this.handleError(error);
    }
  }

  async BulkMoveProductsToUncategorized(params = {}) {
    try {
      if (!params.product_ids || !Array.isArray(params.product_ids)) throw new Error('Product IDs array is required');

      const uncategorized = await this.GetUncategorizedCategory();
      const uncategorizedId = uncategorized?.uncategorized_category?.category_id;
      if (!uncategorizedId) throw new Error('Could not resolve Uncategorized category ID');

      return await this.BulkMoveProductsToCategory({
        product_ids: params.product_ids,
        new_category_id: uncategorizedId,
        new_subcategory_name: 'None'
      });
    } catch (error) {
      console.error('Error in bulk move to Uncategorized:', error);
      this.handleError(error);
    }
  }

  // ================ STATISTICS ================

  // No dedicated stats endpoint exists — callers should use the categoryStats
  // computed property in useCategories.js which derives stats from the local list.
  async GetCategoryStats() {
    try {
      const response = await api.get('/categories/');
      const categories = response.data?.categories || [];
      return {
        total: categories.length,
        active: categories.filter(c => c.status === 'active').length,
        inactive: categories.filter(c => c.status === 'inactive').length,
        deleted: categories.filter(c => c.isDeleted).length
      };
    } catch (error) {
      console.error('Error getting category stats:', error);
      this.handleError(error);
    }
  }

  // ================ EXPORT ================

  async ExportCategoryData(params = {}) {
    try {
      const categories = params.categories || [];
      if (categories.length === 0) throw new Error('No categories to export');

      const formatSubcategories = subs =>
        subs?.length ? subs.map(s => s.name).join('; ') : 'None';

      const getTotalProducts = subs =>
        subs ? subs.reduce((t, s) => t + (s.product_count || 0), 0) : 0;

      const formatDate = d =>
        d ? new Date(d).toLocaleDateString('en-US') : 'N/A';

      const headers = [
        'Category ID', 'Category Name', 'Description', 'Status',
        'Sub-Categories', 'Total Products', 'Date Created', 'Last Updated'
      ];

      const csvContent = [
        headers.join(','),
        ...categories.map(c => [
          c.category_id,
          `"${c.category_name}"`,
          `"${c.description || ''}"`,
          c.status || 'active',
          `"${formatSubcategories(c.sub_categories)}"`,
          getTotalProducts(c.sub_categories),
          formatDate(c.date_created),
          formatDate(c.last_updated)
        ].join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `categories_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      return { success: true, message: 'Export completed successfully' };
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  }

  // ================ UTILITY ================

  formatDeletionDate(dateString) {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
      });
    } catch {
      return 'Invalid Date';
    }
  }
}

const categoryApiService = new CategoryApiService();
export default categoryApiService;
export { CategoryApiService };
