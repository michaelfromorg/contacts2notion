"""Custom exceptions for contacts2notion."""


class ContactsNotionError(Exception):
    """Base exception for all contacts2notion errors."""


class ConfigurationError(ContactsNotionError):
    """Configuration or environment variable error."""


class GoogleAPIError(ContactsNotionError):
    """Error from Google People API."""


class GoogleAuthError(GoogleAPIError):
    """Google OAuth authentication error."""


class NotionAPIError(ContactsNotionError):
    """Error from Notion API."""

    def __init__(self, status_code: int, message: str, page_id: str | None = None):
        self.status_code = status_code
        self.page_id = page_id
        super().__init__(f"Notion API error ({status_code}): {message}")


class RateLimitError(NotionAPIError):
    """Rate limit exceeded error."""

    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after
        message = f"Rate limited (retry after {retry_after}s)" if retry_after else "Rate limited"
        super().__init__(429, message)


class SyncError(ContactsNotionError):
    """Error syncing a specific contact."""

    def __init__(self, contact_id: str, name: str, original_error: Exception):
        self.contact_id = contact_id
        self.name = name
        self.original_error = original_error
        super().__init__(f"Failed to sync '{name}' ({contact_id}): {original_error}")
