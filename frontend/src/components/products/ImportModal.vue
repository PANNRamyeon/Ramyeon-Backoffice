<template>
  <div 
    class="modal fade" 
    id="importModal" 
    tabindex="-1" 
    aria-labelledby="importModalLabel" 
    aria-hidden="true"
    @hidden.bs.modal="onModalHidden"
    @shown.bs.modal="onModalShown"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <!-- Modal Header -->
        <div class="modal-header">
          <h5 class="modal-title" id="importModalLabel">
            <Upload :size="20" class="me-2" style="color: var(--primary);" />
            Import Products
          </h5>
          <button 
            type="button" 
            class="btn-close" 
            data-bs-dismiss="modal" 
            aria-label="Close"
          ></button>
        </div>

        <!-- Modal Body -->
        <div class="modal-body">
          <!-- Download Template Section -->
          <div class="mb-4">
            <h6 class="mb-3" style="color: var(--tertiary-dark);">
              Step 1: Download Template
            </h6>
            <div class="alert alert-info border-0" style="background-color: var(--info-light); color: var(--info-dark);">
              <AlertTriangle :size="16" class="me-2" />
              <div>
                <strong>Important Guidelines:</strong>
                <ul class="mb-0 mt-2" style="font-size: 0.875rem;">
                  <li><strong>Required columns:</strong> product_name, selling_price, category_id</li>
                  <li><strong>Optional columns:</strong> subcategory_name, SKU, supplier_id, stock, cost_price, low_stock_threshold, unit, status, barcode, description, </li>
                  <li><strong>Stock is optional</strong> - Leave blank or set to 0 if not adding initial inventory</li>
                  <li><strong>When adding stock (stock > 0):</strong>
                    <ul>
                      <li><code>cost_price</code> is <strong>REQUIRED</strong></li>
                      <li><code>expiry_date</code> is <strong>REQUIRED</strong></li>
                      <li>Initial batch will be created automatically by the system</li>
                    </ul>
                  </li>
                  <li><strong>When stock is 0 or empty:</strong>
                    <ul>
                      <li><code>cost_price</code> is optional</li>
                      <li>No batch will be created (add stock later via restock)</li>
                    </ul>
                  </li>
                </ul>
              </div>
            </div>
            
            <div class="d-flex gap-2 flex-wrap">
              <button 
                type="button" 
                class="btn btn-export btn-sm btn-with-icon-sm"
                @click="downloadTemplate('csv')"
                :disabled="isDownloading || loading"
              >
                <FileSpreadsheet :size="14" />
                {{ isDownloading ? 'Downloading...' : 'Download CSV Template' }}
              </button>
              
              <button 
                type="button" 
                class="btn btn-export btn-sm btn-with-icon-sm"
                @click="downloadTemplate('xlsx')"
                :disabled="isDownloading || loading"
              >
                <FileSpreadsheet :size="14" />
                {{ isDownloading ? 'Downloading...' : 'Download Excel Template' }}
              </button>
            </div>
          </div>

          <!-- File Upload Section -->
          <div class="mb-4">
            <h6 class="mb-3" style="color: var(--tertiary-dark);">
              Step 2: Upload Your File
            </h6>
            
            <!-- File Input -->
            <div class="mb-3">
              <label for="importFile" class="form-label" style="color: var(--tertiary-medium);">
                Select CSV or Excel file
              </label>
              <input 
                type="file" 
                class="form-control" 
                id="importFile"
                ref="fileInput"
                @change="onFileSelected"
                accept=".csv,.xlsx,.xls"
                :disabled="isUploading || loading"
              >
              <div class="form-text" style="color: var(--tertiary-medium);">
                Supported formats: CSV, Excel (.xlsx, .xls) • Max file size: 10MB
              </div>
            </div>

            <!-- Selected File Info -->
            <div v-if="selectedFile" class="alert alert-success border-0" style="background-color: var(--success-light); color: var(--success-dark);">
              <Check :size="16" class="me-2" />
              <strong>Selected:</strong> {{ selectedFile.name }} 
              <small>({{ formatFileSize(selectedFile.size) }})</small>
            </div>

            <!-- File Validation Errors -->
            <div v-if="fileValidationError" class="alert alert-danger border-0" style="background-color: var(--error-light); color: var(--error-dark);">
              <AlertTriangle :size="16" class="me-2" />
              {{ fileValidationError }}
            </div>

            <!-- Stock/Cost Price Validation Warning -->
            <div v-if="selectedFile && !fileValidationError" class="alert alert-warning border-0" style="background-color: var(--warning-light); color: var(--warning-dark);">
              <AlertTriangle :size="16" class="me-2" />
              <div>
                <strong>Before importing, make sure:</strong>
                <ul class="mb-0 mt-2" style="font-size: 0.875rem;">
                  <li>Products with <code>stock > 0</code> must have <code>cost_price</code> and <code>expiry_date</code></li>
                  <li>Products without stock (or stock = 0) don't need cost_price</li>
                  <li>Use "Validate only" first to check for errors without importing</li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Import Options -->
          <div class="mb-4">
            <h6 class="mb-3" style="color: var(--tertiary-dark);">
              Step 3: Import Options
            </h6>
            
            <div class="form-check mb-3">
              <input 
                class="form-check-input" 
                type="checkbox" 
                id="validateOnly"
                v-model="validateOnly"
                :disabled="loading"
              >
              <label class="form-check-label" for="validateOnly" style="color: var(--tertiary-medium);">
                <strong>Validate only</strong> (recommended first step)
              </label>
              <small class="form-text d-block mt-1" style="color: var(--tertiary-medium);">
                Check your file for errors before doing the actual import. This will verify:
                <ul class="mb-0 mt-1" style="font-size: 0.8125rem;">
                  <li>Required fields are present</li>
                  <li>Stock/cost_price validation rules</li>
                  <li>Duplicate SKUs</li>
                  <li>Data format issues</li>
                </ul>
              </small>
            </div>
            
            <div class="form-check mb-3">
              <input 
                class="form-check-input" 
                type="checkbox" 
                id="skipDuplicates"
                v-model="skipDuplicates"
                :disabled="validateOnly || loading"
              >
              <label class="form-check-label" for="skipDuplicates" style="color: var(--tertiary-medium);">
                Skip duplicate products (based on SKU)
              </label>
              <small class="form-text d-block mt-1" style="color: var(--tertiary-medium);">
                Products with existing SKUs will be skipped instead of causing errors
              </small>
            </div>

            <div class="form-check">
              <input 
                class="form-check-input" 
                type="checkbox" 
                id="updateExisting"
                v-model="updateExisting"
                :disabled="validateOnly || skipDuplicates || loading"
              >
              <label class="form-check-label" for="updateExisting" style="color: var(--tertiary-medium);">
                Update existing products
              </label>
              <small class="form-text d-block mt-1" style="color: var(--tertiary-medium);">
                Update products that already exist (based on SKU) instead of creating duplicates
              </small>
            </div>
          </div>

          <!-- Batch Creation Info -->
          <div v-if="!validateOnly && selectedFile" class="mb-4">
            <div class="alert alert-info border-0" style="background-color: var(--info-light); color: var(--info-dark);">
              <Package :size="16" class="me-2" />
              <div>
                <strong>Automatic Batch Creation:</strong>
                <ul class="mb-0 mt-2" style="font-size: 0.875rem;">
                  <li>Products with initial stock will automatically get their first batch created</li>
                  <li>Batch will include: quantity, cost price, and expiry date from your file</li>
                  <li>You can add more batches later when restocking</li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Progress Bar -->
          <div v-if="isUploading || loading" class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <small style="color: var(--tertiary-medium);">{{ uploadStatus }}</small>
              <small v-if="!loading" style="color: var(--tertiary-medium);">{{ uploadProgress }}%</small>
            </div>
            <div class="progress">
              <div 
                class="progress-bar" 
                role="progressbar" 
                :style="{ 
                  width: loading ? '100%' : uploadProgress + '%',
                  backgroundColor: uploadProgress === 100 ? 'var(--success)' : 'var(--primary)'
                }"
                :class="{ 'progress-bar-striped progress-bar-animated': loading }"
                :aria-valuenow="loading ? 100 : uploadProgress" 
                aria-valuemin="0" 
                aria-valuemax="100"
              ></div>
            </div>
          </div>

          <!-- Error Messages -->
          <div v-if="error" class="alert alert-danger border-0" style="background-color: var(--error-light); color: var(--error-dark);">
            <AlertTriangle :size="16" class="me-2" />
            <strong>Error:</strong> {{ error }}
          </div>

          <!-- Results Section -->
          <div v-if="importResults" class="mt-4">
            <h6 class="mb-3" style="color: var(--tertiary-dark);">
              {{ validateOnly ? 'Validation Results' : 'Import Results' }}
            </h6>
            
            <!-- Success Results -->
            <div v-if="importResults.success && importResults.validationErrors.length === 0" class="alert alert-success border-0" style="background-color: var(--success-light); color: var(--success-dark);">
              <CheckCircle :size="16" class="me-2" />
              <div>
                <strong>{{ validateOnly ? 'Validation completed successfully!' : 'Import completed successfully!' }}</strong>
                <ul class="mb-0 mt-2">
                  <li>Total rows processed: {{ importResults.totalProcessed || 0 }}</li>
                  <li v-if="validateOnly">
                    ✅ {{ importResults.totalProcessed }} valid products found
                  </li>
                  <li v-if="!validateOnly">
                    Successfully imported: {{ importResults.totalSuccessful || 0 }}
                    <span v-if="importResults.batchesCreated > 0" class="ms-2">
                      <Package :size="14" style="display: inline;" />
                      {{ importResults.batchesCreated }} batches created
                    </span>
                  </li>
                  <li v-if="!validateOnly && importResults.totalSkipped > 0">
                    Skipped (duplicates): {{ importResults.totalSkipped }}
                  </li>
                </ul>
              </div>
            </div>

            <!-- Partial Success with Warnings -->
            <div v-if="importResults.hasWarnings" class="alert alert-warning border-0 mt-2" style="background-color: var(--warning-light); color: var(--warning-dark);">
              <AlertTriangle :size="16" class="me-2" />
              <div>
                <strong>Import completed with warnings:</strong>
                <ul class="mb-0 mt-2" style="font-size: 0.875rem;">
                  <li v-if="importResults.productsWithoutBatches > 0">
                    {{ importResults.productsWithoutBatches }} products created without initial stock
                  </li>
                  <li v-if="importResults.batchCreationErrors > 0">
                    {{ importResults.batchCreationErrors }} products created but batch creation failed
                    <small class="d-block text-muted">Products were created successfully, but you'll need to add stock manually</small>
                  </li>
                </ul>
              </div>
            </div>

            <!-- Error Results -->
            <div v-if="!importResults.success" class="alert alert-danger border-0" style="background-color: var(--error-light); color: var(--error-dark);">
              <AlertTriangle :size="16" class="me-2" />
              <strong>{{ validateOnly ? 'Validation failed' : 'Import failed' }}</strong>
              <div class="mt-2">
                <span class="badge bg-danger me-2">
                  {{ importResults.validationErrors.length }} {{ importResults.validationErrors.length === 1 ? 'error' : 'errors' }} found
                </span>
                <span v-if="importResults.totalProcessed > 0" class="badge bg-secondary">
                  {{ importResults.totalProcessed }} rows processed
                </span>
              </div>
            </div>

            <!-- Detailed Validation Errors -->
            <div v-if="importResults.validationErrors && importResults.validationErrors.length > 0" class="mt-3">
              <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center" style="background-color: var(--error-light); color: var(--error-dark);">
                  <strong>
                    <AlertTriangle :size="16" class="me-2" />
                    {{ importResults.validationErrors.length }} {{ importResults.validationErrors.length === 1 ? 'Error' : 'Errors' }} Found
                  </strong>
                  <small>Fix these issues and try again</small>
                </div>
                <div class="card-body p-0">
                  <div class="error-list" style="max-height: 400px; overflow-y: auto;">
                    <table class="table table-sm table-hover mb-0">
                      <tbody>
                        <tr 
                          v-for="(error, index) in importResults.validationErrors.slice(0, 50)" 
                          :key="index"
                          class="error-row"
                        >
                          <td style="width: 40px; text-align: center; color: var(--error);">
                            <XCircle :size="16" />
                          </td>
                          <td>
                            <div class="d-flex flex-column">
                              <span class="text-danger fw-bold" style="font-size: 0.875rem;">
                                {{ error }}
                              </span>
                            </div>
                          </td>
                        </tr>
                        <tr v-if="importResults.validationErrors.length > 50">
                          <td colspan="2" class="text-center text-muted py-3">
                            <Info :size="16" class="me-2" />
                            ... and {{ importResults.validationErrors.length - 50 }} more errors
                            <div class="mt-2">
                              <small>Showing first 50 errors. Fix these and validate again to see remaining issues.</small>
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                <div class="card-footer" style="background-color: var(--info-light); color: var(--info-dark);">
                  <small>
                    <Info :size="14" class="me-1" />
                    <strong>Tips:</strong> Each error shows the row number and what needs to be fixed. Update your file and validate again.
                  </small>
                </div>
              </div>
            </div>

            <!-- Success Actions -->
            <div v-if="importResults.success && !validateOnly && importResults.validationErrors.length === 0" class="mt-3">
              <div class="d-flex gap-2 flex-wrap">
                <button 
                  type="button" 
                  class="btn btn-export btn-sm btn-with-icon-sm"
                  @click="refreshProductList"
                  :disabled="loading"
                >
                  <RefreshCw :size="14" />
                  Refresh Product List
                </button>
                
                <button 
                  type="button" 
                  class="btn btn-view btn-sm btn-with-icon-sm"
                  @click="viewImportedProducts"
                  :disabled="loading"
                >
                  <Eye :size="14" />
                  View Imported Products
                </button>
              </div>
            </div>

            <!-- Validation Success Next Steps -->
            <div v-if="importResults.success && validateOnly && importResults.validationErrors.length === 0" class="mt-3">
              <div class="alert alert-success border-0" style="background-color: var(--success-light); color: var(--success-dark);">
                <CheckCircle :size="16" class="me-2" />
                <div>
                  <strong>✨ Your file is ready to import!</strong>
                  <p class="mb-0 mt-2">Uncheck "Validate only" and click "Import Products" to proceed with the actual import.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button 
            type="button" 
            class="btn btn-cancel btn-sm"
            data-bs-dismiss="modal"
            :disabled="isUploading || loading"
          >
            {{ (importResults?.success && !validateOnly && importResults?.validationErrors?.length === 0) ? 'Close' : 'Cancel' }}
          </button>
          
          <button 
            v-if="!importResults?.success || validateOnly || importResults?.validationErrors?.length > 0"
            type="button" 
            class="btn btn-submit btn-sm btn-with-icon-sm"
            @click="handleImport"
            :disabled="!canImport"
            :class="{ 'btn-loading': isUploading || loading }"
          >
            <Upload v-if="!isUploading && !loading" :size="14" />
            {{ getImportButtonText }}
          </button>

          <button 
            v-if="importResults?.success && !validateOnly && importResults?.validationErrors?.length === 0"
            type="button" 
            class="btn btn-add btn-sm btn-with-icon-sm"
            @click="startNewImport"
          >
            <Plus :size="14" />
            Import Another File
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { 
  Upload, FileSpreadsheet, AlertTriangle, Check, CheckCircle, 
  RefreshCw, Eye, Plus, Package, XCircle, Info
} from 'lucide-vue-next'
import { useProducts } from '@/composables/api/useProducts'
import apiProductsService from '@/services/apiProducts.js'

