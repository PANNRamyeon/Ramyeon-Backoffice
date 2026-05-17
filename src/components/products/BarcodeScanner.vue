<template>
  <div v-if="show" class="barcode-modal-overlay" @click="handleOverlayClick">
    <div class="barcode-modal" @click.stop>
      <!-- Modal Header -->
      <div class="modal-header">
        <h2 class="modal-title">Scan Product Barcode</h2>
        <button class="close-btn" @click="closeScanner" :disabled="scanning">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Scanner Content -->
      <div class="modal-body">
        <!-- Camera View -->
        <div class="camera-container">
          <div v-if="!cameraActive && !scanning" class="camera-placeholder">
            <svg class="camera-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
              <circle cx="12" cy="13" r="4"/>
            </svg>
            <p>Click "Start Scanner" to begin</p>
          </div>

          <div v-if="scanning" class="scanner-active">
            <div class="scanning-frame">
              <div class="scan-line"></div>
              <div class="corner-frame top-left"></div>
              <div class="corner-frame top-right"></div>
              <div class="corner-frame bottom-left"></div>
              <div class="corner-frame bottom-right"></div>
            </div>
            <p class="scanning-text">
              <svg class="scanning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 11-6.219-8.56"/>
              </svg>
              Scanning for barcode...
            </p>
          </div>

          <!-- Video element (hidden for now since we're simulating) -->
          <video 
            ref="videoElement" 
            v-show="cameraActive && !simulateMode"
            class="camera-video"
            autoplay
            muted
            playsinline
          ></video>
        </div>

        <!-- Status Messages -->
        <div v-if="errorMessage" class="status-message error">
          <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="status-message success">
          <svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"/>
          </svg>
          {{ successMessage }}
        </div>

        <!-- Manual Input Section -->
        <div class="manual-input-section">
          <h3 class="section-title">Or Enter Barcode Manually</h3>
          <div class="input-group">
            <input 
              v-model="manualBarcode"
              type="text"
              placeholder="Enter barcode number"
              class="barcode-input"
              @keyup.enter="handleManualBarcode"
              :disabled="scanning"
            />
            <button 
              class="btn btn-secondary"
              @click="handleManualBarcode"
              :disabled="scanning || !manualBarcode.trim()"
            >
              Add Product
            </button>
          </div>
        </div>

        <!-- Simulation Mode (for development) -->
        <div v-if="simulateMode" class="simulation-section">
          <h3 class="section-title">Development Mode - Simulate Scan</h3>
          <div class="simulation-grid">
            <button 
              v-for="sample in sampleBarcodes"
              :key="sample.code"
              class="sample-btn"
              @click="simulateScan(sample)"
              :disabled="scanning"
            >
              <div class="sample-info">
                <span class="sample-name">{{ sample.product_name }}</span>
                <span class="sample-code">{{ sample.code }}</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="modal-footer">
        <button 
          v-if="!scanning && !cameraActive"
          class="btn btn-primary"
          @click="startScanner"
        >
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="23,7 16,12 23,17"/>
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
          </svg>
          Start Scanner
        </button>

        <button 
          v-if="scanning"
          class="btn btn-error"
          @click="stopScanner"
        >
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="6" width="12" height="12"/>
          </svg>
          Stop Scanner
        </button>

        <button 
          class="btn btn-secondary"
          @click="closeScanner"
          :disabled="scanning"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BarcodeScanner',
  props: {
    show: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close', 'scanned'],
  data() {
    return {
      scanning: false,
      cameraActive: false,
      errorMessage: null,
      successMessage: null,
      manualBarcode: '',
      simulateMode: true, // Set to false when real camera scanning is implemented
      sampleBarcodes: [
        {
          code: '8801043032155',
          product_name: 'Samyang Hot Chicken Ramen',
          category_id: 'noodles',
          cost_price: 59.00
        },
        {
          code: '8801043031806',
          product_name: 'Samyang Carbonara Ramen',
          category_id: 'noodles',
          cost_price: 65.00
        },
        {
          code: '8801043031530',
          product_name: 'Nongshim Shin Ramyun',
          category_id: 'noodles',
          cost_price: 45.00
        },
        {
          code: '8801043031714',
          product_name: 'Pancit Canton Original',
          category_id: 'noodles',
          cost_price: 12.00
        },
        {
          code: '4901990346559',
          product_name: 'Nissin Cup Noodles',
          category_id: 'noodles',
          cost_price: 25.00
        },
        {
          code: '8934563150693',
          product_name: 'Mama Tom Yum Noodles',
          category_id: 'noodles',
          cost_price: 35.00
        }
      ]
    }
  },
  watch: {
    show(newVal) {
      if (newVal) {
        this.resetScanner()
      } else {
        this.stopScanner()
      }
    }
  },
  mounted() {
    // Handle escape key
    document.addEventListener('keydown', this.handleEscapeKey)
  },
  beforeUnmount() {
    document.removeEventListener('keydown', this.handleEscapeKey)
    this.stopScanner()
  },
  methods: {
    resetScanner() {
      this.scanning = false
      this.cameraActive = false
      this.errorMessage = null
      this.successMessage = null
      this.manualBarcode = ''
    },

    closeScanner() {
      this.stopScanner()
      this.$emit('close')
    },

    handleOverlayClick() {
      if (!this.scanning) {
        this.closeScanner()
      }
    },

    handleEscapeKey(event) {
      if (event.key === 'Escape' && this.show && !this.scanning) {
        this.closeScanner()
      }
    },

    async startScanner() {
      try {
        this.errorMessage = null
        this.scanning = true

        if (this.simulateMode) {
          // In simulation mode, just show the scanning UI
          this.successMessage = 'Click on a sample product below to simulate scanning'
          return
        }

        // Real camera implementation would go here
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: {
              facingMode: 'environment', // Use back camera if available
              width: { ideal: 640 },
              height: { ideal: 480 }
            }
          })

          this.$refs.videoElement.srcObject = stream
          this.cameraActive = true

          // Here you would integrate with a barcode scanning library
          // like @zxing/library, quagga2, or zbar-wasm
          this.simulateRealScan()

        } else {
          throw new Error('Camera access not supported by this browser')
        }

      } catch (error) {
        console.error('Error starting camera:', error)
        this.errorMessage = error.message || 'Failed to access camera'
        this.scanning = false
      }
    },

    stopScanner() {
      this.scanning = false
      
      if (this.$refs.videoElement && this.$refs.videoElement.srcObject) {
        const tracks = this.$refs.videoElement.srcObject.getTracks()
        tracks.forEach(track => track.stop())
        this.$refs.videoElement.srcObject = null
      }
      
      this.cameraActive = false
      this.clearMessages()
    },

    simulateRealScan() {
      // Simulate scanning delay
      setTimeout(() => {
        if (this.scanning && !this.simulateMode) {
          // In a real implementation, this would be triggered by the barcode library
          const randomSample = this.sampleBarcodes[Math.floor(Math.random() * this.sampleBarcodes.length)]
          this.handleScannedBarcode(randomSample)
        }
      }, 3000)
    },

    simulateScan(sampleData) {
      if (!this.scanning) return
      
      this.handleScannedBarcode(sampleData)
    },

    handleManualBarcode() {
      if (!this.manualBarcode.trim()) return

      // Create product data from manual input
      const barcodeData = {
        code: this.manualBarcode.trim(),
        product_name: `Product ${this.manualBarcode.trim()}`,
        category_id: '',
        cost_price: null
      }

      this.handleScannedBarcode(barcodeData)
    },

    handleScannedBarcode(barcodeData) {
      this.successMessage = `Scanned: ${barcodeData.product_name || barcodeData.code}`
      
      // Emit the scanned data
      this.$emit('scanned', barcodeData)
      
      // Auto-close after a short delay
      setTimeout(() => {
        this.closeScanner()
      }, 1500)
    },

    clearMessages() {
      this.errorMessage = null
      this.successMessage = null
    }
  }
}
</script>

