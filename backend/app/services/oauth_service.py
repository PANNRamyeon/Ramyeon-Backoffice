import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple
from urllib.parse import quote

from decouple import config
from django.conf import settings
from jose import jwt, JWTError
from requests_oauthlib import OAuth2Session

from ..database import db_manager
from .auth_services import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from .customer_service import CustomerService


class OAuthService:
    """
    Service responsible for managing third-party OAuth flows (Google, Facebook).
    Handles authorization URL generation, code exchange, profile normalization,
    and user upsert/token issuance.
    """

    GOOGLE_SCOPE = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]
    FACEBOOK_SCOPE = ["public_profile", "email"]

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = db_manager.get_database()
        self.customer_service = CustomerService()
        self.customer_collection = self.db.customers

        self.allowed_redirects = config(
            "OAUTH_ALLOWED_REDIRECTS",
            default="",
            cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
        )
        self.default_redirect = config("OAUTH_DEFAULT_REDIRECT", default="")

        # State token configuration
        self.state_secret = config(
            "OAUTH_STATE_SECRET",
            default=getattr(settings, "SECRET_KEY", "oauth-state-secret"),
        )
        self.state_algorithm = config("OAUTH_STATE_ALGORITHM", default="HS256")
        self.state_ttl = config("OAUTH_STATE_TTL", default=600, cast=int)

    # --------------------------------------------------------------------- #
    # Provider configuration helpers
    # --------------------------------------------------------------------- #
    def _provider_settings(self, provider: str) -> Dict:
        provider = (provider or "").lower()
        if provider not in ("google", "facebook"):
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        if provider == "google":
            config_map = {
                "client_id": config("GOOGLE_CLIENT_ID", default=""),
                "client_secret": config("GOOGLE_CLIENT_SECRET", default=""),
                "authorization_base_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "userinfo_endpoint": "https://www.googleapis.com/oauth2/v3/userinfo",
                "scope": self.GOOGLE_SCOPE,
                "auth_params": {
                    "access_type": "offline",
                    "prompt": "consent",
                },
            }
        else:  # facebook
            config_map = {
                "client_id": config("FACEBOOK_APP_ID", default=""),
                "client_secret": config("FACEBOOK_APP_SECRET", default=""),
                "authorization_base_url": "https://www.facebook.com/v19.0/dialog/oauth",
                "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
                "userinfo_endpoint": "https://graph.facebook.com/me",
                "scope": self.FACEBOOK_SCOPE,
                "auth_params": {
                    "display": "popup",
                },
                "userinfo_params": {
                    "fields": "id,name,email,picture.type(large),first_name,last_name",
                },
            }

        if not config_map["client_id"] or not config_map["client_secret"]:
            raise ValueError(
                f"OAuth credentials are not configured for provider '{provider}'."
            )

        return config_map

    # --------------------------------------------------------------------- #
    # Redirect + state handling
    # --------------------------------------------------------------------- #
    def _sanitize_redirect(self, redirect_uri: str) -> str:
        redirect_uri = (redirect_uri or "").strip()
        if not redirect_uri:
            return self.default_redirect

        if not self.allowed_redirects:
            # If allow-list is empty, accept provided URI (use cautiously)
            return redirect_uri

        for allowed in self.allowed_redirects:
            if redirect_uri.startswith(allowed):
                return redirect_uri

        raise ValueError("Redirect URI is not allowed")

    def generate_state_token(self, provider: str, redirect_uri: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "provider": provider,
            "redirect_uri": redirect_uri,
            "nonce": secrets.token_urlsafe(16),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=self.state_ttl)).timestamp()),
        }
        return jwt.encode(payload, self.state_secret, algorithm=self.state_algorithm)

    def decode_state_token(self, token: str) -> Dict:
        try:
            return jwt.decode(
                token,
                self.state_secret,
                algorithms=[self.state_algorithm],
                options={"require": ["provider", "redirect_uri"]},
            )
        except JWTError as exc:
            raise ValueError(f"Invalid OAuth state token: {exc}") from exc

    # --------------------------------------------------------------------- #
    # Authorization / token exchange
    # --------------------------------------------------------------------- #
    def build_authorization_url(
        self, provider: str, callback_url: str, redirect_uri: str
    ) -> str:
        provider_cfg = self._provider_settings(provider)
        sanitized_redirect = self._sanitize_redirect(redirect_uri)
        state_token = self.generate_state_token(provider, sanitized_redirect)

        session = OAuth2Session(
            provider_cfg["client_id"],
            scope=provider_cfg["scope"],
            redirect_uri=callback_url,
            state=state_token,
        )

        auth_params = provider_cfg.get("auth_params", {})
        authorization_url, _ = session.authorization_url(
            provider_cfg["authorization_base_url"],
            **auth_params,
            state=state_token,
        )
        return authorization_url

    def exchange_code_for_profile(
        self, provider: str, code: str, callback_url: str, state_token: str
    ) -> Dict:
        provider_cfg = self._provider_settings(provider)

        # Validate state
        state_payload = self.decode_state_token(state_token)
        if state_payload.get("provider") != provider:
            raise ValueError("OAuth provider mismatch in state payload")

        oauth_session = OAuth2Session(
            provider_cfg["client_id"],
            scope=provider_cfg["scope"],
            redirect_uri=callback_url,
            state=state_token,
        )

        try:
            token = oauth_session.fetch_token(
                provider_cfg["token_url"],
                client_secret=provider_cfg["client_secret"],
                code=code,
                include_client_id=True,
            )
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"Token exchange failed: {exc}") from exc

        userinfo_params = provider_cfg.get("userinfo_params", {})
        try:
            response = oauth_session.get(
                provider_cfg["userinfo_endpoint"], params=userinfo_params
            )
            response.raise_for_status()
            userinfo = response.json()
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"Failed to fetch user profile: {exc}") from exc

        profile = self._normalize_profile(provider, userinfo)
        profile["provider_tokens"] = {k: token.get(k) for k in ("access_token", "id_token", "token_type")}
        profile["state"] = state_payload
        return profile

    # --------------------------------------------------------------------- #
    # Profile normalization and persistence
    # --------------------------------------------------------------------- #
    def _normalize_profile(self, provider: str, userinfo: Dict) -> Dict:
        provider = provider.lower()
        if provider == "google":
            profile = {
                "provider": provider,
                "provider_user_id": userinfo.get("sub"),
                "email": userinfo.get("email"),
                "email_verified": userinfo.get("email_verified", False),
                "full_name": userinfo.get("name"),
                "first_name": userinfo.get("given_name"),
                "last_name": userinfo.get("family_name"),
                "avatar_url": userinfo.get("picture"),
                "locale": userinfo.get("locale"),
                "raw_profile": userinfo,
            }
        else:  # facebook
            picture = userinfo.get("picture", {})
            picture_data = picture.get("data", {}) if isinstance(picture, dict) else {}
            profile = {
                "provider": provider,
                "provider_user_id": userinfo.get("id"),
                "email": userinfo.get("email"),
                "email_verified": bool(userinfo.get("email")),
                "full_name": userinfo.get("name"),
                "first_name": userinfo.get("first_name"),
                "last_name": userinfo.get("last_name"),
                "avatar_url": picture_data.get("url"),
                "locale": userinfo.get("locale"),
                "raw_profile": userinfo,
            }
        return profile

    def _provider_record(self, profile: Dict) -> Dict:
        now = datetime.now(timezone.utc)
        return {
            "provider": profile.get("provider"),
            "provider_user_id": profile.get("provider_user_id"),
            "email": profile.get("email"),
            "full_name": profile.get("full_name"),
            "first_name": profile.get("first_name"),
            "last_name": profile.get("last_name"),
            "avatar_url": profile.get("avatar_url"),
            "locale": profile.get("locale"),
            "last_login": now,
        }

    def upsert_customer(self, profile: Dict) -> Dict:
        provider = profile.get("provider")
        provider_user_id = profile.get("provider_user_id")
        email = (profile.get("email") or "").strip().lower()

        if not provider or not provider_user_id:
            raise ValueError("Provider profile is missing required identifiers.")

        # Attempt lookup by email
        customer = None
        if email:
            customer = self.customer_collection.find_one(
                {
                    "email": email,
                    "isDeleted": {"$ne": True},
                }
            )

        # Fallback lookup by provider ID
        if not customer:
            customer = self.customer_collection.find_one(
                {
                    "auth_providers": {
                        "$elemMatch": {
                            "provider": provider,
                            "provider_user_id": provider_user_id,
                        }
                    }
                }
            )

        now = datetime.now(timezone.utc)
        provider_entry = self._provider_record(profile)

        if not customer:
            customer_id = self.customer_service.generate_customer_id()
            username = email.split("@")[0] if email else customer_id.lower()

            customer_record = {
                "_id": customer_id,
                "username": username,
                "full_name": profile.get("full_name") or username,
                "email": email or None,
                "email_verified": profile.get("email_verified", False),
                "password": None,
                "password_set": False,
                "auth_mode": "oauth",
                "auth_providers": [provider_entry],
                "phone": "",
                "delivery_address": {},
                "loyalty_points": 0,
                "last_purchase": None,
                "isDeleted": False,
                "status": "active",
                "date_created": now,
                "last_updated": now,
                "source": provider,
            }

            self.customer_collection.insert_one(customer_record)
            self.logger.info(
                "Created new OAuth customer %s via %s",
                customer_id,
                provider,
            )
            customer = customer_record
        else:
            updates = {
                "last_updated": now,
            }

            if profile.get("email_verified"):
                updates["email_verified"] = True

            if profile.get("full_name"):
                updates["full_name"] = profile["full_name"]

            providers = customer.get("auth_providers", [])
            updated = False
            for entry in providers:
                if (
                    entry.get("provider") == provider
                    and entry.get("provider_user_id") == provider_user_id
                ):
                    entry.update(provider_entry)
                    updated = True
                    break

            if not updated:
                providers.append(provider_entry)

            updates["auth_providers"] = providers
            self.customer_collection.update_one(
                {"_id": customer["_id"]},
                {"$set": updates},
            )
            customer = self.customer_collection.find_one({"_id": customer["_id"]})

        return customer

    # --------------------------------------------------------------------- #
    # Token issuance
    # --------------------------------------------------------------------- #
    def issue_tokens(self, customer: Dict) -> Dict:
        auth_service = AuthService()
        user_id = str(customer["_id"])
        token_data = {
            "sub": user_id,
            "email": customer.get("email"),
            "role": "customer",
        }

        access_token = auth_service.create_access_token(token_data)
        refresh_token = auth_service.create_refresh_token(token_data)

        expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

        user_payload = {
            "id": user_id,
            "email": customer.get("email"),
            "full_name": customer.get("full_name"),
            "username": customer.get("username"),
            "email_verified": customer.get("email_verified", False),
            "loyalty_points": customer.get("loyalty_points", 0),
            "auth_mode": customer.get("auth_mode", "oauth"),
            "auth_providers": customer.get("auth_providers", []),
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": user_payload,
        }

    # --------------------------------------------------------------------- #
    # Fragment construction helpers
    # --------------------------------------------------------------------- #
    @staticmethod
    def build_success_params(token_payload: Dict) -> str:
        fragment_parts = [
            f"status=success",
            f"access_token={quote(token_payload['access_token'])}",
            f"refresh_token={quote(token_payload['refresh_token'])}",
            f"token_type={quote(token_payload['token_type'])}",
            f"expires_in={token_payload['expires_in']}",
            f"user_id={quote(token_payload['user']['id'])}",
            f"user_email={quote(token_payload['user'].get('email') or '')}",
            f"user_name={quote(token_payload['user'].get('full_name') or '')}",
            f"username={quote(token_payload['user'].get('username') or '')}",
            f"email_verified={str(int(bool(token_payload['user'].get('email_verified'))))}",
        ]
        return "&".join(fragment_parts)

    @staticmethod
    def build_error_params(message: str) -> str:
        return f"status=error&message={quote(message or 'OAuthError')}"

    @staticmethod
    def build_redirect_url(redirect_uri: str, params: str) -> str:
        """
        Attach query parameters to the supplied redirect URI while respecting
        hash-based SPA routes.
        """
        if not redirect_uri:
            return ""

        if "#" in redirect_uri:
            base, fragment = redirect_uri.split("#", 1)
            fragment = fragment or ""
            separator = "&" if "?" in fragment else "?" if fragment else ""
            new_fragment = f"{fragment}{separator}{params}" if fragment else params
            return f"{base}#{new_fragment}"

        separator = "&" if "?" in redirect_uri else "?"
        return f"{redirect_uri}{separator}{params}"


oauth_service = OAuthService()

