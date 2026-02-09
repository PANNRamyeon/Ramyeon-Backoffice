<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
    <div class="modal-dialog modal-xl modal-dialog-centered">
      <div class="modal-content modern-bulk-modal">
        <!-- Modal Header -->
        <div class="modal-header border-0 pb-0">
          <div class="d-flex align-items-center">
            <div class="modal-icon me-3">
              <Building :size="24" />
            </div>
            <div>
              <h4 class="modal-title mb-1">Bulk Add Suppliers</h4>
              <p class="text-muted mb-0 small">Add multiple suppliers efficiently (5-20 suppliers recommended)</p>
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
          <!-- Progress Indicator -->
          <div class="progress-indicator mb-4">
            <div class="step" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
              <div class="step-number">1</div>
              <div class="step-label">Choose Method</div>
            </div>
            <div class="step-connector" :class="{ active: currentStep > 1 }"></div>
            <div class="step" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
              <div class="step-number">2</div>
              <div class="step-label">Add Suppliers</div>
            </div>
            <div class="step-connector" :class="{ active: currentStep > 2 }"></div>
            <div class="step" :class="{ active: currentStep >= 3 }">
              <div class="step-number">3</div>
              <div class="step-label">Review & Save</div>
            </div>
          </div>

          <!-- Step 1: Choose Method -->
          <div v-if="currentStep === 1" class="step-content">
            <h5 class="mb-4">Choose how you'd like to add suppliers:</h5>
            
            <div class="row g-3">
              <div class="col-md-6">
                <div 
                  class="method-option"
                  :class="{ active: selectedMethod === 'manual' }"
                  @click="selectedMethod = 'manual'"
                >
                  <div class="method-icon manual">
                    <Edit :size="32" />
                  </div>
                  <div class="method-details">
                    <h6>Manual Entry</h6>
                    <p class="text-muted mb-0">Fill out a form with multiple supplier rows</p>
                    <small class="text-success">✓ Easy to use</small>
                  </div>
                </div>
              </div>
              
              <div class="col-md-6">
                <div 
                  class="method-option"
                  :class="{ active: selectedMethod === 'template' }"
                  @click="selectedMethod = 'template'"
                >
                  <div class="method-icon template">
                    <Download :size="32" />
                  </div>
                  <div class="method-details">
                    <h6>Use Template</h6>
                    <p class="text-muted mb-0">Download template, fill it out, then upload</p>
                    <small class="text-info">✓ Best for many suppliers</small>
                  </div>
                </div>
              </div>
            </div>

            <div class="mt-4 d-flex justify-content-end">
              <button 
                class="btn btn-primary"
                @click="proceedToStep2"
                :disabled="!selectedMethod"
              >
                Continue
                <ChevronRight :size="16" class="ms-1" />
              </button>
            </div>
          </div>

          <!-- Step 2: Add Suppliers -->
          <div v-if="currentStep === 2" class="step-content">
            <!-- Manual Entry Method -->
            <div v-if="selectedMethod === 'manual'">
              <div class="d-flex justify-content-between align-items-center mb-4">
                <h5 class="mb-0">Add Supplier Information</h5>
                <div class="d-flex gap-2">
                  <button 
                    class="btn btn-outline-success btn-sm"
                    @click="addSupplierRow"
                    :disabled="suppliers.length >= 20"
                  >
                    <Plus :size="16" class="me-1" />
                    Add Row
                  </button>
                  <button 
                    class="btn btn-outline-primary btn-sm"
                    @click="fillSampleData"
                  >
                    <Lightbulb :size="16" class="me-1" />
                    Fill Sample
                  </button>
                </div>
              </div>

              <div class="bulk-form-container">
                <div class="table-responsive">
                  <table class="table table-bordered bulk-suppliers-table">
                    <thead class="table-light sticky-top">
                      <tr>
                        <th style="width: 40px;">#</th>
                        <th style="width: 200px;">Company Name <span class="text-danger">*</span></th>
                        <th style="width: 150px;">Contact Person</th>
                        <th style="width: 180px;">Email</th>
                        <th style="width: 150px;">Phone</th>
                        <th style="width: 130px;">Type</th>
                        <th style="width: 100px;">Status</th>
                        <th style="width: 40px;">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr 
                        v-for="(supplier, index) in suppliers" 
                        :key="`supplier-${index}`"
                        :class="{ 'table-danger': supplier.errors && Object.keys(supplier.errors).length > 0 }"
                      >
                        <td class="text-center">{{ index + 1 }}</td>
                        
                        <!-- Company Name -->
                        <td>
                          <input 
                            type="text" 
                            class="form-control form-control-sm"
                            :class="{ 'is-invalid': supplier.errors?.name }"
                            v-model="supplier.name"
                            @input="validateSupplier(index)"
                            placeholder="Company name"
                          >
                          <div v-if="supplier.errors?.name" class="invalid-feedback">
                            {{ supplier.errors.name }}
                          </div>
                        </td>
                        
                        <!-- Contact Person -->
                        <td>
                          <input 
                            type="text" 
                            class="form-control form-control-sm"
                            v-model="supplier.contactPerson"
                            placeholder="Contact name"
                          >
                        </td>
                        
                        <!-- Email -->
                        <td>
                          <input 
                            type="email" 
                            class="form-control form-control-sm"
                            :class="{ 'is-invalid': supplier.errors?.email }"
                            v-model="supplier.email"
                            @input="validateSupplier(index)"
                            placeholder="email@company.com"
                          >
                          <div v-if="supplier.errors?.email" class="invalid-feedback">
                            {{ supplier.errors.email }}
                          </div>
                        </td>
                        
                        <!-- Phone -->
                        <td>
                          <input 
                            type="tel" 
                            class="form-control form-control-sm"
                            :class="{ 'is-invalid': supplier.errors?.phone }"
                            v-model="supplier.phone"
                            @input="validateSupplier(index)"
                            placeholder="+63 912 345 6789"
                          >
                          <div v-if="supplier.errors?.phone" class="invalid-feedback">
                            {{ supplier.errors.phone }}
                          </div>
                        </td>
                        
                        <!-- Type -->
                        <td>
                          <select 
                            class="form-select form-select-sm" 
                            v-model="supplier.type"
                          >
                            <option value="">Select type</option>
                            <option value="food">Food & Beverages</option>
                            <option value="packaging">Packaging</option>
                            <option value="equipment">Equipment</option>
                            <option value="services">Services</option>
                            <option value="raw_materials">Raw Materials</option>
                            <option value="other">Other</option>
                          </select>
                        </td>
                        
                        <!-- Status -->
                        <td>
                          <select 
                            class="form-select form-select-sm" 
                            v-model="supplier.status"
                          >
                            <option value="active">Active</option>
                            <option value="pending">Pending</option>
                            <option value="inactive">Inactive</option>
                          </select>
                        </td>
                        
                        <!-- Actions -->
                        <td class="text-center">
                          <button 
                            class="btn btn-outline-danger btn-sm"
                            @click="removeSupplierRow(index)"
                            :disabled="suppliers.length <= 1"
                            title="Remove row"
                          >
                            <Trash2 :size="14" />
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="mt-3">
                <small class="text-muted">
                  <Info :size="14" class="me-1" />
                  You can add up to 20 suppliers at once. Required fields are marked with *
                </small>
              </div>
            </div>

            <!-- Template Method -->
            <div v-else-if="selectedMethod === 'template'">
              <div class="text-center py-4">
                <div class="template-upload-area" :class="{ 'dragover': isDragOver }" 
                     @drop="handleFileDrop" 
                     @dragover.prevent="isDragOver = true" 
                     @dragleave="isDragOver = false">
                  
                  <div v-if="!uploadedFile">
                    <Upload :size="48" class="text-muted mb-3" />
                    <h5>Upload Your Supplier Data</h5>
                    <p class="text-muted mb-4">
                      First, download our template, fill it out, then upload it here
                    </p>
                    
                    <div class="d-flex justify-content-center gap-3 mb-4">
                      <button class="btn btn-outline-primary" @click="downloadTemplate">
                        <Download :size="16" class="me-1" />
                        Download Template
                      </button>
                      
                      <input 
                        type="file" 
                        ref="fileInput" 
                        @change="handleFileSelect" 
                        accept=".csv,.xlsx,.xls"
                        style="display: none;"
                      >
                      <button class="btn btn-primary" @click="$refs.fileInput.click()">
                        <Upload :size="16" class="me-1" />
                        Choose File
                      </button>
                    </div>
                    
                    <small class="text-muted">
                      Supported formats: CSV, Excel (.xlsx, .xls) • Max file size: 5MB
                    </small>
                  </div>
                  
                  <div v-else class="uploaded-file-info">
                    <CheckCircle :size="48" class="text-success mb-3" />
                    <h5>File Uploaded Successfully!</h5>
                    <p class="text-muted mb-3">
                      <FileText :size="16" class="me-1" />
                      {{ uploadedFile.name }} ({{ formatFileSize(uploadedFile.size) }})
                    </p>
                    <p class="text-success mb-3">
                      <strong>{{ parsedSuppliers.length }}</strong> suppliers found
                    </p>
                    
                    <div class="d-flex justify-content-center gap-2">
                      <button class="btn btn-outline-secondary" @click="clearUploadedFile">
                        <X :size="16" class="me-1" />
                        Remove File
                      </button>
                      <button class="btn btn-success" @click="useUploadedData">
                        <Check :size="16" class="me-1" />
                        Use This Data
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Navigation Buttons -->
            <div class="mt-4 d-flex justify-content-between">
              <button class="btn btn-outline-secondary" @click="currentStep = 1">
                <ChevronLeft :size="16" class="me-1" />
                Back
              </button>
              <button 
                class="btn btn-primary"
                @click="proceedToStep3"
                :disabled="!canProceedToStep3"
              >
                Review Suppliers
                <ChevronRight :size="16" class="ms-1" />
              </button>
            </div>
          </div>

          <!-- Step 3: Review & Save -->
          <div v-if="currentStep === 3" class="step-content">
            <h5 class="mb-4">Review Suppliers Before Adding</h5>
            
            <!-- Summary Stats -->
            <div class="row mb-4">
              <div class="col-md-3">
                <div class="stat-card">
                  <div class="stat-number text-primary">{{ validSuppliers.length }}</div>
                  <div class="stat-label">Valid Suppliers</div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="stat-card">
                  <div class="stat-number text-danger">{{ invalidSuppliers.length }}</div>
                  <div class="stat-label">With Errors</div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="stat-card">
                  <div class="stat-number text-warning">{{ duplicateCount }}</div>
                  <div class="stat-label">Potential Duplicates</div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="stat-card">
                  <div class="stat-number text-success">{{ suppliersToSave.length }}</div>
                  <div class="stat-label">Will Be Added</div>
                </div>
              </div>
            </div>

            <!-- Error Summary -->
            <div v-if="invalidSuppliers.length > 0" class="alert alert-warning">
              <AlertTriangle :size="16" class="me-2" />
              <strong>{{ invalidSuppliers.length }} suppliers have errors</strong> and will be skipped. 
              Go back to fix them or continue to add only the valid suppliers.
            </div>

            <!-- Suppliers List -->
            <div class="review-table-container">
              <div class="table-responsive">
                <table class="table table-sm">
                  <thead class="table-light">
                    <tr>
                      <th>Status</th>
                      <th>Company Name</th>
                      <th>Contact Person</th>
                      <th>Email</th>
                      <th>Phone</th>
                      <th>Type</th>
                      <th>Issues</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="(supplier, index) in suppliers" 
                      :key="`review-${index}`"
                      :class="getSupplierRowClass(supplier)"
                    >
                      <td>
                        <span v-if="isSupplierValid(supplier)" class="badge bg-success">
                          <Check :size="12" class="me-1" />
                          Valid
                        </span>
                        <span v-else class="badge bg-danger">
                          <X :size="12" class="me-1" />
                          Error
                        </span>
                      </td>
                      <td>{{ supplier.name || '-' }}</td>
                      <td>{{ supplier.contactPerson || '-' }}</td>
                      <td>{{ supplier.email || '-' }}</td>
                      <td>{{ supplier.phone || '-' }}</td>
                      <td>{{ getTypeLabel(supplier.type) }}</td>
                      <td>
                        <div v-if="supplier.errors && Object.keys(supplier.errors).length > 0">
                          <small 
                            v-for="(error, field) in supplier.errors" 
                            :key="field"
                            class="d-block text-danger"
                          >
                            {{ error }}
                          </small>
                        </div>
                        <span v-else class="text-muted">-</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Navigation Buttons -->
            <div class="mt-4 d-flex justify-content-between">
              <button class="btn btn-outline-secondary" @click="currentStep = 2">
                <ChevronLeft :size="16" class="me-1" />
                Back to Edit
              </button>
              <div class="d-flex gap-2">
                <button class="btn btn-outline-primary" @click="validateAllSuppliers">
                  <RefreshCw :size="16" class="me-1" />
                  Re-validate
                </button>
                <button 
                  class="btn btn-success"
                  @click="saveBulkSuppliers"
                  :disabled="suppliersToSave.length === 0 || saving"
                  :class="{ 'btn-loading': saving }"
                >
                  <div v-if="saving" class="spinner-border spinner-border-sm me-2"></div>
                  <Save :size="16" class="me-1" />
                  Add {{ suppliersToSave.length }} Suppliers
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { 
  Building, 
  Edit, 
  Download, 
  Upload,
  Plus, 
  Trash2, 
  ChevronRight, 
  ChevronLeft,
  Info,
  Lightbulb,
  FileText,
  CheckCircle,
  X,
  Check,
  AlertTriangle,
  RefreshCw,
  Save
} from 'lucide-vue-next'

