import { api } from './api.js';

class CategoryApiService {
  // Helper method to handle errors
  handleError(error) {
    const message = error.response?.data?.error || 
                   error.response?.data?.message || 
                   error.message || 
                   'An unexpected error occurred';
    throw new Error(message);
  }

  // ================ CORE CATEGORY METHODS ================
  
  /**
   * Get all categories with sales data
   * @param {Object} params - Query parameters (include_deleted, etc.)
   * @returns {Promise<Object>} Categories list with sales data
   */
  async CategoryData(params = {}) {
    try {
        const response = await api.get('/category/', { params });
        return response.data;
    } catch (error) {
        console.error("Error fetching all category data:", error);
        throw error;
    }
  }

  async getActiveCategories() {
    try {
      const allCategories = await this.getAllCategories();
      const activeCategories = allCategories.filter(cat => cat.status === 'active' && !cat.isDeleted);
      return activeCategories;
    } catch (error) {
      console.error("❌ getActiveCategories: Error:", error);
      return [];
    }
  }

  async getCategoryById(categoryId, includeDeleted = false) {
    try {
      const params = includeDeleted ? { include_deleted: true } : {};
      const response = await api.get(`/category/${categoryId}/`, { params });
      return response.data;
    } catch (error) {
      console.error(`❌ getCategoryById: Error fetching category ${categoryId}:`, error);
      return null;
    }
  }

  async getSubcategories(categoryId) {
    try {
      const response = await api.get(`/category/${categoryId}/subcategories/`);
      return response.data.subcategories || [];
    } catch (error) {
      console.error(`Error fetching subcategories for ${categoryId}:`, error);
      this.handleError(error);
    }
  }

  async getAllCategories(params = {}) {
    try {
      const response = await api.get('/category/', { params });

      // Handle different response formats
      if (response.data && Array.isArray(response.data)) {
        return response.data;
      } else if (response.data && response.data.categories) {
        return response.data.categories;
      } else {
        return [];
      }
    } catch (error) {
      console.error("❌ getAllCategories: Error fetching categories:", error);
      return [];
    }
  }

  /**
   * Add new category
   * @param {Object} params - Category data
   * @returns {Promise<Object>} Created category
   */
  async AddCategoryData(params = {}) {
      try {
          const categoryData = {
              category_name: params.category_name,
              description: params.description || '',
              status: params.status || 'active',
              sub_categories: params.sub_categories || []
          };

          // ADD IMAGE FIELDS if they exist
          if (params.image_url) {
              categoryData.image_url = params.image_url;
              categoryData.image_filename = params.image_filename;
              categoryData.image_size = params.image_size;
              categoryData.image_type = params.image_type;
              categoryData.image_uploaded_at = params.image_uploaded_at;
          }

          const response = await api.post('/category/', categoryData);

          return response.data;

      } catch (error) {
          console.error(`Error creating category ${params.category_name}:`, error);
          throw error;
      }
  }

  /**
   * Update an existing category
   * @param {Object} params - Parameters including id and update data
   * @returns {Promise<Object>} Updated category data
   */
    async UpdateCategoryData(params = {}) {
      try {
          const updateData = {
              category_name: params.category_name,
              description: params.description || '',
              status: params.status || 'active',
              sub_categories: params.sub_categories || []
          };

          // ADD IMAGE FIELDS if they exist
          if (params.image_url) {
              updateData.image_url = params.image_url;
              updateData.image_filename = params.image_filename;
              updateData.image_size = params.image_size;
              updateData.image_type = params.image_type;
              updateData.image_uploaded_at = params.image_uploaded_at;
          }
          // Handle image removal (when user removes image)
          else if (params.image_url === null || params.image_url === '') {
              updateData.image_url = null;
              updateData.image_filename = null;
              updateData.image_size = null;
              updateData.image_type = null;
              updateData.image_uploaded_at = null;
          }

          // Remove undefined values
          Object.keys(updateData).forEach(key => {
              if (updateData[key] === undefined) {
                  delete updateData[key];
              }
          });

          const response = await api.put(`/category/${params.id}/`, updateData);

          return response.data;

      } catch (error) {
          console.error(`Error updating category ${params.id}:`, error);
          throw error;
      }
  }

