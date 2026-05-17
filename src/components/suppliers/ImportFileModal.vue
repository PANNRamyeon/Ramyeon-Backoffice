<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
    <div class="modal-dialog modal-lg modal-dialog-centered">
      <div class="modal-content modern-import-modal">
        <!-- Modal Header -->
        <div class="modal-header border-0 pb-0">
          <div class="d-flex align-items-center">
            <div class="modal-icon me-3">
              <FileText :size="24" />
            </div>
            <div>
              <h4 class="modal-title mb-1">Import Suppliers from File</h4>
              <p class="text-secondary mb-0 small">Upload a CSV or Excel file to import multiple suppliers at once</p>
            </div>
          </div>
          <button 
            type="button" 
            class="btn-close" 
            @click="$emit('close')"
            aria-label="Close"
          ></button>
        </div>

        <!-- Modal Body -->
        <div class="modal-body pt-4">
          <div v-if="!uploadedFile" class="upload-section">
            <!-- Template Download Section -->
            <div class="template-section mb-4">
              <h5 class="mb-3">
                <Download :size="18" class="me-2" />
                Step 1: Download Template
              </h5>
              <p class="text-secondary mb-3">
                Download our template file, fill it out with your supplier data, then upload it back here.
              </p>
              
              <div class="template-info mb-3">
                <div class="row g-3">
                  <div class="col-md-6">
                    <div class="info-card">
                      <div class="info-icon">
                        <FileText :size="20" />
                      </div>
                      <div class="info-content">
                        <h6>Required Fields</h6>
                        <small class="text-secondary">Company Name is required. Email and Phone are validated if provided.</small>
                      </div>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <div class="info-card">
                      <div class="info-icon">
                        <Users :size="20" />
                      </div>
                      <div class="info-content">
                        <h6>Bulk Capacity</h6>
                        <small class="text-secondary">Import 20+ suppliers efficiently. No upper limit.</small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <button class="btn btn-export" @click="downloadTemplate">
                <Download :size="16" class="me-1" />
                Download CSV Template
              </button>
            </div>

            <hr class="my-4">

            <!-- File Upload Section -->
            <div class="upload-section">
              <h5 class="mb-3">
                <Upload :size="18" class="me-2" />
                Step 2: Upload Your File
              </h5>
              
              <div 
                class="upload-area" 
                :class="{ 'dragover': isDragOver }" 
                @drop="handleFileDrop" 
                @dragover.prevent="isDragOver = true" 
                @dragleave="isDragOver = false"
                @click="$refs.fileInput.click()"
              >
                <Upload :size="48" class="text-secondary mb-3" />
                <h6>Drag & Drop Your File Here</h6>
                <p class="text-secondary mb-3">or click to browse files</p>
                
                <div class="supported-formats">
                  <small class="text-secondary">
                    <strong>Supported formats:</strong> CSV, Excel (.xlsx, .xls)
                    <br>
                    <strong>Max file size:</strong> 10MB
                  </small>
                </div>
                
                <input 
                  type="file" 
                  ref="fileInput" 
                  @change="handleFileSelect" 
                  accept=".csv,.xlsx,.xls"
                  style="display: none;"
                >
              </div>
            </div>
          </div>

          <!-- File Uploaded Section -->
          <div v-else class="uploaded-section">
            <div class="uploaded-file-card">
              <div class="file-success-icon">
                <CheckCircle :size="48" class="text-status-success" />
              </div>
              
              <div class="file-info">
                <h5>File Uploaded Successfully!</h5>
                <div class="file-details mb-3">
                  <div class="detail-item">
                    <FileText :size="16" class="me-2" />
                    <span>{{ uploadedFile.name }}</span>
                  </div>
                  <div class="detail-item">
                    <Archive :size="16" class="me-2" />
                    <span>{{ formatFileSize(uploadedFile.size) }}</span>
                  </div>
                  <div class="detail-item">
                    <Users :size="16" class="me-2" />
                    <span class="text-status-success fw-bold">{{ parsedSuppliers.length }} suppliers found</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Preview Section -->
            <div class="preview-section mt-4">
              <h6 class="mb-3">
                <Eye :size="16" class="me-2" />
                Data Preview (First 5 rows)
              </h6>
              
              <div class="preview-table-container">
                <table class="table table-sm table-bordered">
                  <thead class="table-light">
                    <tr>
                      <th>Company Name</th>
                      <th>Contact Person</th>
                      <th>Email</th>
                      <th>Phone</th>
                      <th>Type</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(supplier, index) in previewData" :key="index">
                      <td>{{ supplier.supplier_name || '-' }}</td>
                      <td>{{ supplier.contact_person || '-' }}</td>
                      <td>{{ supplier.email || '-' }}</td>
                      <td>{{ supplier.phone_number || '-' }}</td>
                      <td>{{ getTypeLabel(supplier.type) }}</td>
                      <td>
                        <span :class="['badge', 'badge-sm', getStatusClass(supplier.status)]">
                          {{ formatStatus(supplier.status) }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <div v-if="parsedSuppliers.length > 5" class="text-center mt-2">
                <small class="text-secondary">
                  ... and {{ parsedSuppliers.length - 5 }} more suppliers
                </small>
              </div>
            </div>

            <!-- Validation Summary -->
            <div class="validation-summary mt-4">
              <div class="row g-3">
                <div class="col-md-3">
                  <div class="summary-card valid">
                    <div class="summary-number">{{ validCount }}</div>
                    <div class="summary-label">Valid</div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="summary-card invalid">
                    <div class="summary-number">{{ invalidCount }}</div>
                    <div class="summary-label">Invalid</div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="summary-card duplicates">
                    <div class="summary-number">{{ duplicateCount }}</div>
                    <div class="summary-label">Duplicates</div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="summary-card will-import">
                    <div class="summary-number">{{ willImportCount }}</div>
                    <div class="summary-label">Will Import</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Error Messages -->
            <div v-if="invalidCount > 0" class="alert alert-warning mt-3">
              <AlertTriangle :size="16" class="me-2" />
              <strong>{{ invalidCount }} suppliers have validation errors</strong> and will be skipped during import.
              Common issues: missing company name, invalid email format, invalid phone format.
            </div>

            <!-- Action Buttons -->
            <div class="mt-4 d-flex justify-content-center gap-3">
              <button class="btn btn-cancel" @click="clearUploadedFile">
                <X :size="16" class="me-1" />
                Remove File
              </button>
              <button
                class="btn btn-save"
                @click="processImport"
                :disabled="willImportCount === 0 || importing"
                :class="{ 'btn-loading': importing }"
              >
                <div v-if="importing" class="spinner-border spinner-border-sm me-2"></div>
                <Upload :size="16" class="me-1" />
                Import {{ willImportCount }} Suppliers
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { 
  FileText, 
  Download, 
  Upload, 
  Users,
  CheckCircle,
  Archive,
  Eye,
  X,
  AlertTriangle
} from 'lucide-vue-next'

export default {
  name: 'ImportFileModal',
  components: {
    FileText,
    Download,
    Upload,
    Users,
    CheckCircle,
    Archive,
    Eye,
    X,
    AlertTriangle
  },
  emits: ['close', 'save'],
  props: {
    show: {
      type: Boolean,
      default: false
    },
    existingSuppliers: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      uploadedFile: null,
      parsedSuppliers: [],
      isDragOver: false,
      importing: false
    }
  },
  computed: {
    previewData() {
      return this.parsedSuppliers.slice(0, 5)
    },
    
    validSuppliers() {
      return this.parsedSuppliers.filter(supplier => this.isSupplierValid(supplier))
    },
    
    validCount() {
      return this.validSuppliers.length
    },
    
    invalidCount() {
      return this.parsedSuppliers.length - this.validCount
    },
    
    duplicateCount() {
      // Simple duplicate detection based on name or email
      const names = this.parsedSuppliers.map(s => s.supplier_name?.toLowerCase()).filter(Boolean)
      const emails = this.parsedSuppliers.map(s => s.email?.toLowerCase()).filter(Boolean)
      
      const duplicateNames = names.filter((name, index) => names.indexOf(name) !== index).length
      const duplicateEmails = emails.filter((email, index) => emails.indexOf(email) !== index).length
      
      return duplicateNames + duplicateEmails
    },
    
    willImportCount() {
      return this.validCount
    }
  },
  methods: {
    downloadTemplate() {
      const headers = ['Company Name*', 'Contact Person', 'Email', 'Phone', 'Address', 'Type', 'Status', 'Notes']
      const sampleData = [
        ['ABC Food Distributors', 'Maria Santos', 'maria@abcfood.com', '+63 917 123 4567', '123 Food St, Manila', 'food', 'active', 'Primary supplier'],
        ['XYZ Packaging Co', 'Carlos Rivera', 'carlos@xyzpack.com', '+63 922 987 6543', '456 Pack Ave, QC', 'packaging', 'active', 'Eco-friendly materials'],
        ['Tech Equipment Pro', 'Ana Lopez', 'ana@techequip.com', '+63 933 555 0123', '789 Tech Blvd, Makati', 'equipment', 'pending', 'Kitchen equipment'],
        ['Fresh Produce Hub', 'Juan Dela Cruz', 'juan@freshproduce.ph', '+63 945 678 9012', '321 Market St, Caloocan', 'food', 'active', 'Organic vegetables'],
        ['Office Supplies Plus', 'Lisa Chen', 'lisa@officesupplies.com', '+63 956 789 0123', '654 Business Ave, Taguig', 'services', 'active', 'Office equipment']
      ]
      
      const csvContent = [
        headers.join(','),
        ...sampleData.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n')
      
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'suppliers_import_template.csv'
      a.click()
      window.URL.revokeObjectURL(url)
    },
    
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        this.processUploadedFile(file)
      }
    },
    
    handleFileDrop(event) {
      event.preventDefault()
      this.isDragOver = false
      const file = event.dataTransfer.files[0]
      if (file) {
        this.processUploadedFile(file)
      }
    },
    
    processUploadedFile(file) {
      // Validate file size (10MB max)
      if (file.size > 10 * 1024 * 1024) {
        alert('File size is too large. Maximum size is 10MB.')
        return
      }
      
      // Validate file type
      const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
      const allowedExtensions = ['.csv', '.xlsx', '.xls']
      
      if (!allowedTypes.includes(file.type) && !allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext))) {
        alert('Invalid file type. Please upload a CSV or Excel file.')
        return
      }
      
      // Process CSV files (for Excel files, you'd need a proper Excel parser)
      if (file.type === 'text/csv' || file.name.toLowerCase().endsWith('.csv')) {
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            const text = e.target.result
            const lines = text.split('\n').filter(line => line.trim())
            
            if (lines.length < 2) {
              alert('File appears to be empty or invalid.')
              return
            }
            
            const headers = lines[0].split(',').map(h => h.replace(/"/g, '').trim())
            
            this.parsedSuppliers = lines.slice(1)
              .map((line, index) => {
                try {
                  const values = line.split(',').map(v => v.replace(/"/g, '').trim())
                  return {
                    supplier_name: values[0] || '',
                    contact_person: values[1] || '',
                    email: values[2] || '',
                    phone_number: values[3] || '',
                    address: values[4] || '',
                    type: values[5] || 'other',
                    notes: values[6] || '',
                    _rowNumber: index + 2 // For error reporting
                  }
                } catch (error) {
                  console.error(`Error parsing line ${index + 2}:`, error)
                  return null
                }
              })
              .filter(supplier => supplier !== null)
            
            this.uploadedFile = file
            this.validateAllSuppliers()
            
          } catch (error) {
            console.error('Error parsing file:', error)
            alert('Error parsing file. Please check the format and try again.')
          }
        }
        reader.readAsText(file)
      } else {
        alert('Excel file support is not implemented yet. Please use CSV format.')
      }
    },
    
    validateAllSuppliers() {
      this.parsedSuppliers.forEach(supplier => {
        this.validateSupplier(supplier)
      })
    },
    
    validateSupplier(supplier) {
      const errors = {}
      
      // Name validation
      if (!supplier.supplier_name || !supplier.supplier_name.trim()) {
        errors.supplier_name = 'Company name is required'
      } else if (supplier.supplier_name.trim().length < 2) {
        errors.supplier_name = 'Name must be at least 2 characters'
      }

      // Email validation (optional but must be valid if provided)
      if (supplier.email && supplier.email.trim()) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRegex.test(supplier.email)) {
          errors.email = 'Invalid email format'
        }
      }

      // Phone validation (optional but must be valid if provided)
      if (supplier.phone_number && supplier.phone_number.trim()) {
        const phoneRegex = /^[\d\s\+\-\(\)]+$/
        if (!phoneRegex.test(supplier.phone_number) || supplier.phone_number.replace(/\D/g, '').length < 10) {
          errors.phone_number = 'Invalid phone format'
        }
      }
      
      supplier.errors = errors
    },
    
    isSupplierValid(supplier) {
      return supplier.supplier_name &&
             supplier.supplier_name.trim() &&
             (!supplier.errors || Object.keys(supplier.errors).length === 0)
    },
    
    clearUploadedFile() {
      this.uploadedFile = null
      this.parsedSuppliers = []
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = ''
      }
    },
    
    async processImport() {
      this.importing = true
      try {
        const { api } = await import('@/services/api.js')
        const created = []
        for (const supplier of this.validSuppliers) {
          const { errors, _rowNumber, ...data } = supplier
          const response = await api.post('/suppliers/', data)
          created.push(response.data)
        }
        this.$emit('save', created)
        this.$emit('close')
      } catch (error) {
        console.error('Error importing suppliers:', error)
        alert('Failed to import suppliers. Please try again.')
      } finally {
        this.importing = false
      }
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    
    getTypeLabel(type) {
      const labels = {
        'food': 'Food & Beverages',
        'packaging': 'Packaging',
        'equipment': 'Equipment',
        'services': 'Services',
        'raw_materials': 'Raw Materials',
        'other': 'Other'
      }
      return labels[type] || 'Other'
    },
    
    formatStatus(status) {
      return status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Active'
    },
    
    getStatusClass(status) {
      const classes = {
        'active': 'status-success',
        'pending': 'status-warning',
        'inactive': 'status-error'
      }
      return classes[status] || ''
    }
  },
  
  watch: {
    show(newVal) {
      if (newVal) {
        // Reset modal state when opened
        this.uploadedFile = null
        this.parsedSuppliers = []
        this.importing = false
        this.isDragOver = false
      }
    }
  }
}
</script>