export default {
  name: 'BulkSuppliersModal',
  components: {
    Building,
    Edit,
    Download,
    Upload,
    Plus,
    Trash2,
    ChevronRight,
    ChevronLeft,
    Info,
    Lightbulb,
    FileText,
    CheckCircle,
    X,
    Check,
    AlertTriangle,
    RefreshCw,
    Save
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
      currentStep: 1,
      selectedMethod: '',
      saving: false,
      
      // File upload
      uploadedFile: null,
      parsedSuppliers: [],
      isDragOver: false,
      
      // Suppliers data
      suppliers: [
        this.createEmptySupplier()
      ]
    }
  },
  computed: {
    canProceedToStep3() {
      if (this.selectedMethod === 'manual') {
        return this.suppliers.some(s => s.name && s.name.trim())
      } else if (this.selectedMethod === 'template') {
        return this.uploadedFile && this.parsedSuppliers.length > 0
      }
      return false
    },
    
    validSuppliers() {
      return this.suppliers.filter(s => this.isSupplierValid(s))
    },
    
    invalidSuppliers() {
      return this.suppliers.filter(s => !this.isSupplierValid(s) && (s.name || s.email || s.phone))
    },
    
    duplicateCount() {
      // Simple duplicate detection based on name or email
      const names = this.suppliers.map(s => s.name?.toLowerCase()).filter(Boolean)
      const emails = this.suppliers.map(s => s.email?.toLowerCase()).filter(Boolean)
      
      const duplicateNames = names.filter((name, index) => names.indexOf(name) !== index).length
      const duplicateEmails = emails.filter((email, index) => emails.indexOf(email) !== index).length
      
      return duplicateNames + duplicateEmails
    },
    
    suppliersToSave() {
      return this.validSuppliers.filter(s => s.name && s.name.trim())
    }
  },
  methods: {
    createEmptySupplier() {
      return {
        name: '',
        contactPerson: '',
        email: '',
        phone: '',
        address: '',
        type: '',
        status: 'active',
        notes: '',
        errors: {}
      }
    },
    
    proceedToStep2() {
      if (this.selectedMethod) {
        this.currentStep = 2
        if (this.selectedMethod === 'manual' && this.suppliers.length === 0) {
          this.suppliers = [this.createEmptySupplier()]
        }
      }
    },
    
    proceedToStep3() {
      if (this.selectedMethod === 'template' && this.uploadedFile) {
        this.suppliers = [...this.parsedSuppliers]
      }
      this.validateAllSuppliers()
      this.currentStep = 3
    },
    
    addSupplierRow() {
      if (this.suppliers.length < 20) {
        this.suppliers.push(this.createEmptySupplier())
      }
    },
    
    removeSupplierRow(index) {
      if (this.suppliers.length > 1) {
        this.suppliers.splice(index, 1)
      }
    },
    
    fillSampleData() {
      this.suppliers = [
        {
          name: 'ABC Food Distributors',
          contactPerson: 'Maria Santos',
          email: 'maria@abcfood.com',
          phone: '+63 917 123 4567',
          address: '123 Food Street, Manila',
          type: 'food',
          status: 'active',
          notes: 'Primary food supplier',
          errors: {}
        },
        {
          name: 'XYZ Packaging Solutions',
          contactPerson: 'Carlos Rivera',
          email: 'carlos@xyzpack.com',
          phone: '+63 922 987 6543',
          address: '456 Package Ave, Quezon City',
          type: 'packaging',
          status: 'active',
          notes: 'Eco-friendly packaging',
          errors: {}
        },
        {
          name: 'Tech Equipment Pro',
          contactPerson: 'Ana Lopez',
          email: 'ana@techequip.com',
          phone: '+63 933 555 0123',
          address: '789 Tech Blvd, Makati',
          type: 'equipment',
          status: 'pending',
          notes: 'Kitchen equipment specialist',
          errors: {}
        }
      ]
      
      this.validateAllSuppliers()
    },
    
    validateSupplier(index) {
      const supplier = this.suppliers[index]
      const errors = {}
      
      // Name validation
      if (!supplier.name || !supplier.name.trim()) {
        errors.name = 'Company name is required'
      } else if (supplier.name.trim().length < 2) {
        errors.name = 'Name must be at least 2 characters'
      }
      
      // Email validation (optional but must be valid if provided)
      if (supplier.email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRegex.test(supplier.email)) {
          errors.email = 'Invalid email format'
        }
      }
      
      // Phone validation (optional but must be valid if provided)
      if (supplier.phone) {
        const phoneRegex = /^[\d\s\+\-\(\)]+$/
        if (!phoneRegex.test(supplier.phone) || supplier.phone.replace(/\D/g, '').length < 10) {
          errors.phone = 'Invalid phone format'
        }
      }
      
      supplier.errors = errors
    },
    
    validateAllSuppliers() {
      this.suppliers.forEach((supplier, index) => {
        this.validateSupplier(index)
      })
    },
    
    isSupplierValid(supplier) {
      return supplier.name && 
             supplier.name.trim() && 
             (!supplier.errors || Object.keys(supplier.errors).length === 0)
    },
    
    getSupplierRowClass(supplier) {
      if (this.isSupplierValid(supplier)) {
        return 'table-success'
      } else if (supplier.name || supplier.email || supplier.phone) {
        return 'table-danger'
      }
      return ''
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
      return labels[type] || '-'
    },
    
    downloadTemplate() {
      const headers = ['Company Name*', 'Contact Person', 'Email', 'Phone', 'Address', 'Type', 'Status', 'Notes']
      const sampleData = [
        ['ABC Food Distributors', 'Maria Santos', 'maria@abcfood.com', '+63 917 123 4567', '123 Food St, Manila', 'food', 'active', 'Primary supplier'],
        ['XYZ Packaging Co', 'Carlos Rivera', 'carlos@xyzpack.com', '+63 922 987 6543', '456 Pack Ave, QC', 'packaging', 'active', 'Eco-friendly materials'],
        ['Tech Equipment Pro', 'Ana Lopez', 'ana@techequip.com', '+63 933 555 0123', '789 Tech Blvd, Makati', 'equipment', 'pending', 'Kitchen equipment']
      ]
      
      const csvContent = [
        headers.join(','),
        ...sampleData.map(row => row.map(cell => `"${cell}"`).join(','))
      ].join('\n')
      
      const blob = new Blob([csvContent], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'bulk_suppliers_template.csv'
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
      // Simple CSV parsing (in real app, use proper CSV parser)
      if (file.type === 'text/csv' || file.name.endsWith('.csv')) {
        const reader = new FileReader()
        reader.onload = (e) => {
          const text = e.target.result
          const lines = text.split('\n')
          const headers = lines[0].split(',').map(h => h.replace(/"/g, '').trim())
          
          this.parsedSuppliers = lines.slice(1)
            .filter(line => line.trim())
            .map(line => {
              const values = line.split(',').map(v => v.replace(/"/g, '').trim())
              return {
                name: values[0] || '',
                contactPerson: values[1] || '',
                email: values[2] || '',
                phone: values[3] || '',
                address: values[4] || '',
                type: values[5] || '',
                status: values[6] || 'active',
                notes: values[7] || '',
                errors: {}
              }
            })
          
          this.uploadedFile = file
        }
        reader.readAsText(file)
      } else {
        alert('Please upload a CSV file')
      }
    },
    
    clearUploadedFile() {
      this.uploadedFile = null
      this.parsedSuppliers = []
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = ''
      }
    },
    
    useUploadedData() {
      this.suppliers = [...this.parsedSuppliers]
      this.validateAllSuppliers()
      this.currentStep = 3
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },
    
    async saveBulkSuppliers() {
      this.saving = true
      
      try {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 2000))
        
        const suppliersToAdd = this.suppliersToSave.map(supplier => ({
          ...supplier,
          id: Date.now() + Math.random(),
          purchaseOrders: 0,
          createdAt: new Date().toISOString().split('T')[0]
        }))
        
        this.$emit('save', suppliersToAdd)
        this.$emit('close')
        
      } catch (error) {
        console.error('Error saving suppliers:', error)
        alert('Failed to save suppliers. Please try again.')
      } finally {
        this.saving = false
      }
    }
  },
  
  watch: {
    show(newVal) {
      if (newVal) {
        // Reset modal state when opened
        this.currentStep = 1
        this.selectedMethod = ''
        this.suppliers = [this.createEmptySupplier()]
        this.uploadedFile = null
        this.parsedSuppliers = []
        this.saving = false
      }
    }
  }
}
</script>