  /**
   * Find specific category by ID
   * @param {Object} params - Parameters including id and include_deleted
   * @returns {Promise<Object>} Category data
   */
  async FindCategoryData(params = {}) {
    try {
      const queryParams = {};
      if (params.include_deleted !== undefined) {
        queryParams.include_deleted = params.include_deleted;
      }

      const response = await api.get(`/category/${params.id}/`, { params: queryParams });
      return response.data;

    } catch (error) {
      console.error(`Error fetching specific category ${params.id} data:`, error);
      throw error;
    }
  }

  /**
   * Get products by category using the refactored endpoint
   * @param {Object} params - Parameters including category id and optional subcategory
   * @returns {Promise<Array>} List of products
   */
  async FindProdcategory(params = {}) {
    try {
      if (!params.id) {
        throw new Error('Category ID is required');
      }

      let response;

      if (params.subcategory_name) {
        // Get products for specific subcategory
        response = await api.get(`/category/${params.id}/subcategories/${encodeURIComponent(params.subcategory_name)}/products/`);
      } else {
        // Get all products for category using products API
        response = await api.get(`/products/reports/by-category/${params.id}/`);
      }

      // ✅ FIXED: Handle different response formats
      if (response.data) {
        if (Array.isArray(response.data)) {
          return response.data;
        } else if (response.data.products && Array.isArray(response.data.products)) {
          return response.data.products;
        } else if (response.data.data && Array.isArray(response.data.data)) {
          return response.data.data;
        }
      }

      return [];

    } catch (error) {
      console.error(`❌ FindProdcategory: Error fetching products for category ${params.id}:`, error);
      this.handleError(error);
    }
  }

  // ================ SUBCATEGORY MANAGEMENT ================

  /**
   * Add a new subcategory to a category
   * @param {string} categoryId - Category ID
   * @param {Object} subcategoryData - Subcategory data
   * @returns {Promise<Object>} API response
   */
  async AddSubCategoryData(categoryId, subcategoryData) {
    try {
      const response = await api.post(`/category/${categoryId}/subcategories/`, {
        subcategory: subcategoryData
      });

      return response.data;

    } catch (error) {
      console.error('❌ Error adding subcategory:', error);
      throw error;
    }
  }

  /**
   * Remove a subcategory from a category
   * @param {string} categoryId - Category ID
   * @param {string} subcategoryName - Subcategory name to remove
   * @returns {Promise<Object>} API response
   */
  async RemoveSubCategoryData(categoryId, subcategoryName) {
    try {
      const response = await api.delete(`/category/${categoryId}/subcategories/`, {
        data: { subcategory_name: subcategoryName }
      });

      return response.data;

    } catch (error) {
      console.error('❌ Error removing subcategory:', error);
      throw error;
    }
  }

  // ================ PRODUCT-CATEGORY RELATIONSHIP MANAGEMENT ================

  /**
   * Move a product to a different category/subcategory
   * @param {Object} params - Move parameters
   * @param {string} params.product_id - Product ID to move
   * @param {string} params.new_category_id - Target category ID
   * @param {string} params.new_subcategory_name - Target subcategory name (optional)
   * @returns {Promise<Object>} Move result
   */
  async MoveProductToCategory(params = {}) {
    try {
      if (!params.product_id) {
        throw new Error('Product ID is required');
      }

      if (!params.new_category_id) {
        throw new Error('New category ID is required');
      }

      const payload = {
        product_id: params.product_id,
        new_category_id: params.new_category_id,
        new_subcategory_name: params.new_subcategory_name || null
      };

      const response = await api.put('/category/product-management/', payload);

      return response.data;

    } catch (error) {
      console.error('❌ Error moving product to category:', error);
      this.handleError(error);
    }
  }

