"""
API Client for Training Platform
"""
import requests
from typing import Optional, Dict, Any
import os


class APIClient:
    """Client for interacting with the FastAPI backend"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("API_URL", "http://api-server:8000")
        self.token: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token if available"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Login to the platform

        Returns:
            dict: Response containing access_token and user info
        """
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            return data
        else:
            raise Exception(f"Login failed: {response.text}")

    def get_current_user(self) -> Dict[str, Any]:
        """
        Get current user information

        Returns:
            dict: User information
        """
        response = requests.get(
            f"{self.base_url}/api/v1/auth/me",
            headers=self._get_headers()
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user info: {response.text}")

    def logout(self) -> None:
        """Logout from the platform"""
        if self.token:
            requests.post(
                f"{self.base_url}/api/v1/auth/logout",
                headers=self._get_headers()
            )
        self.token = None

    def check_health(self) -> bool:
        """
        Check if the API is healthy

        Returns:
            bool: True if API is healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make a generic API request

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for requests

        Returns:
            Response data
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            **kwargs
        )

        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
