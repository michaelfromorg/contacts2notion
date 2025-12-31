"""Data models for contacts2notion."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class Contact(BaseModel):
    """Unified contact model for Google ↔ Notion sync."""

    # Primary key (Google People API resourceName: "people/c123456")
    google_id: str = Field(description="Google People API resourceName")

    # Core contact fields (synced both ways)
    first_name: str
    last_name: str = ""
    company: str | None = None
    title: str | None = None
    department: str | None = None
    primary_email: str | None = None
    secondary_email: str | None = None
    primary_phone: str | None = None
    secondary_phone: str | None = None
    birthday: date | None = None
    address: str | None = None
    website: str | None = None

    # Notion-only fields (never sync to Google)
    hide_birthday: bool = Field(default=False, description="When true, removes birthday from Google")
    tags: list[str] = Field(default_factory=list, description="Notion-only categories")
    notes: str | None = Field(default=None, description="Personal notes")
    last_contacted: date | None = Field(default=None, description="Tracking field")

    # Metadata
    last_synced_at: datetime | None = None

    @classmethod
    def from_google_api(cls, person: dict) -> "Contact":
        """Parse Google People API person resource.

        Expected person structure:
        {
            "resourceName": "people/c123456",
            "names": [{"givenName": "John", "familyName": "Doe"}],
            "emailAddresses": [{"value": "john@example.com", "type": "work"}],
            "phoneNumbers": [{"value": "+1234567890", "type": "mobile"}],
            "birthdays": [{"date": {"year": 1990, "month": 1, "day": 15}}],
            "organizations": [{"name": "Company", "title": "Engineer", "department": "Eng"}],
            "addresses": [{"formattedValue": "123 Main St"}],
            "urls": [{"value": "https://example.com"}],
        }
        """
        google_id = person.get("resourceName", "")

        # Extract name
        names = person.get("names", [])
        first_name = names[0].get("givenName", "") if names else ""
        last_name = names[0].get("familyName", "") if names else ""

        # Extract emails (up to 2)
        emails = person.get("emailAddresses", [])
        primary_email = emails[0].get("value") if len(emails) > 0 else None
        secondary_email = emails[1].get("value") if len(emails) > 1 else None

        # Extract phones (up to 2)
        phones = person.get("phoneNumbers", [])
        primary_phone = phones[0].get("value") if len(phones) > 0 else None
        secondary_phone = phones[1].get("value") if len(phones) > 1 else None

        # Extract birthday
        birthday_obj = None
        birthdays = person.get("birthdays", [])
        if birthdays:
            bd = birthdays[0].get("date", {})
            year = bd.get("year", 1900)  # Default to 1900 if year missing
            month = bd.get("month")
            day = bd.get("day")
            if month and day:
                try:
                    birthday_obj = date(year, month, day)
                except ValueError:
                    birthday_obj = None

        # Extract organization
        orgs = person.get("organizations", [])
        company = orgs[0].get("name") if orgs else None
        title = orgs[0].get("title") if orgs else None
        department = orgs[0].get("department") if orgs else None

        # Extract address (use formatted value)
        addresses = person.get("addresses", [])
        address = addresses[0].get("formattedValue") if addresses else None

        # Extract website
        urls = person.get("urls", [])
        website = urls[0].get("value") if urls else None

        return cls(
            google_id=google_id,
            first_name=first_name,
            last_name=last_name,
            company=company,
            title=title,
            department=department,
            primary_email=primary_email,
            secondary_email=secondary_email,
            primary_phone=primary_phone,
            secondary_phone=secondary_phone,
            birthday=birthday_obj,
            address=address,
            website=website,
            # Notion-only fields default to empty
            hide_birthday=False,
            tags=[],
            notes=None,
            last_contacted=None,
        )

    @classmethod
    def from_notion_page(cls, page: dict) -> "Contact":
        """Parse Notion page properties."""
        props = page.get("properties", {})

        def get_title(prop_name: str) -> str:
            """Extract title property."""
            prop = props.get(prop_name, {})
            title_list = prop.get("title", [])
            return title_list[0].get("plain_text", "") if title_list else ""

        def get_rich_text(prop_name: str) -> str | None:
            """Extract rich_text property."""
            prop = props.get(prop_name, {})
            rich_text = prop.get("rich_text", [])
            if rich_text:
                return rich_text[0].get("plain_text", "")
            return None

        def get_email(prop_name: str) -> str | None:
            """Extract email property."""
            prop = props.get(prop_name, {})
            return prop.get("email")

        def get_phone(prop_name: str) -> str | None:
            """Extract phone_number property."""
            prop = props.get(prop_name, {})
            return prop.get("phone_number")

        def get_date(prop_name: str) -> date | None:
            """Extract date property."""
            prop = props.get(prop_name, {})
            date_obj = prop.get("date")
            if date_obj and date_obj.get("start"):
                try:
                    return datetime.fromisoformat(date_obj["start"].replace("Z", "+00:00")).date()
                except (ValueError, AttributeError):
                    return None
            return None

        def get_checkbox(prop_name: str) -> bool:
            """Extract checkbox property."""
            prop = props.get(prop_name, {})
            return prop.get("checkbox", False)

        def get_multi_select(prop_name: str) -> list[str]:
            """Extract multi_select property."""
            prop = props.get(prop_name, {})
            options = prop.get("multi_select", [])
            return [opt.get("name", "") for opt in options]

        def get_url(prop_name: str) -> str | None:
            """Extract url property."""
            prop = props.get(prop_name, {})
            return prop.get("url")

        # Extract core fields
        google_id = get_rich_text("Google ID") or ""
        first_name = get_title("First Name") or ""
        last_name = get_rich_text("Last Name") or ""

        return cls(
            google_id=google_id,
            first_name=first_name,
            last_name=last_name,
            company=get_rich_text("Company"),
            title=get_rich_text("Job Title"),
            department=get_rich_text("Department"),
            primary_email=get_email("Primary Email"),
            secondary_email=get_email("Secondary Email"),
            primary_phone=get_phone("Primary Phone"),
            secondary_phone=get_phone("Secondary Phone"),
            birthday=get_date("Birthday"),
            address=get_rich_text("Address"),
            website=get_url("Website"),
            # Notion-only fields
            hide_birthday=get_checkbox("Hide Birthday"),
            tags=get_multi_select("Tags"),
            notes=get_rich_text("Notes"),
            last_contacted=get_date("Last Contacted"),
        )

    def to_notion_properties(self) -> dict[str, Any]:
        """Convert to Notion API property format.

        Returns dict with structure:
        {
            "First Name": {"title": [{"text": {"content": "..."}}]},
            "Last Name": {"rich_text": [{"text": {"content": "..."}}]},
            ...
        }
        """

        def rich_text(value: str | None) -> dict:
            """Format rich_text property."""
            if value:
                return {"rich_text": [{"text": {"content": value}}]}
            return {"rich_text": []}

        def title_prop(value: str) -> dict:
            """Format title property."""
            return {"title": [{"text": {"content": value}}]}

        def email_prop(value: str | None) -> dict:
            """Format email property."""
            if value:
                return {"email": value}
            return {"email": None}

        def phone_prop(value: str | None) -> dict:
            """Format phone_number property."""
            if value:
                return {"phone_number": value}
            return {"phone_number": None}

        def date_prop(value: date | None) -> dict:
            """Format date property."""
            if value:
                return {"date": {"start": value.isoformat()}}
            return {"date": None}

        def url_prop(value: str | None) -> dict:
            """Format url property."""
            if value:
                return {"url": value}
            return {"url": None}

        def checkbox_prop(value: bool) -> dict:
            """Format checkbox property."""
            return {"checkbox": value}

        def multi_select_prop(values: list[str]) -> dict:
            """Format multi_select property."""
            return {"multi_select": [{"name": tag} for tag in values]}

        return {
            "First Name": title_prop(self.first_name),
            "Last Name": rich_text(self.last_name),
            "Company": rich_text(self.company),
            "Job Title": rich_text(self.title),
            "Department": rich_text(self.department),
            "Primary Email": email_prop(self.primary_email),
            "Secondary Email": email_prop(self.secondary_email),
            "Primary Phone": phone_prop(self.primary_phone),
            "Secondary Phone": phone_prop(self.secondary_phone),
            "Birthday": date_prop(self.birthday),
            "Address": rich_text(self.address),
            "Website": url_prop(self.website),
            # Notion-only fields
            "Hide Birthday": checkbox_prop(self.hide_birthday),
            "Tags": multi_select_prop(self.tags),
            "Notes": rich_text(self.notes),
            "Last Contacted": date_prop(self.last_contacted),
            # Metadata
            "Google ID": rich_text(self.google_id),
            "Last Synced": date_prop(datetime.now().date()),
        }

    def to_google_person(self) -> dict[str, Any]:
        """Convert to Google People API person resource format.

        Returns dict for updateContact API call. Excludes Notion-only fields.
        If hide_birthday is True, birthday is excluded.
        """
        person: dict[str, Any] = {}

        # Names
        if self.first_name or self.last_name:
            person["names"] = [
                {
                    "givenName": self.first_name,
                    "familyName": self.last_name,
                }
            ]

        # Email addresses
        emails = []
        if self.primary_email:
            emails.append({"value": self.primary_email, "type": "work"})
        if self.secondary_email:
            emails.append({"value": self.secondary_email, "type": "home"})
        if emails:
            person["emailAddresses"] = emails

        # Phone numbers
        phones = []
        if self.primary_phone:
            phones.append({"value": self.primary_phone, "type": "mobile"})
        if self.secondary_phone:
            phones.append({"value": self.secondary_phone, "type": "home"})
        if phones:
            person["phoneNumbers"] = phones

        # Birthday (only if not hidden)
        if self.birthday and not self.hide_birthday:
            person["birthdays"] = [
                {
                    "date": {
                        "year": self.birthday.year,
                        "month": self.birthday.month,
                        "day": self.birthday.day,
                    }
                }
            ]

        # Organization
        if self.company or self.title or self.department:
            person["organizations"] = [
                {
                    "name": self.company or "",
                    "title": self.title or "",
                    "department": self.department or "",
                }
            ]

        # Address
        if self.address:
            person["addresses"] = [{"formattedValue": self.address}]

        # URLs/Website
        if self.website:
            person["urls"] = [{"value": self.website, "type": "homepage"}]

        return person


class SyncStats(BaseModel):
    """Statistics from a sync operation."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)
