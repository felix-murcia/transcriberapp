"""
OAuth2 adapter for authentication services.
Implements AuthServicePort using OAuth2 server.
"""

import os
import logging
from typing import Optional, Dict, Any, List

import requests

from domain.ports import AuthServicePort
from domain.exceptions import ExternalServiceError, AuthenticationError

logger = logging.getLogger(__name__)


class OAuth2Adapter(AuthServicePort):
    """Adapter for OAuth2 authentication service."""

    def __init__(self):
        self.server_url = os.getenv("OAUTH2_URL", "http://oauth2-server:8080")
        self.public_url = os.getenv("PUBLIC_OAUTH2_URL", "http://localhost:8080")
        self.client_id = os.getenv("OAUTH2_CLIENT_ID")
        self.client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
        self.timeout = int(os.getenv("OAUTH2_TIMEOUT", "30"))

    def _make_request(self, endpoint: str, method: str = "GET",
                     headers: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to OAuth2 server."""
        url = f"{self.server_url}/{endpoint.lstrip('/')}"

        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            else:
                response = requests.get(url, headers=headers, params=data, timeout=self.timeout)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"OAuth2 API request failed for {endpoint}: {e}")
            raise ExternalServiceError("oauth2", f"Request failed: {e}") from e

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate authentication token with OAuth2 server."""
        logger.info("Validating OAuth2 token")

        try:
            headers = {"Authorization": f"Bearer {token}"}
            result = self._make_request("/validate", headers=headers)

            if result.get("valid", False):
                return {
                    "user_id": result.get("user_id"),
                    "username": result.get("username"),
                    "email": result.get("email"),
                    "scopes": result.get("scopes", [])
                }
            else:
                return None

        except ExternalServiceError:
            # Token validation failed
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            return None

    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions from OAuth2 server."""
        logger.info(f"Getting permissions for user: {user_id}")

        try:
            result = self._make_request(f"/users/{user_id}/permissions")

            return result.get("permissions", [])

        except ExternalServiceError as e:
            logger.warning(f"Failed to get permissions for user {user_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting permissions: {e}")
            return []

    def get_login_url(self, redirect_uri: str) -> str:
        """Get OAuth2 login URL."""
        return f"{self.public_url}/authorize?client_id={self.client_id}&redirect_uri={redirect_uri}&response_type=code"

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        logger.info("Exchanging OAuth2 code for token")

        try:
            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            result = self._make_request("/token", method="POST", data=data)

            return {
                "access_token": result.get("access_token"),
                "token_type": result.get("token_type", "Bearer"),
                "expires_in": result.get("expires_in"),
                "refresh_token": result.get("refresh_token")
            }

        except ExternalServiceError as e:
            logger.error(f"Failed to exchange code for token: {e}")
            return None