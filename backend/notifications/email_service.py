"""
Email Service for SendGrid Integration
Handles sending emails via SendGrid API
"""
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails via SendGrid"""
    
    def __init__(self):
        """Initialize SendGrid client"""
        self.api_key = config('SENDGRID_API_KEY', default='')
        self.from_email = config('SENDGRID_FROM_EMAIL', default='')
        self.from_name = config('SENDGRID_FROM_NAME', default='PANN POS System')
        
        if not self.api_key:
            logger.warning("SENDGRID_API_KEY not found in environment variables")
        
        if not self.from_email:
            logger.warning("SENDGRID_FROM_EMAIL not found in environment variables")
        
        try:
            self.sg = SendGridAPIClient(self.api_key) if self.api_key else None
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid client: {e}")
            self.sg = None
    
    def send_email(self, to_email, subject, html_content, plain_text_content=None):
        """
        Send email via SendGrid
        
        Args:
            to_email (str): Recipient email address
            subject (str): Email subject
            html_content (str): HTML email content
            plain_text_content (str, optional): Plain text email content
        
        Returns:
            dict: Result with success status and message
        """
        if not self.sg:
            logger.error("SendGrid client not initialized. Check API key.")
            return {
                'success': False,
                'error': 'SendGrid client not initialized'
            }
        
        if not to_email:
            logger.error("Recipient email is required")
            return {
                'success': False,
                'error': 'Recipient email is required'
            }
        
        try:
            # Create email message
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            # Add plain text content if provided
            if plain_text_content:
                message.plain_text_content = Content("text/plain", plain_text_content)
            
            # Send email
            response = self.sg.send(message)
            
            # Check response status
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}. Status: {response.status_code}")
                return {
                    'success': True,
                    'message': 'Email sent successfully',
                    'status_code': response.status_code
                }
            else:
                # Get error details
                error_body = response.body.decode('utf-8') if response.body else 'No error details'
                logger.error(f"Failed to send email. Status: {response.status_code}, Body: {error_body}")
                return {
                    'success': False,
                    'error': f'Failed to send email. Status: {response.status_code}. Details: {error_body}',
                    'status_code': response.status_code,
                    'error_details': error_body
                }
        
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_verification_code_email(self, to_email, verification_code, user_name=None):
        """
        Send email verification code email
        
        Args:
            to_email (str): Recipient email address
            verification_code (str): 6-digit verification code
            user_name (str, optional): User's name for personalization
        
        Returns:
            dict: Result with success status
        """
        subject = "Your Email Verification Code - PANN POS System"
        
        # HTML email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f9f9f9;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .code-box {{
                    background-color: #f5f5f5;
                    border: 2px dashed #4CAF50;
                    border-radius: 8px;
                    padding: 20px;
                    text-align: center;
                    margin: 20px 0;
                }}
                .verification-code {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #4CAF50;
                    letter-spacing: 8px;
                    font-family: 'Courier New', monospace;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Email Verification Code</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name or 'there'},</p>
                    <p>Thank you for registering with PANN POS System. Use the verification code below to verify your email address:</p>
                    
                    <div class="code-box">
                        <div class="verification-code">{verification_code}</div>
                    </div>
                    
                    <div class="warning">
                        <p><strong>Important:</strong> This code will expire in 10 minutes. Do not share this code with anyone.</p>
                    </div>
                    
                    <p>If you didn't request this code, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2025 PANN POS System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        plain_text_content = f"""
        Hello {user_name or 'there'},
        
        Thank you for registering with PANN POS System. Use the verification code below to verify your email address:
        
        Verification Code: {verification_code}
        
        This code will expire in 10 minutes. Do not share this code with anyone.
        
        If you didn't request this code, please ignore this email.
        
        © 2025 PANN POS System. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, plain_text_content)
    
    def send_verification_email(self, to_email, verification_token, user_name=None):
        """
        Legacy method - Send email verification email with link (for backward compatibility)
        
        Args:
            to_email (str): Recipient email address
            verification_token (str): JWT verification token
            user_name (str, optional): User's name for personalization
        
        Returns:
            dict: Result with success status
        """
        # Get frontend URL from environment or use default
        frontend_url = config('FRONTEND_URL', default='http://localhost:5173')
        verification_link = f"{frontend_url}/verify-email?token={verification_token}"
        
        subject = "Verify Your Email Address - PANN POS System"
        
        # HTML email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f9f9f9;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Email Verification</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name or 'there'},</p>
                    <p>Thank you for registering with PANN POS System. Please verify your email address by clicking the button below:</p>
                    <p style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{verification_link}</p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't create an account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2025 PANN POS System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        plain_text_content = f"""
        Hello {user_name or 'there'},
        
        Thank you for registering with PANN POS System. Please verify your email address by clicking the link below:
        
        {verification_link}
        
        This link will expire in 24 hours.
        
        If you didn't create an account, please ignore this email.
        
        © 2025 PANN POS System. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, plain_text_content)
    
    def send_shift_summary_email(self, to_email, shift_data, admin_name=None):
        """
        Send shift summary email to admin
        
        Args:
            to_email (str): Admin email address
            shift_data (dict): Shift summary data containing:
                - cashier_name (str): Name of the cashier
                - shift_start (str): Shift start time
                - shift_end (str): Shift end time
                - total_sales (float): Total sales amount
                - total_transactions (int): Number of transactions
                - session_duration (str): Duration of the shift
                - branch_id (str, optional): Branch ID
            admin_name (str, optional): Admin's name for personalization
        
        Returns:
            dict: Result with success status
        """
        subject = f"Shift Summary - {shift_data.get('cashier_name', 'Unknown')} - {shift_data.get('shift_end', '')}"
        
        # Format currency
        total_sales = shift_data.get('total_sales', 0)
        formatted_sales = f"₱{total_sales:,.2f}" if isinstance(total_sales, (int, float)) else str(total_sales)
        
        # HTML email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f9f9f9;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .header {{
                    background-color: #2196F3;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .summary-box {{
                    background-color: #f5f5f5;
                    border-left: 4px solid #2196F3;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .summary-item {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #ddd;
                }}
                .summary-item:last-child {{
                    border-bottom: none;
                }}
                .summary-label {{
                    font-weight: bold;
                    color: #666;
                }}
                .summary-value {{
                    color: #333;
                    font-size: 1.1em;
                }}
                .total-sales {{
                    font-size: 1.5em;
                    color: #4CAF50;
                    font-weight: bold;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Shift Summary Report</h1>
                </div>
                <div class="content">
                    <p>Hello {admin_name or 'Admin'},</p>
                    <p>A shift has been closed. Here's the summary:</p>
                    
                    <div class="summary-box">
                        <div class="summary-item">
                            <span class="summary-label">Cashier:</span>
                            <span class="summary-value">{shift_data.get('cashier_name', 'Unknown')}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Shift Start:</span>
                            <span class="summary-value">{shift_data.get('shift_start', 'N/A')}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Shift End:</span>
                            <span class="summary-value">{shift_data.get('shift_end', 'N/A')}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Duration:</span>
                            <span class="summary-value">{shift_data.get('session_duration', 'N/A')}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Total Transactions:</span>
                            <span class="summary-value">{shift_data.get('total_transactions', 0)}</span>
                        </div>
                        <div class="summary-item">
                            <span class="summary-label">Total Sales:</span>
                            <span class="summary-value total-sales">{formatted_sales}</span>
                        </div>
                        {f'<div class="summary-item"><span class="summary-label">Branch:</span><span class="summary-value">{shift_data.get("branch_id", "N/A")}</span></div>' if shift_data.get('branch_id') else ''}
                    </div>
                    
                    <p>This is an automated email from PANN POS System.</p>
                </div>
                <div class="footer">
                    <p>© 2025 PANN POS System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        plain_text_content = f"""
        Hello {admin_name or 'Admin'},
        
        A shift has been closed. Here's the summary:
        
        Cashier: {shift_data.get('cashier_name', 'Unknown')}
        Shift Start: {shift_data.get('shift_start', 'N/A')}
        Shift End: {shift_data.get('shift_end', 'N/A')}
        Duration: {shift_data.get('session_duration', 'N/A')}
        Total Transactions: {shift_data.get('total_transactions', 0)}
        Total Sales: {formatted_sales}
        {f"Branch: {shift_data.get('branch_id', 'N/A')}" if shift_data.get('branch_id') else ''}
        
        This is an automated email from PANN POS System.
        
        © 2025 PANN POS System. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, plain_text_content)
    
    def send_password_reset_email(self, to_email, reset_token, user_name=None):
        """
        Send password reset email with secure link
        
        Args:
            to_email (str): User's email address
            reset_token (str): Secure reset token
            user_name (str, optional): User's name for personalization
        
        Returns:
            dict: Result with success status
        """
        # Get frontend URL from environment
        frontend_url = config('FRONTEND_URL', default='http://localhost:5173')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        subject = "Reset Your Password - PANN POS System"
        
        # HTML email template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .container {{
                    background-color: #f9f9f9;
                    border-radius: 8px;
                    padding: 30px;
                    margin: 20px 0;
                }}
                .header {{
                    background-color: #FF5722;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #FF5722;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 20px;
                    color: #666;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name or 'there'},</p>
                    <p>We received a request to reset your password for your PANN POS account. Click the button below to create a new password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{reset_link}</p>
                    
                    <div class="warning">
                        <p><strong>⚠️ Security Notice:</strong></p>
                        <ul>
                            <li>This link will expire in <strong>1 hour</strong></li>
                            <li>If you didn't request this reset, please ignore this email</li>
                            <li>Your password will remain unchanged until you create a new one</li>
                        </ul>
                    </div>
                    
                    <p>For security reasons, we never send passwords via email.</p>
                </div>
                <div class="footer">
                    <p>© 2025 PANN POS System. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        plain_text_content = f"""
        Hello {user_name or 'there'},
        
        We received a request to reset your password for your PANN POS account.
        
        Click this link to reset your password:
        {reset_link}
        
        This link will expire in 1 hour.
        
        If you didn't request this reset, please ignore this email.
        Your password will remain unchanged until you create a new one.
        
        © 2025 PANN POS System. All rights reserved.
        """
        
        return self.send_email(to_email, subject, html_content, plain_text_content)

# Singleton instance
email_service = EmailService()