<style scoped>
/* Modern Modal styling */
.modern-import-modal {
  border-radius: 16px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.modal-icon {
  width: 48px;
  height: 48px;
  background-color: var(--status-info-bg);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--status-info);
}

.modal-title {
  color: var(--text-primary);
  font-weight: 600;
  margin: 0;
}

.modal-header {
  padding: 2rem 2rem 1rem 2rem;
  background-color: var(--surface-secondary);
}

.modal-body {
  padding: 1.5rem 2rem 2rem 2rem;
  max-height: 80vh;
  overflow-y: auto;
}

/* Info Cards */
.info-card {
  display: flex;
  align-items: center;
  padding: 1rem;
  background: var(--surface-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-primary);
}

.info-icon {
  width: 40px;
  height: 40px;
  background: var(--surface-tertiary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-accent);
  margin-right: 0.75rem;
  flex-shrink: 0;
}

.info-content h6 {
  margin-bottom: 0.25rem;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.9rem;
}

/* Upload Area */
.upload-area {
  border: 2px dashed var(--border-primary);
  border-radius: 12px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: var(--surface-secondary);
}

.upload-area:hover {
  border-color: var(--border-accent);
  background-color: var(--state-hover);
}

.upload-area.dragover {
  border-color: var(--border-accent);
  background-color: var(--state-selected);
  transform: scale(1.02);
}

