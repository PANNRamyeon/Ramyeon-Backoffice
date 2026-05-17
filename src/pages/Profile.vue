<template>
  <div class="profile-page">
    <!-- Page Header -->
    <header class="page-header">
      <h1 class="page-title">My Profile</h1>
      <p class="page-subtitle">Manage your account settings and email verification</p>
    </header>

    <!-- Profile Content -->
    <div class="profile-content">
      <!-- Profile Information Card -->
      <section class="profile-section surface-card">
        <header class="section-header">
          <h2 class="section-title">Profile Information</h2>
        </header>
        
        <div v-if="loadingUser" class="loading-state">
          <p class="text-tertiary">Loading profile information...</p>
        </div>
        
        <div v-else class="profile-info">
          <div class="info-row">
            <span class="info-label">Full Name</span>
            <span class="info-value">{{ userInfo.full_name || 'N/A' }}</span>
          </div>
          
          <div class="info-row">
            <span class="info-label">Username</span>
            <span class="info-value">{{ userInfo.username || 'N/A' }}</span>
          </div>
          
          <div class="info-row">
            <span class="info-label">Email</span>
            <div class="info-value-group info-value-group--email">
              <span class="info-value">{{ userInfo.email || 'N/A' }}</span>
              <span 
                v-if="isEmailVerified" 
                class="verification-badge verification-badge--verified"
                title="Email verified"
              >
                <CheckCircle :size="16" />
                Verified
              </span>
              <span 
                v-else 
                class="verification-badge verification-badge--unverified"
                title="Email not verified"
              >
                <AlertCircle :size="16" />
                Not Verified
              </span>
              
              <!-- Email Verification Controls -->
              <div v-if="!isEmailVerified" class="email-verification-controls">
                <button 
                  class="btn btn-primary btn-sm" 
                  @click="openVerificationModal"
                >
                  <Mail :size="14" />
                  Send Code
                </button>
              </div>
            </div>
          </div>
          
          <div class="info-row">
            <span class="info-label">Role</span>
            <span class="info-value">{{ userInfo.role || 'N/A' }}</span>
          </div>
          
          <div class="info-row">
            <span class="info-label">Status</span>
            <span class="info-value">{{ userInfo.status || 'N/A' }}</span>
          </div>
        </div>
      </section>


      <!-- Success Message -->
      <div v-if="verificationSuccess" class="alert alert-success">
        <CheckCircle :size="20" />
        <span>Email verified successfully!</span>
      </div>

      <!-- Error Message -->
      <div v-if="verificationError" class="alert alert-danger">
        <AlertCircle :size="20" />
        <span>{{ verificationError }}</span>
      </div>
    </div>

    <!-- Email Verification Modal -->
    <EmailVerificationModal
      ref="verificationModalRef"
      :email="userInfo.email"
      @send-code="handleModalSendCode"
      @verify-code="handleModalVerifyCode"
      @resend-code="handleModalResendCode"
      @verify="handleModalVerify"
      @close="handleModalClose"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from '@/composables/ui/useToast.js'
import { useAuth } from '@/composables/auth/useAuth.js'
import { emailVerificationService } from '@/services/apiEmailVerification.js'
import { CheckCircle, AlertCircle, Mail } from 'lucide-vue-next'
import EmailVerificationModal from '@/components/common/EmailVerificationModal.vue'