<style scoped>
/* Modern Modal styling */
.modern-bulk-modal {
  border-radius: 16px;
  border: none;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.modal-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary-light), var(--primary));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-dark);
}

.modal-title {
  color: var(--primary-dark);
  font-weight: 600;
  margin: 0;
}

.modal-header {
  padding: 2rem 2rem 1rem 2rem;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.modal-body {
  padding: 1.5rem 2rem 2rem 2rem;
  max-height: 70vh;
  overflow-y: auto;
}

/* Progress Indicator */
.progress-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2rem 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--neutral-medium);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  margin-bottom: 0.5rem;
  transition: all 0.3s ease;
}

.step.active .step-number {
  background-color: var(--primary);
}

.step.completed .step-number {
  background-color: var(--success);
}

.step-label {
  font-size: 0.875rem;
  color: var(--tertiary-medium);
  font-weight: 500;
}

.step.active .step-label {
  color: var(--primary-dark);
  font-weight: 600;
}

.step-connector {
  width: 80px;
  height: 2px;
  background-color: var(--neutral-medium);
  margin: 0 1rem;
  transition: all 0.3s ease;
}

.step-connector.active {
  background-color: var(--primary);
}

/* Method Selection */
.method-option {
  padding: 1.5rem;
  border: 2px solid var(--neutral-medium);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
  background-color: white;
  height: 100%;
}