export default {
  name: 'ImportModal',
  components: {
    Upload, FileSpreadsheet, AlertTriangle, Check, CheckCircle,
    RefreshCw, Eye, Plus, Package, XCircle, Info
  },
  emits: ['import-completed', 'import-failed', 'refresh-products', 'view-imported-products'],
  
  setup(props, { emit }) {
    const {
      loading,
      error,
      fetchProducts
    } = useProducts()

    const selectedFile = ref(null)
    const validateOnly = ref(true)
    const skipDuplicates = ref(true)
    const updateExisting = ref(false)
    const isDownloading = ref(false)
    const isUploading = ref(false)
    const uploadProgress = ref(0)
    const uploadStatus = ref('')
    const importResults = ref(null)
    const fileInput = ref(null)
    const lastImportWasSuccessful = ref(false)
    const fileValidationError = ref(null)

    const canImport = computed(() => {
      return selectedFile.value && 
             !isUploading.value && 
             !loading.value && 
             !fileValidationError.value
    })

    const getImportButtonText = computed(() => {
      if (isUploading.value || loading.value) {
        return validateOnly.value ? 'Validating...' : 'Importing...'
      }
      return validateOnly.value ? 'Validate File' : 'Import Products'
    })

    // ✅ Prevent auto-import UI showing when switching modes
    watch(validateOnly, (value) => {
      if (!value) {
        importResults.value = null
      }
    })

    const downloadTemplate = async (fileType) => {
      try {
        isDownloading.value = true
        uploadStatus.value = `Downloading ${fileType.toUpperCase()} template...`
        
        await apiProductsService.downloadImportTemplate(fileType)
        
        uploadStatus.value = 'Template downloaded successfully!'
        setTimeout(() => {
          uploadStatus.value = ''
        }, 2000)
        
      } catch (error) {
        console.error('Error downloading template:', error)
        uploadStatus.value = 'Failed to download template'
        setTimeout(() => {
          uploadStatus.value = ''
        }, 3000)
      } finally {
        isDownloading.value = false
      }
    }

    const validateFile = (file) => {
      fileValidationError.value = null

      const maxSize = 10 * 1024 * 1024
      if (file.size > maxSize) {
        fileValidationError.value = `File size (${formatFileSize(file.size)}) exceeds the 10MB limit`
        return false
      }

      const allowedTypes = [
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      ]
      
      const fileExtension = file.name.toLowerCase().split('.').pop()
      const allowedExtensions = ['csv', 'xlsx', 'xls']

      if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
        fileValidationError.value = 'Invalid file type. Please select a CSV or Excel file'
        return false
      }

      return true
    }

    const onFileSelected = (event) => {
      const file = event.target.files[0]
      if (file && validateFile(file)) {
        selectedFile.value = file
        importResults.value = null
        validateOnly.value = true
      } else if (file) {
        selectedFile.value = null
      }
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const resetForm = () => {
      selectedFile.value = null
      validateOnly.value = true
      skipDuplicates.value = true
      updateExisting.value = false
      importResults.value = null
      uploadProgress.value = 0
      uploadStatus.value = ''
      isUploading.value = false
      isDownloading.value = false
      lastImportWasSuccessful.value = false
      fileValidationError.value = null
      
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }

    const startNewImport = () => {
      resetForm()
    }

    // ✅ FULLY FIXED VERSION — separate validation and import
    const handleImport = async () => {
      if (!selectedFile.value || !canImport.value) return

      try {
        isUploading.value = true
        uploadProgress.value = 0
        uploadStatus.value = validateOnly.value
          ? 'Validating file...'
          : 'Importing products...'

        const progressInterval = setInterval(() => {
          if (uploadProgress.value < 85) {
            uploadProgress.value += Math.random() * 15
            updateStatusMessage()
          }
        }, 300)

        let result
        if (validateOnly.value) {
          result = await apiProductsService.importProducts(selectedFile.value, true)
        } else {
          result = await apiProductsService.importProducts(selectedFile.value, false)
        }

        clearInterval(progressInterval)
        uploadProgress.value = 100

        const processedResult = parseImportResult(result)

        if (processedResult.success && processedResult.validationErrors.length === 0) {
          uploadStatus.value = validateOnly.value ? 'Validation completed!' : 'Import completed!'
          importResults.value = processedResult
          lastImportWasSuccessful.value = !validateOnly.value

          if (!validateOnly.value) {
            await fetchProducts()
            emit('import-completed', {
              totalSuccessful: processedResult.totalSuccessful,
              totalFailed: processedResult.totalFailed,
              batchesCreated: processedResult.batchesCreated
            })
          }

        } else {
          uploadStatus.value = validateOnly.value ? 'Validation failed' : 'Import completed with issues'
          uploadProgress.value = 0
          importResults.value = processedResult
          lastImportWasSuccessful.value = false

          emit('import-failed', { 
            message: processedResult.error, 
            details: result 
          })
        }

      } catch (error) {
        console.error('Import error:', error)
        uploadProgress.value = 0
        uploadStatus.value = validateOnly.value ? 'Validation failed' : 'Import failed'
        
        const errorMessage = error.response?.data?.error || 
                           error.response?.data?.message || 
                           error.message || 
                           'An unexpected error occurred'

        importResults.value = {
          success: false,
          error: errorMessage,
          totalProcessed: 0,
          totalSuccessful: 0,
          totalFailed: 0,
          batchesCreated: 0,
          validationErrors: [errorMessage]
        }

        lastImportWasSuccessful.value = false
        emit('import-failed', error)
      } finally {
        isUploading.value = false
      }
    }

    // unchanged
    const parseImportResult = (result) => {
      if (!result) {
        return {
          success: false,
          error: 'No response from server',
          totalProcessed: 0,
          totalSuccessful: 0,
          totalFailed: 0,
          batchesCreated: 0,
          validationErrors: ['No response from server']
        }
      }

      const data = result.results || result
      let errors = []
      let totalProcessed = 0
      let totalSuccessful = 0
      let totalFailed = 0

      if (validateOnly.value) {
        errors = data.errors || []
        totalProcessed = data.total_rows || 0
        totalSuccessful = data.valid_products || 0
        totalFailed = errors.length
      } else {
        totalProcessed = data.total_rows || 0
        totalSuccessful = data.successful || 0
        totalFailed = data.failed || 0
        
        const failedDetails = data.failed_details || []
        errors = failedDetails.map(f => `${f.product}: ${f.error}`)
      }
      
      const batchesCreated = data.batches_created || 0
      const batchCreationErrors = data.batch_creation_errors?.length || 0
      const productsWithoutBatches = totalSuccessful - batchesCreated
      
      const isSuccess = validateOnly.value ? 
        (errors.length === 0) :
        (totalSuccessful > 0)

      const hasWarnings = !validateOnly.value && (batchCreationErrors > 0 || productsWithoutBatches > 0)

      return {
        success: isSuccess,
        error: data.message || (isSuccess ? '' : 'Validation failed'),
        totalProcessed,
        totalSuccessful,
        totalFailed,
        totalSkipped: data.skipped || 0,
        batchesCreated,
        batchCreationErrors,
        productsWithoutBatches,
        hasWarnings,
        validationErrors: errors
      }
    }

    const updateStatusMessage = () => {
      const progress = uploadProgress.value
      if (progress < 20) {
        uploadStatus.value = 'Uploading file...'
      } else if (progress < 40) {
        uploadStatus.value = 'Processing data...'
      } else if (progress < 60) {
        uploadStatus.value = 'Validating products...'
      } else if (progress < 80) {
        uploadStatus.value = validateOnly.value ? 'Checking for errors...' : 'Creating products and batches...'
      } else {
        uploadStatus.value = 'Finalizing...'
      }
    }

    const refreshProductList = async () => {
      try {
        await fetchProducts()
        emit('refresh-products')
        uploadStatus.value = 'Product list refreshed!'
        setTimeout(() => {
          uploadStatus.value = ''
        }, 2000)
      } catch (error) {
        console.error('Error refreshing products:', error)
        uploadStatus.value = 'Failed to refresh product list'
      }
    }

    const viewImportedProducts = () => {
      const modal = bootstrap.Modal.getInstance(document.getElementById('importModal'))
      if (modal) {
        modal.hide()
      }
      
      emit('view-imported-products', importResults.value)
    }

    const onModalShown = () => {
      if (lastImportWasSuccessful.value) {
        resetForm()
      }
    }

    const onModalHidden = () => {
      uploadStatus.value = ''
    }

    let modalElement = null

    onMounted(() => {
      modalElement = document.getElementById('importModal')
      if (modalElement) {
        modalElement.addEventListener('shown.bs.modal', onModalShown)
        modalElement.addEventListener('hidden.bs.modal', onModalHidden)
      }
    })

    onUnmounted(() => {
      if (modalElement) {
        modalElement.removeEventListener('shown.bs.modal', onModalShown)
        modalElement.removeEventListener('hidden.bs.modal', onModalHidden)
      }
    })

    return {
      loading,
      error,
      selectedFile,
      validateOnly,
      skipDuplicates,
      updateExisting,
      isDownloading,
      isUploading,
      uploadProgress,
      uploadStatus,
      importResults,
      fileInput,
      fileValidationError,
      canImport,
      getImportButtonText,
      downloadTemplate,
      onFileSelected,
      formatFileSize,
      resetForm,
      startNewImport,
      handleImport,
      refreshProductList,
      viewImportedProducts,
      onModalShown,
      onModalHidden
    }
  }
}
</script>