export default {
  name: 'Profile',
  components: {
    CheckCircle,
    AlertCircle,
    Mail,
    EmailVerificationModal
  },
  setup() {
    const { success, error: showError } = useToast()
    const { user, fetchCurrentUser, isLoading: authLoading } = useAuth()
    
    // Watch for user changes to update email verification status
    watch(() => user.value, (newUser) => {
      if (newUser) {
        const userData = newUser.user_data || newUser
        const emailVerified = newUser.email_verified !== undefined ? newUser.email_verified : 
                             (userData?.email_verified !== undefined ? userData.email_verified : false)
        if (emailVerified !== isEmailVerified.value) {
          isEmailVerified.value = emailVerified === true
          if (userInfo.value) {
            userInfo.value.email_verified = emailVerified === true
          }
        }
      }
    }, { deep: true })
    
    // User info
    const userInfo = ref({})
    const isEmailVerified = ref(false)
    const loadingUser = ref(false)
    
    // Verification state
    const verificationModalRef = ref(null)
    const verificationToken = ref(null)
    const verificationSuccess = ref(false)
    const verificationError = ref('')


    // Methods
    const loadUserInfo = async () => {
      loadingUser.value = true
      try {
        // Fetch user data from API
        const success = await fetchCurrentUser()
        
        if (success && user.value) {
          // The apiService.getCurrentUser() transforms the response
          // It spreads user_data fields, so user.value should have all fields at top level
          const userData = user.value
          
          // Handle both transformed format and raw format
          const rawUserData = userData.user_data || userData
          
          // Extract email_verified from multiple possible locations
          // Check top level first, then nested user_data, then default to false
          const emailVerified = userData.email_verified !== undefined ? userData.email_verified : 
                               (rawUserData && rawUserData.email_verified !== undefined ? rawUserData.email_verified : false)
          
          userInfo.value = {
            id: userData.id || userData.user_id || rawUserData?._id || rawUserData?.id || '',
            username: userData.username || rawUserData?.username || '',
            email: userData.email || rawUserData?.email || '',
            full_name: userData.full_name || userData.name || rawUserData?.full_name || rawUserData?.name || '',
            role: userData.role || rawUserData?.role || '',
            status: userData.status || rawUserData?.status || 'active',
            email_verified: emailVerified
          }
          // Set verification status - use strict boolean check
          isEmailVerified.value = emailVerified === true
        } else {
          console.error('Failed to fetch user data')
          showError('Failed to load user information')
        }
      } catch (err) {
        console.error('Error loading user info:', err)
        showError('Error loading user information: ' + (err.message || 'Unknown error'))
      } finally {
        loadingUser.value = false
      }
    }

    // Modal handlers
    const openVerificationModal = () => {
      if (verificationModalRef.value) {
        verificationModalRef.value.show()
      }
    }

    const handleModalSendCode = async (callback) => {
      if (!userInfo.value.email) {
        showError('Email address not found')
        callback(null)
        return
      }

      try {
        const result = await emailVerificationService.sendVerificationCode(userInfo.value.email)
        
        if (result.success && result.token) {
          verificationToken.value = result.token
          success('Verification code sent to your email')
          callback(result.token)
        } else {
          throw new Error(result.message || 'Failed to send verification code')
        }
      } catch (err) {
        console.error('Error sending verification code:', err)
        showError(err.message || 'Failed to send verification code')
        callback(null)
      }
    }

    const handleModalVerifyCode = async (token, code, callback) => {
      try {
        if (!token) {
          callback(false, 'Verification token is missing. Please request a new code.')
          return
        }
        
        const result = await emailVerificationService.verifyCode(token, code)
        
        if (result.success) {
          callback(true)
        } else {
          console.error('Verification failed:', result.message)
          callback(false, result.message || 'Invalid verification code')
        }
      } catch (err) {
        console.error('Error verifying code:', err)
        callback(false, err.message || 'Failed to verify code')
      }
    }

    const handleModalResendCode = async (callback) => {
      if (!userInfo.value.email) {
        showError('Email address not found')
        callback(null)
        return
      }

      try {
        const result = await emailVerificationService.resendVerificationCode(userInfo.value.email)
        
        if (result.success) {
          verificationToken.value = result.token
          success('Verification code resent to your email')
          callback(result.token)
        } else {
          throw new Error(result.message || 'Failed to resend verification code')
        }
      } catch (err) {
        showError(err.message || 'Failed to resend verification code')
        callback(null)
      }
    }

    const handleModalVerify = async () => {
      verificationSuccess.value = true
      isEmailVerified.value = true
      verificationToken.value = null
      success('Email verified successfully!')
      
      // Update user info immediately
      userInfo.value.email_verified = true
      
      // Wait a bit longer for backend to update database, then refresh
      // The backend updates the database for the test account
      setTimeout(async () => {
        await loadUserInfo()
        // Double-check after another short delay
        if (!isEmailVerified.value) {
          setTimeout(async () => {
            await loadUserInfo()
          }, 1500)
        }
      }, 1500)
    }

    const handleModalClose = () => {
      verificationToken.value = null
      verificationError.value = ''
      verificationSuccess.value = false
    }

    // Lifecycle
    onMounted(() => {
      loadUserInfo()
    })

    return {
      userInfo,
      isEmailVerified,
      loadingUser,
      verificationModalRef,
      verificationSuccess,
      verificationError,
      loadUserInfo,
      openVerificationModal,
      handleModalSendCode,
      handleModalVerifyCode,
      handleModalResendCode,
      handleModalVerify,
      handleModalClose
    }
  }
}
</script>

<style scoped>
.profile-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* Page Header */
.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 1rem;
}

/* Profile Content */
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Profile Section */
.profile-section {
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: var(--shadow-md);
}

.section-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-primary);
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

/* Profile Info */
.profile-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border-secondary);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-weight: 500;
  color: var(--text-secondary);
  min-width: 120px;
}

.info-value {
  color: var(--text-primary);
  font-weight: 400;
}

.info-value-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.info-value-group--email {
  justify-content: flex-end;
}

/* Verification Badge */
.verification-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
}

.verification-badge--verified {
  background-color: var(--status-success-bg);
  color: var(--status-success);
}

.verification-badge--unverified {
  background-color: var(--status-warning-bg);
  color: var(--status-warning);
}

/* Email Verification Controls */
.email-verification-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-sm {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1.5;
}

/* Alert Messages */
.alert {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 4px;
  margin-top: 1rem;
}

.alert-success {
  background-color: var(--status-success-bg);
  color: var(--status-success);
  border-left: 4px solid var(--status-success);
}

.alert-danger {
  background-color: var(--status-error-bg);
  color: var(--status-error);
  border-left: 4px solid var(--status-error);
}

/* Responsive */
@media (max-width: 768px) {
  .profile-page {
    padding: 1rem;
  }

  .info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .info-label {
    min-width: auto;
  }

  .verification-actions {
    flex-direction: column;
  }

  .verification-actions .btn {
    width: 100%;
  }
}
</style>

