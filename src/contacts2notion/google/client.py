"""Google Contacts API client with OAuth2."""

import http.server
import urllib.parse
import webbrowser

import httpx

from contacts2notion.config import Settings
from contacts2notion.exceptions import GoogleAPIError, GoogleAuthError
from contacts2notion.models import Contact

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_PEOPLE_API_BASE = "https://people.googleapis.com/v1"


class GoogleContactsClient:
    """Async client for Google People API using OAuth2."""

    SCOPES = ["https://www.googleapis.com/auth/contacts"]

    def __init__(self, settings: Settings):
        self.settings = settings
        self._access_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def _refresh_token(self) -> str:
        """Refresh access token using refresh token."""
        if not self.settings.google_refresh_token:
            raise GoogleAuthError(
                "No refresh token configured. Run 'contacts2notion auth' first."
            )

        client = await self._get_client()

        try:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.settings.google_refresh_token,
                },
            )

            if response.status_code != 200:
                raise GoogleAuthError(
                    f"Token refresh failed ({response.status_code}): {response.text}"
                )

            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

        except httpx.HTTPError as e:
            raise GoogleAuthError(f"Token refresh request failed: {e}") from e

    async def _get_access_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self._access_token is None:
            return await self._refresh_token()
        return self._access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict | list:
        """Make authenticated API request."""
        client = await self._get_client()
        token = await self._get_access_token()

        try:
            response = await client.request(
                method,
                f"{GOOGLE_PEOPLE_API_BASE}{endpoint}",
                params=params,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code == 401:
                # Token expired, refresh and retry
                token = await self._refresh_token()
                response = await client.request(
                    method,
                    f"{GOOGLE_PEOPLE_API_BASE}{endpoint}",
                    params=params,
                    json=json,
                    headers={"Authorization": f"Bearer {token}"},
                )

            if response.status_code >= 400:
                raise GoogleAPIError(
                    f"Google People API error ({response.status_code}): {response.text}"
                )

            return response.json()

        except httpx.HTTPError as e:
            raise GoogleAPIError(f"Google People API request failed: {e}") from e

    def authorize(self, port: int = 8000) -> dict:
        """
        Run OAuth flow to get new tokens with proper scopes.

        Opens browser for user authorization, then exchanges code for tokens.
        Returns dict with access_token and refresh_token.
        """
        auth_code: str | None = None
        error: str | None = None

        class CallbackHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code, error
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)

                if "code" in params:
                    auth_code = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h1>Authorization successful!</h1>")
                    self.wfile.write(b"<p>You can close this window and return to the terminal.</p>")
                elif "error" in params:
                    error = params.get("error_description", params["error"])[0]
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f"<h1>Error: {error}</h1>".encode())
                else:
                    self.send_response(400)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logging

        # Build authorization URL
        auth_params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": f"http://localhost:{port}/callback",
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "access_type": "offline",  # Important: Request refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
        }
        auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"

        # Start local server
        server = http.server.HTTPServer(("localhost", port), CallbackHandler)
        server.timeout = 120  # 2 minute timeout

        # Open browser
        webbrowser.open(auth_url)

        # Wait for callback
        server.handle_request()
        server.server_close()

        if error:
            raise GoogleAuthError(f"Authorization failed: {error}")
        if not auth_code:
            raise GoogleAuthError("No authorization code received")

        # Exchange code for tokens
        with httpx.Client() as client:
            response = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "code": auth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": f"http://localhost:{port}/callback",
                },
            )

            if response.status_code != 200:
                raise GoogleAuthError(f"Token exchange failed: {response.text}")

            return response.json()

    async def get_contacts(self, page_size: int = 1000) -> list[Contact]:
        """
        Fetch all contacts from Google People API.

        Uses people.connections.list with pagination.
        Returns list of Contact objects.
        """
        contacts = []
        page_token = None

        # Person fields to request from API
        person_fields = ",".join([
            "names",
            "emailAddresses",
            "phoneNumbers",
            "birthdays",
            "organizations",
            "addresses",
            "urls",
            "metadata",
        ])

        while True:
            params = {
                "personFields": person_fields,
                "pageSize": page_size,
            }
            if page_token:
                params["pageToken"] = page_token

            data = await self._request("GET", "/people/me/connections", params=params)

            # Parse contacts
            for person in data.get("connections", []):
                try:
                    contact = Contact.from_google_api(person)
                    contacts.append(contact)
                except Exception as e:
                    # Skip contacts that fail to parse
                    print(f"Warning: Failed to parse contact: {e}")
                    continue

            # Check for more pages
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return contacts

    async def get_contact(self, resource_name: str) -> dict:
        """
        Fetch a single contact by resourceName.

        Args:
            resource_name: Google People API resourceName (e.g., "people/c123456")

        Returns:
            Person resource dict
        """
        person_fields = ",".join([
            "names",
            "emailAddresses",
            "phoneNumbers",
            "birthdays",
            "organizations",
            "addresses",
            "urls",
            "metadata",
        ])

        return await self._request(
            "GET",
            f"/{resource_name}",
            params={"personFields": person_fields},
        )

    async def update_contact(self, resource_name: str, contact: Contact) -> dict:
        """
        Update existing contact via People API.

        Args:
            resource_name: Google People API resourceName
            contact: Contact object with updated data

        Returns:
            Updated person resource
        """
        person = contact.to_google_person()

        # Build update mask (fields to update)
        update_fields = []
        if "names" in person:
            update_fields.append("names")
        if "emailAddresses" in person:
            update_fields.append("emailAddresses")
        if "phoneNumbers" in person:
            update_fields.append("phoneNumbers")
        if "birthdays" in person:
            update_fields.append("birthdays")
        if "organizations" in person:
            update_fields.append("organizations")
        if "addresses" in person:
            update_fields.append("addresses")
        if "urls" in person:
            update_fields.append("urls")

        return await self._request(
            "PATCH",
            f"/{resource_name}:updateContact",
            params={"updatePersonFields": ",".join(update_fields)},
            json=person,
        )

    async def delete_birthday(self, resource_name: str) -> None:
        """
        Remove birthday field from contact.

        Used when 'Hide Birthday' is checked in Notion.

        Args:
            resource_name: Google People API resourceName
        """
        await self._request(
            "PATCH",
            f"/{resource_name}:updateContact",
            params={"updatePersonFields": "birthdays"},
            json={"birthdays": []},  # Empty array removes the field
        )