  /**
   * Bulk move multiple products to a category/subcategory
   * @param {Object} params - Bulk move parameters
   * @param {Array} params.product_ids - Array of product IDs to move
   * @param {string} params.new_category_id - Target category ID
   * @param {string} params.new_subcategory_name - Target subcategory name (optional)
   * @returns {Promise<Object>} Bulk move result
   */
  async BulkMoveProductsToCategory(params = {}) {
    try {
      if (!params.product_ids || !Array.isArray(params.product_ids)) {
        throw new Error('Product IDs array is required');
      }

      if (!params.new_category_id) {
        throw new Error('New category ID is required');
      }

      const payload = {
        product_ids: params.product_ids,
        new_category_id: params.new_category_id,
        new_subcategory_name: params.new_subcategory_name || null
      };

      const response = await api.post('/category/product-management/', payload);

      return response.data;

    } catch (error) {
      console.error('❌ Error in bulk move to category:', error);
      this.handleError(error);
    }
  }

  /**
   * Legacy method - now redirects to MoveProductToCategory
   * @deprecated Use MoveProductToCategory instead
   */
  async SubCatChangeTab(params = {}) {
    console.warn('⚠️ SubCatChangeTab is deprecated, use MoveProductToCategory instead');
    
    // Convert old params to new format
    const newParams = {
      product_id: params.product_id,
      new_category_id: params.category_id,
      new_subcategory_name: params.new_subcategory
    };
    
    return this.MoveProductToCategory(newParams);
  }

  /**
   * Legacy method - now redirects to MoveProductToCategory
   * @deprecated Use MoveProductToCategory instead
   */
  async CatChangeTab(params = {}) {
    console.warn('⚠️ CatChangeTab is deprecated, use MoveProductToCategory instead');
    
    // Convert old params to new format
    const newParams = {
      product_id: params.product_id,
      new_category_id: params.new_category || params.category_id,
      new_subcategory_name: 'None' // Default subcategory
    };
    
    return this.MoveProductToCategory(newParams);
  }

  // ================ DELETE METHODS ================

  /**
   * Soft delete a category
   * @param {string} categoryId - Category ID to soft delete
   * @returns {Promise<Object>} Delete result
   */
  async SoftDeleteCategory(categoryId) {
    try {
      const response = await api.delete(`/category/${categoryId}/soft-delete/`);

      return response.data;

    } catch (error) {
      console.error('❌ Error soft deleting category:', error);
      this.handleError(error);
    }
  }

  /**
   * Hard delete a category (Admin only)
   * @param {string} categoryId - Category ID to hard delete
   * @returns {Promise<Object>} Delete result
   */
  async HardDeleteCategory(categoryId) {
    try {
      const response = await api.delete(`/category/${categoryId}/hard-delete/`);

      return response.data;

    } catch (error) {
      console.error('❌ Error hard deleting category:', error);
      this.handleError(error);
    }
  }

  /**
   * Restore a soft-deleted category
   * @param {string} categoryId - Category ID to restore
   * @returns {Promise<Object>} Restore result
   */
  async RestoreCategory(categoryId) {
    try {
      const response = await api.post(`/category/${categoryId}/restore/`);

      return response.data;

    } catch (error) {
      console.error('❌ Error restoring category:', error);
      this.handleError(error);
    }
  }

  /**
   * Get category deletion impact information
   * @param {string} categoryId - Category ID to check
   * @returns {Promise<Object>} Deletion impact info
   */
  async GetCategoryDeleteInfo(categoryId) {
    try {
      const response = await api.get(`/category/${categoryId}/delete-info/`);

      return response.data;

    } catch (error) {
      console.error('❌ Error fetching category delete info:', error);
      this.handleError(error);
    }
  }

  // ================ UNCATEGORIZED CATEGORY MANAGEMENT ================

  /**
   * Get or ensure the Uncategorized category exists
   * @returns {Promise<Object>} Uncategorized category data
   */
  async GetUncategorizedCategory() {
    try {
      const response = await api.get('/category/uncategorized/');

      return response.data;

    } catch (error) {
      console.error('❌ Error getting Uncategorized category:', error);
      this.handleError(error);
    }
  }

  /**
   * Move product to Uncategorized category (uses default "None" subcategory)
   * @param {Object} params - Parameters
   * @param {string} params.product_id - Product ID to move
   * @returns {Promise<Object>} Move result
   */
  async MoveProductToUncategorized(params = {}) {
    try {
      if (!params.product_id) {
        throw new Error('Product ID is required');
      }

      // First get the uncategorized category
      const uncategorizedCategory = await this.GetUncategorizedCategory();
      const uncategorizedCategoryId = uncategorizedCategory.uncategorized_category._id;

      // Move to uncategorized using the standard move method
      return await this.MoveProductToCategory({
        product_id: params.product_id,
        new_category_id: uncategorizedCategoryId,
        new_subcategory_name: 'None'
      });

    } catch (error) {
      console.error('❌ Error moving product to Uncategorized:', error);
      this.handleError(error);
    }
  }