.method-option:hover {
  border-color: var(--primary-light);
  box-shadow: 0 2px 8px rgba(115, 146, 226, 0.1);
}

.method-option.active {
  border-color: var(--primary);
  background-color: var(--primary-light);
}

.method-icon {
  width: 64px;
  height: 64px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1rem;
  transition: all 0.3s ease;
}

.method-icon.manual {
  background-color: #e8f4f8;
  color: var(--info);
}

.method-icon.template {
  background-color: #e8f5e8;
  color: var(--success);
}

.method-option.active .method-icon.manual {
  background-color: var(--info);
  color: white;
}

.method-option.active .method-icon.template {
  background-color: var(--success);
  color: white;
}

.method-details h6 {
  margin-bottom: 0.5rem;
  color: var(--tertiary-dark);
  font-weight: 600;
}

.method-details p {
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

/* Bulk Form */
.bulk-form-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--neutral-medium);
  border-radius: 8px;
}

.bulk-suppliers-table {
  margin-bottom: 0;
}

.bulk-suppliers-table th {
  background-color: #f8f9fa;
  font-weight: 600;
  color: var(--tertiary-dark);
  border-bottom: 2px solid var(--neutral-medium);
  font-size: 0.875rem;
}

.bulk-suppliers-table td {
  vertical-align: middle;
  padding: 0.5rem;
}