<style scoped>
.modal-header {
  border-bottom: 1px solid var(--neutral-medium);
}

.modal-footer {
  border-top: 1px solid var(--neutral-medium);
}

.form-control:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 0.2rem rgba(115, 146, 226, 0.25);
}

.form-check-input:checked {
  background-color: var(--primary);
  border-color: var(--primary);
}

.progress {
  height: 10px;
  background-color: var(--neutral-light);
  border-radius: 5px;
  overflow: hidden;
}

.progress-bar {
  border-radius: 5px;
  transition: width 0.3s ease;
}

.progress-bar-striped {
  background-image: linear-gradient(45deg, rgba(255, 255, 255, 0.15) 25%, transparent 25%, transparent 50%, rgba(255, 255, 255, 0.15) 50%, rgba(255, 255, 255, 0.15) 75%, transparent 75%, transparent);
  background-size: 1rem 1rem;
}

.progress-bar-animated {
  animation: progress-bar-stripes 1s linear infinite;
}

@keyframes progress-bar-stripes {
  0% {
    background-position-x: 1rem;
  }
}

.alert {
  border-radius: 8px;
}

.alert ul {
  margin-left: 1.25rem;
  font-size: 0.875rem;
}

.alert code {
  background-color: rgba(0, 0, 0, 0.1);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}

