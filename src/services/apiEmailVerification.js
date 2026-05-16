/**
 * Email Verification API Service
 * Handles email verification code sending and verification
 */

class EmailVerificationService {
  constructor() {
    // Email verification endpoints are at /api/v1/notifications/email/
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    this.baseURL = `${baseUrl}/notifications/email`
  }

  /**
   * Send verification code to user's email
   * @param {string} email - User's email address
   * @returns {Promise<Object>} Response with token
   */
  async sendVerificationCode(email) {
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${this.baseURL}/send-code/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ email })
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || data.error || 'Failed to send verification code')
      }

      return data
    } catch (error) {
      console.error('Error sending verification code:', error)
      throw error
    }
  }

  /**
   * Verify email using code
   * @param {string} token - Verification token (returned from sendVerificationCode)
   * @param {string} code - 6-digit verification code
   * @returns {Promise<Object>} Verification result
   */
  async verifyCode(token, code) {
    try {
      const authToken = localStorage.getItem('access_token')
      const response = await fetch(`${this.baseURL}/verify-code/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': authToken ? `Bearer ${authToken}` : ''
        },
        body: JSON.stringify({ token, code })
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || data.error || 'Failed to verify code')
      }

      return data
    } catch (error) {
      console.error('Error verifying code:', error)
      throw error
    }
  }

  /**
   * Resend verification code
   * @param {string} email - User's email address
   * @returns {Promise<Object>} Response with token
   */
  async resendVerificationCode(email) {
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${this.baseURL}/resend-verification/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ email })
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || data.error || 'Failed to resend verification code')
      }

      return data
    } catch (error) {
      console.error('Error resending verification code:', error)
      throw error
    }
  }
}

// Export singleton instance
export const emailVerificationService = new EmailVerificationService()
export default emailVerificationService

