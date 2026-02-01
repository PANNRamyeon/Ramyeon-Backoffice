import logging
from django.core.management.base import BaseCommand
from app.services.user_service import UserService
from app.services.auth_services import AuthService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate authentication token for a MongoDB user'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email', 
            type=str, 
            required=True, 
            help='User email to generate token for'
        )
        
    def handle(self, *args, **options):
        email = options['email']
        
        try:
            # Get MongoDB user through your UserService
            user_service = UserService()
            mongo_user = user_service.get_user_by_email(email)
            
            if not mongo_user:
                self.stdout.write(
                    self.style.ERROR(f"No MongoDB user found with email: {email}")
                )
                return
                
            self.stdout.write(
                self.style.SUCCESS(
                    f"Found MongoDB user: {mongo_user.get('username', 'N/A')} ({mongo_user['email']})"
                )
            )
            
            # Generate tokens using your AuthService (same as login)
            auth_service = AuthService()
            
            # Use the same logic as your working login
            user_id = str(mongo_user['_id'])  # Convert ObjectId to string
            
            # Create token data (same as login)
            token_data = {
                "sub": user_id,
                "email": mongo_user['email'],
                "role": mongo_user.get('role', 'admin')
            }
            
            # Generate tokens
            access_token = auth_service.create_access_token(token_data)
            refresh_token = auth_service.create_refresh_token(token_data)
            
            # Display the tokens
            self._display_tokens(mongo_user, access_token, refresh_token)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error generating token: {str(e)}")
            )
            logger.error(f"Token generation failed: {str(e)}")
        
    def _display_tokens(self, mongo_user, access_token, refresh_token):
        """Display tokens in clean format"""
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS(" JWT AUTHENTICATION TOKENS "))
        self.stdout.write("="*70)
        self.stdout.write(f"User: {mongo_user.get('username', 'N/A')} ({mongo_user['email']})")
        self.stdout.write(f"Role: {mongo_user.get('role', 'N/A')}")
        self.stdout.write(f"User ID: {str(mongo_user['_id'])}")
        self.stdout.write("-"*70)
        self.stdout.write("ACCESS TOKEN:")
        self.stdout.write(access_token)
        self.stdout.write("")
        self.stdout.write("REFRESH TOKEN:")
        self.stdout.write(refresh_token)
        self.stdout.write("="*70)