.form-control[type="file"] {
  padding: 0.5rem;
}

.form-control[type="file"]:focus {
  box-shadow: 0 0 0 0.2rem rgba(115, 146, 226, 0.25);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-text {
  font-size: 0.8125rem;
}

.form-check {
  padding-left: 1.5em;
}

.form-check-input {
  margin-top: 0.15em;
}

.form-check-label {
  line-height: 1.4;
}

.btn-loading {
  position: relative;
  color: transparent !important;
}

.btn-loading::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 1rem;
  height: 1rem;
  border: 2px solid currentColor;
  border-radius: 50%;
  border-top-color: transparent;
  animation: btn-spin 0.8s linear infinite;
}

@keyframes btn-spin {
  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

.error-list {
  background-color: var(--neutral-light);
}

.error-list::-webkit-scrollbar {
  width: 8px;
}

.error-list::-webkit-scrollbar-track {
  background: var(--neutral-light);
}

.error-list::-webkit-scrollbar-thumb {
  background: var(--neutral-medium);
  border-radius: 4px;
}

.error-list::-webkit-scrollbar-thumb:hover {
  background: var(--neutral-dark);
}

.error-row:hover {
  background-color: var(--neutral-light);
}

.card {
  border: 1px solid var(--neutral-medium);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  padding: 0.75rem 1rem;
  font-weight: 600;
}

.card-footer {
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
}

:root {
  --warning-light: #FFF3CD;
  --warning-dark: #856404;
}

@media (max-width: 768px) {
  .modal-lg {
    max-width: 95%;
    margin: 1rem auto;
  }
  
  .d-flex.gap-2 {
    flex-direction: column;
  }
  
  .d-flex.gap-2 .btn {
    width: 100%;
  }
}
</style>