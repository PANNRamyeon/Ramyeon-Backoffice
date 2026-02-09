import logging

from django.http import HttpResponseRedirect
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.oauth_service import oauth_service


logger = logging.getLogger(__name__)


class OAuthAuthorizeView(APIView):
    """
    Initiate OAuth flow for supported providers.
    Redirects the user agent to the provider authorization URL.
    """

    def get(self, request, provider: str):
        redirect_uri = (
            request.query_params.get("redirect_uri")
            or request.query_params.get("next")
            or ""
        )
        callback_url = request.build_absolute_uri(
            reverse("oauth-callback", args=[provider])
        )

        try:
            authorization_url = oauth_service.build_authorization_url(
                provider=provider,
                callback_url=callback_url,
                redirect_uri=redirect_uri,
            )
            return HttpResponseRedirect(authorization_url)
        except ValueError as error:
            logger.warning("OAuth authorize validation error: %s", error)
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("OAuth authorize unexpected failure: %s", exc)
            return Response(
                {"error": "Unable to initiate OAuth flow."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OAuthCallbackView(APIView):
    """
    OAuth provider callback endpoint.
    Exchanges code for tokens, upserts user, issues application JWT,
    and redirects back to the frontend with results encoded in URL fragment.
    """

    def get(self, request, provider: str):
        error = request.query_params.get("error")
        state_token = request.query_params.get("state")
        code = request.query_params.get("code")
        callback_url = request.build_absolute_uri(
            reverse("oauth-callback", args=[provider])
        )

        if error:
            logger.warning("OAuth callback received error '%s' from %s", error, provider)
            return self._redirect_with_error(provider, state_token, error)

        if not code or not state_token:
            logger.warning("OAuth callback missing code/state for provider %s", provider)
            return Response(
                {"error": "Missing authorization code or state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            provider_profile = oauth_service.exchange_code_for_profile(
                provider=provider,
                code=code,
                callback_url=callback_url,
                state_token=state_token,
            )

            customer = oauth_service.upsert_customer(provider_profile)
            token_payload = oauth_service.issue_tokens(customer)

            redirect_target = (
                provider_profile.get("state", {}).get("redirect_uri")
                or oauth_service.default_redirect
            )

            if redirect_target:
                params = oauth_service.build_success_params(token_payload)
                redirect_url = oauth_service.build_redirect_url(redirect_target, params)
                return HttpResponseRedirect(redirect_url)

            # Fallback: return JSON payload if no redirect target configured.
            return Response(token_payload, status=status.HTTP_200_OK)

        except ValueError as validation_error:
            logger.warning(
                "OAuth callback validation error for %s: %s",
                provider,
                validation_error,
            )
            return self._redirect_with_error(provider, state_token, str(validation_error))
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("OAuth callback failed for %s: %s", provider, exc)
            message = str(exc) or "OAuth authentication failed."
            return self._redirect_with_error(
                provider,
                state_token,
                message,
            )

    @staticmethod
    def _redirect_with_error(provider: str, state_token: str, message: str):
        redirect_target = oauth_service.default_redirect
        if state_token:
            try:
                decoded = oauth_service.decode_state_token(state_token)
                redirect_target = decoded.get("redirect_uri") or redirect_target
            except ValueError:
                logger.warning("Failed to decode OAuth state token during error redirect.")

        if redirect_target:
            params = oauth_service.build_error_params(message)
            redirect_url = oauth_service.build_redirect_url(redirect_target, params)
            return HttpResponseRedirect(redirect_url)

        return Response(
            {"error": message or "OAuth authentication failed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