<style scoped>
.barcode-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
}

.barcode-modal {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  animation: modalSlideIn 0.3s ease;
  display: flex;
  flex-direction: column;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--neutral);
  background-color: var(--primary-light);
  border-top-left-radius: 1rem;
  border-top-right-radius: 1rem;
  flex-shrink: 0;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--primary-dark);
  margin: 0;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 0.5rem;
  background-color: transparent;
  color: var(--tertiary-medium);
  cursor: pointer;
  transition: all 0.2s ease;
}

.close-btn:hover:not(:disabled) {
  background-color: var(--error-light);
  color: var(--error);
}

.close-btn svg {
  width: 20px;
  height: 20px;
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.camera-container {
  position: relative;
  width: 100%;
  height: 300px;
  background-color: var(--neutral-light);
  border-radius: 0.75rem;
  border: 2px dashed var(--neutral);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.camera-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: var(--tertiary-medium);
  text-align: center;
}

.camera-icon {
  width: 64px;
  height: 64px;
  color: var(--tertiary-medium);
}

.camera-placeholder p {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 500;
}

.scanner-active {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--primary-light), var(--secondary-light));
}

.scanning-frame {
  position: relative;
  width: 200px;
  height: 200px;
  border: 2px solid var(--primary);
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  overflow: hidden;
}