/* Uploaded File Card */
.uploaded-file-card {
  display: flex;
  align-items: center;
  padding: 1.5rem;
  background-color: var(--status-info-bg);
  border-radius: 12px;
  border: 1px solid var(--border-accent);
}

.file-success-icon {
  margin-right: 1.5rem;
}

.file-info h5 {
  margin-bottom: 0.5rem;
  color: var(--status-success);
  font-weight: 600;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-item {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Preview Table */
.preview-table-container {
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
}

.preview-table-container .table {
  margin-bottom: 0;
  font-size: 0.875rem;
}

.preview-table-container th {
  background-color: var(--surface-secondary);
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-primary);
  position: sticky;
  top: 0;
}

/* Summary Cards */
.summary-card {
  text-align: center;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
}

.summary-card.valid {
  background-color: var(--status-success-bg);
  border-color: var(--status-success);
}

.summary-card.invalid {
  background-color: var(--status-error-bg);
  border-color: var(--status-error);
}

.summary-card.duplicates {
  background-color: var(--status-warning-bg);
  border-color: var(--status-warning);
}

.summary-card.will-import {
  background-color: var(--status-info-bg);
  border-color: var(--status-info);
}

.summary-number {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.summary-card.valid .summary-number {
  color: var(--status-success);
}

.summary-card.invalid .summary-number {
  color: var(--status-error);
}

.summary-card.duplicates .summary-number {
  color: var(--status-warning);
}

.summary-card.will-import .summary-number {
  color: var(--text-accent);
}

.summary-label {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Badge styling */
.badge-sm {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .uploaded-file-card {
    flex-direction: column;
    text-align: center;
  }
  
  .file-success-icon {
    margin-right: 0;
    margin-bottom: 1rem;
  }
  
  .upload-area {
    padding: 2rem 1rem;
  }
  
  .modal-body {
    padding: 1rem;
  }
  
  .info-card {
    padding: 0.75rem;
  }
}
</style>