.bulk-suppliers-table .form-control,
.bulk-suppliers-table .form-select {
  font-size: 0.875rem;
  padding: 0.375rem 0.5rem;
}

/* Template Upload */
.template-upload-area {
  border: 2px dashed var(--neutral-medium);
  border-radius: 12px;
  padding: 3rem 2rem;
  transition: all 0.3s ease;
  background-color: #fafafa;
}

.template-upload-area.dragover {
  border-color: var(--primary);
  background-color: var(--primary-light);
}

.uploaded-file-info {
  text-align: center;
}

/* Review Section */
.stat-card {
  text-align: center;
  padding: 1rem;
  background: var(--neutral-light);
  border-radius: 8px;
  border: 1px solid var(--neutral-medium);
}

.stat-number {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--tertiary-medium);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.review-table-container {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--neutral-medium);
  border-radius: 8px;
}

/* Color classes */
.text-primary-dark {
  color: var(--primary-dark) !important;
}

.text-tertiary-dark {
  color: var(--tertiary-dark) !important;
}

.text-tertiary-medium {
  color: var(--tertiary-medium) !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .progress-indicator {
    flex-direction: column;
    gap: 1rem;
  }
  
  .step-connector {
    width: 2px;
    height: 40px;
    margin: 0.5rem 0;
  }
  
  .method-option {
    padding: 1rem;
  }
  
  .method-icon {
    width: 48px;
    height: 48px;
  }
  
  .bulk-form-container {
    max-height: 300px;
  }
  
  .modal-body {
    padding: 1rem;
    max-height: 80vh;
  }
}

@media (max-width: 576px) {
  .bulk-suppliers-table {
    font-size: 0.8rem;
  }
  
  .bulk-suppliers-table th,
  .bulk-suppliers-table td {
    padding: 0.25rem;
  }
  
  .stat-card {
    padding: 0.75rem;
  }
  
  .stat-number {
    font-size: 1.25rem;
  }
}

/* Button loading state */
.btn-loading {
  position: relative;
}

.btn-loading .spinner-border-sm {
  width: 1rem;
  height: 1rem;
}
</style>