.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary);
  animation: scanLine 2s linear infinite;
}

@keyframes scanLine {
  0% { top: 0; }
  50% { top: calc(100% - 2px); }
  100% { top: 0; }
}

.corner-frame {
  position: absolute;
  width: 20px;
  height: 20px;
  border: 3px solid var(--primary);
}

.corner-frame.top-left {
  top: -2px;
  left: -2px;
  border-right: none;
  border-bottom: none;
}

.corner-frame.top-right {
  top: -2px;
  right: -2px;
  border-left: none;
  border-bottom: none;
}

.corner-frame.bottom-left {
  bottom: -2px;
  left: -2px;
  border-right: none;
  border-top: none;
}

.corner-frame.bottom-right {
  bottom: -2px;
  right: -2px;
  border-left: none;
  border-top: none;
}

.scanning-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--primary-dark);
  font-weight: 500;
  margin: 0;
}

.scanning-icon {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.status-message {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  font-weight: 500;
}

.status-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.status-message.success {
  background-color: var(--success-light);
  border: 1px solid var(--success);
  color: var(--success-dark);
}

.status-message.error {
  background-color: var(--error-light);
  border: 1px solid var(--error);
  color: var(--error-dark);
}

.manual-input-section,
.simulation-section {
  border-top: 1px solid var(--neutral);
  padding-top: 1.5rem;
  margin-top: 1.5rem;
}

.section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--tertiary-dark);
  margin: 0 0 1rem 0;
}

.input-group {
  display: flex;
  gap: 0.75rem;
}

.barcode-input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid var(--neutral);
  border-radius: 0.5rem;
  font-size: 1rem;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  background: white;
  color: var(--tertiary-dark);
}

.barcode-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(115, 146, 226, 0.1);
}

.simulation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 0.75rem;
}

.sample-btn {
  display: flex;
  align-items: center;
  padding: 1rem;
  border: 1px solid var(--neutral);
  border-radius: 0.5rem;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.sample-btn:hover:not(:disabled) {
  border-color: var(--primary);
  background-color: var(--primary-light);
}

.sample-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sample-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.sample-name {
  font-weight: 500;
  color: var(--tertiary-dark);
  font-size: 0.875rem;
}

.sample-code {
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.75rem;
  color: var(--tertiary-medium);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--neutral);
  background-color: var(--neutral-light);
  border-bottom-left-radius: 1rem;
  border-bottom-right-radius: 1rem;
  flex-shrink: 0;
}

.btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-radius: 0.5rem;
  border: none;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.875rem;
  white-space: nowrap;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-primary {
  background-color: var(--primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--primary-dark);
}

.btn-secondary {
  background-color: var(--neutral-medium);
  color: var(--tertiary-dark);
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--neutral-dark);
}

.btn-error {
  background-color: var(--error);
  color: white;
}

.btn-error:hover:not(:disabled) {
  background-color: var(--error-dark);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive Design */
@media (max-width: 768px) {
  .barcode-modal {
    margin: 0;
    border-radius: 0;
    height: 100vh;
    max-height: none;
  }
  
  .input-group {
    flex-direction: column;
  }
  
  .simulation-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-footer {
    flex-direction: column-reverse;
  }
  
  .camera-container {
    height: 250px;
  }
}

/* Animation for sample buttons */
.sample-btn {
  animation: fadeInUp 0.3s ease;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>