  /**
   * Bulk move multiple products to Uncategorized category
   * @param {Object} params - Parameters
   * @param {Array} params.product_ids - Array of product IDs to move
   * @returns {Promise<Object>} Bulk move result
   */
  async BulkMoveProductsToUncategorized(params = {}) {
    try {
      if (!params.product_ids || !Array.isArray(params.product_ids)) {
        throw new Error('Product IDs array is required');
      }

      // First get the uncategorized category
      const uncategorizedCategory = await this.GetUncategorizedCategory();
      const uncategorizedCategoryId = uncategorizedCategory.uncategorized_category._id;

      // Bulk move to uncategorized using the standard bulk move method
      return await this.BulkMoveProductsToCategory({
        product_ids: params.product_ids,
        new_category_id: uncategorizedCategoryId,
        new_subcategory_name: 'None'
      });

    } catch (error) {
      console.error('❌ Error in bulk move to Uncategorized:', error);
      this.handleError(error);
    }
  }

  // ================ CATEGORY STATISTICS ================

  /**
   * Get category statistics
   * @returns {Promise<Object>} Category statistics
   */
  async GetCategoryStats() {
    try {
      const response = await api.get('/category/stats/');

      return response.data;

    } catch (error) {
      console.error('❌ Error getting category stats:', error);
      this.handleError(error);
    }
  }

  // ================ EXPORT METHODS ================

  /**
   * Export categories data
   * @param {Object} params - Export parameters (format, include_sales_data, include_deleted)
   * @returns {Promise<Blob>} Export file blob
   */
  async ExportCategoryData(params = {}) {
    try {
      const categories = params.categories || [];

      if (categories.length === 0) {
        throw new Error('No categories to export')
      }
      
      // Helper functions
      const formatSubcategories = (subcategories) => {
        if (!subcategories || subcategories.length === 0) return 'None'
        return subcategories.map(sub => sub.name).join('; ')
      }

      const getTotalProducts = (subcategories) => {
        if (!subcategories) return 0
        return subcategories.reduce((total, sub) => total + (sub.product_count || 0), 0)
      }

      const formatDate = (dateString) => {
        if (!dateString) return 'N/A'
        return new Date(dateString).toLocaleDateString('en-US')
      }

      // Create CSV content
      const headers = [
        'Category ID',
        'Category Name', 
        'Description',
        'Status',
        'Sub-Categories',
        'Total Products',
        'Date Created',
        'Last Updated'
      ]
      
      const csvContent = [
        headers.join(','),
        ...categories.map(category => [
          category._id || category.category_id,
          `"${category.category_name}"`,
          `"${category.description || ''}"`,
          category.status || 'active',
          `"${formatSubcategories(category.sub_categories)}"`,
          getTotalProducts(category.sub_categories),
          formatDate(category.date_created),
          formatDate(category.last_updated)
        ].join(','))
      ].join('\n')

      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `categories_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)

      return { success: true, message: 'Export completed successfully' }

    } catch (error) {
      console.error('Export failed:', error)
      throw error
    }
  }

  // ================ UTILITY METHODS ================

  /**
   * Format deletion date
   * @param {string} dateString - Date string
   * @returns {string} Formatted date
   */
  formatDeletionDate(dateString) {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return 'Invalid Date';
    }
  }

  // ================ LEGACY COMPATIBILITY ================

  /**
   * Legacy method - kept for backward compatibility
   * @deprecated This method is deprecated and may be removed in future versions
   */
  async UncategorizedData(params = {}) {
    console.warn('⚠️ UncategorizedData is deprecated, use MoveProductToUncategorized instead');
    return await this.MoveProductToUncategorized(params);
  }
}

const categoryApiService = new CategoryApiService();
export default categoryApiService;

export { CategoryApiService };