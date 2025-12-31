"""Contact syncer with 2-way sync logic."""

import logging
import sys

from contacts2notion.google.client import GoogleContactsClient
from contacts2notion.models import Contact, SyncStats
from contacts2notion.notion.client import NotionClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class ContactSyncer:
    """Handles 2-way sync between Google Contacts and Notion."""

    def __init__(
        self,
        notion_client: NotionClient,
        google_client: GoogleContactsClient,
        database_id: str,
    ):
        self.notion_client = notion_client
        self.google_client = google_client
        self.database_id = database_id

        # Lookup indexes
        self._google_id_to_page_id: dict[str, str] = {}
        self._email_to_page_id: dict[str, str] = {}  # Fallback
        self._phone_to_page_id: dict[str, str] = {}  # Fallback
        self._name_to_page_id: dict[str, str] = {}  # Fallback (for Facebook imports)

    async def initialize(self) -> None:
        """Build lookup indexes from existing Notion pages."""
        logger.info("Building lookup indexes from Notion...")
        self._google_id_to_page_id = {}
        self._email_to_page_id = {}
        self._phone_to_page_id = {}
        self._name_to_page_id = {}

        count = 0
        async for page in self.notion_client.query_database_all(self.database_id):
            count += 1
            page_id = page["id"]
            props = page.get("properties", {})

            # Index by Google ID (primary)
            google_id_prop = props.get("Google ID", {})
            rich_text = google_id_prop.get("rich_text", [])
            if rich_text:
                google_id = rich_text[0].get("plain_text", "")
                if google_id:
                    self._google_id_to_page_id[google_id] = page_id

            # Index by email (fallback for migration from CSV)
            primary_email_prop = props.get("Primary Email", {})
            primary_email = primary_email_prop.get("email")
            if primary_email:
                self._email_to_page_id[primary_email.lower()] = page_id

            # Index by phone (fallback for migration)
            primary_phone_prop = props.get("Primary Phone", {})
            primary_phone = primary_phone_prop.get("phone_number")
            if primary_phone:
                # Normalize phone (remove non-digits)
                normalized_phone = "".join(c for c in primary_phone if c.isdigit())
                if normalized_phone:
                    self._phone_to_page_id[normalized_phone] = page_id

            # Index by name (fallback for Facebook imports without email/phone)
            first_name_prop = props.get("First Name", {})
            first_name_list = first_name_prop.get("title", [])
            first_name = first_name_list[0].get("plain_text", "") if first_name_list else ""

            last_name_prop = props.get("Last Name", {})
            last_name_list = last_name_prop.get("rich_text", [])
            last_name = last_name_list[0].get("plain_text", "") if last_name_list else ""

            if first_name:
                # Normalize: lowercase "firstname lastname"
                name_key = f"{first_name.lower()} {last_name.lower()}".strip()
                if name_key:
                    self._name_to_page_id[name_key] = page_id

        logger.info(f"Indexed {len(self._google_id_to_page_id)} contacts with Google ID")
        logger.info(f"Total Notion pages: {count}")

    def _find_existing_page(self, contact: Contact) -> str | None:
        """
        Find existing Notion page for contact.

        Matching priority:
        1. Google ID (resourceName)
        2. Primary email
        3. Primary phone (normalized)
        4. Name (first + last, for Facebook imports)

        Returns page_id if found, None otherwise.
        """
        # Try Google ID first (most reliable)
        if contact.google_id and contact.google_id in self._google_id_to_page_id:
            return self._google_id_to_page_id[contact.google_id]

        # Try email (for migration from CSV)
        if contact.primary_email:
            page_id = self._email_to_page_id.get(contact.primary_email.lower())
            if page_id:
                return page_id

        # Try phone (for migration)
        if contact.primary_phone:
            normalized = "".join(c for c in contact.primary_phone if c.isdigit())
            page_id = self._phone_to_page_id.get(normalized)
            if page_id:
                return page_id

        # Try name (for Facebook imports with no email/phone)
        if contact.first_name:
            name_key = f"{contact.first_name.lower()} {contact.last_name.lower()}".strip()
            page_id = self._name_to_page_id.get(name_key)
            if page_id:
                return page_id

        return None

    async def sync_contact_to_notion(self, contact: Contact) -> tuple[str, str]:
        """
        Upsert single contact to Notion.

        Returns: (page_id, action) where action is "created" or "updated"
        """
        properties = contact.to_notion_properties()
        existing_page_id = self._find_existing_page(contact)

        if existing_page_id:
            # Update existing page
            await self.notion_client.update_page(existing_page_id, properties)
            # Update index if Google ID was added
            if contact.google_id:
                self._google_id_to_page_id[contact.google_id] = existing_page_id
            return existing_page_id, "updated"
        else:
            # Create new page
            result = await self.notion_client.create_page(self.database_id, properties)
            new_page_id = result["id"]
            # Update indexes
            if contact.google_id:
                self._google_id_to_page_id[contact.google_id] = new_page_id
            if contact.primary_email:
                self._email_to_page_id[contact.primary_email.lower()] = new_page_id
            return new_page_id, "created"

    async def sync_from_google(self) -> SyncStats:
        """
        Sync Google Contacts → Notion.

        Fetches all Google contacts and upserts to Notion.
        Preserves Notion-only fields for existing contacts.

        Returns SyncStats with counts.
        """
        logger.info("\n=== Syncing Google → Notion ===")
        stats = SyncStats()

        # Fetch Google contacts
        logger.info("Fetching contacts from Google...")
        google_contacts = await self.google_client.get_contacts()
        logger.info(f"Fetched {len(google_contacts)} contacts from Google")

        # Sync each contact
        for i, contact in enumerate(google_contacts, 1):
            try:
                # Check if contact exists in Notion
                existing_page_id = self._find_existing_page(contact)

                if existing_page_id:
                    # Load existing Notion page to preserve Notion-only fields
                    page = await self.notion_client.get_page(existing_page_id)
                    notion_contact = Contact.from_notion_page(page)
                    # Preserve Notion-only fields
                    contact.hide_birthday = notion_contact.hide_birthday
                    contact.tags = notion_contact.tags
                    contact.notes = notion_contact.notes
                    contact.last_contacted = notion_contact.last_contacted

                # Upsert to Notion
                _, action = await self.sync_contact_to_notion(contact)

                if action == "created":
                    stats.created += 1
                else:
                    stats.updated += 1

                if i % 10 == 0 or i == len(google_contacts):
                    logger.info(f"Progress: {i}/{len(google_contacts)} contacts synced")

            except Exception as e:
                error_msg = f"Failed to sync '{contact.first_name} {contact.last_name}': {e}"
                stats.errors.append(error_msg)
                logger.error(f"  Error: {error_msg}")

        logger.info(f"\nGoogle → Notion sync complete:")
        logger.info(f"  Created: {stats.created}")
        logger.info(f"  Updated: {stats.updated}")
        logger.info(f"  Errors: {len(stats.errors)}")

        return stats

    def _merge_contacts(self, google_contact: Contact, notion_contact: Contact) -> Contact:
        """
        Merge Google and Notion contacts with smart strategy.

        Rules:
        - If Google has data for a field → Use Google's value (Google wins)
        - If Google field is empty but Notion has data → Use Notion's value (fill the gap)
        - Always preserve Notion-only fields

        Returns merged contact ready to update in Google.
        """
        merged = google_contact.model_copy()

        # Fill in gaps where Google is empty but Notion has data
        if not merged.primary_email and notion_contact.primary_email:
            merged.primary_email = notion_contact.primary_email
        if not merged.secondary_email and notion_contact.secondary_email:
            merged.secondary_email = notion_contact.secondary_email
        if not merged.primary_phone and notion_contact.primary_phone:
            merged.primary_phone = notion_contact.primary_phone
        if not merged.secondary_phone and notion_contact.secondary_phone:
            merged.secondary_phone = notion_contact.secondary_phone
        if not merged.birthday and notion_contact.birthday and not notion_contact.hide_birthday:
            merged.birthday = notion_contact.birthday
        if not merged.company and notion_contact.company:
            merged.company = notion_contact.company
        if not merged.title and notion_contact.title:
            merged.title = notion_contact.title
        if not merged.department and notion_contact.department:
            merged.department = notion_contact.department
        if not merged.address and notion_contact.address:
            merged.address = notion_contact.address
        if not merged.website and notion_contact.website:
            merged.website = notion_contact.website

        # Handle "Hide Birthday" feature - remove birthday if checked
        if notion_contact.hide_birthday:
            merged.birthday = None

        return merged

    async def sync_to_google(self) -> SyncStats:
        """
        Sync Notion → Google (selective).

        Only syncs contacts that have a Google ID (came from Google originally).
        Applies smart merge:
        - Google fields take precedence if they have data
        - Notion fields fill in gaps where Google is empty
        - "Hide Birthday" removes birthday from Google

        Returns SyncStats with counts.
        """
        logger.info("\n=== Syncing Notion → Google ===")
        stats = SyncStats()

        # Fetch all Notion pages
        logger.info("Fetching contacts from Notion...")
        notion_pages = []
        async for page in self.notion_client.query_database_all(self.database_id):
            notion_pages.append(page)
        logger.info(f"Fetched {len(notion_pages)} contacts from Notion")

        # Process each Notion page
        for i, page in enumerate(notion_pages, 1):
            try:
                notion_contact = Contact.from_notion_page(page)

                # IMPORTANT: Only sync if contact has Google ID
                # This prevents syncing manual Notion entries to Google
                if not notion_contact.google_id:
                    stats.skipped += 1
                    continue

                # Fetch current Google contact
                try:
                    google_person = await self.google_client.get_contact(notion_contact.google_id)
                    google_contact = Contact.from_google_api(google_person)

                    # Merge: Google wins if exists, Notion fills gaps
                    merged_contact = self._merge_contacts(google_contact, notion_contact)

                    # Check if there are actual changes to sync
                    google_data = google_contact.to_google_person()
                    merged_data = merged_contact.to_google_person()

                    if google_data != merged_data:
                        # Update Google with merged data
                        await self.google_client.update_contact(
                            notion_contact.google_id, merged_contact
                        )
                        logger.info(
                            f"  Updated Google contact: {notion_contact.first_name} "
                            f"{notion_contact.last_name}"
                        )
                        stats.updated += 1

                except Exception as e:
                    error_msg = (
                        f"Failed to sync '{notion_contact.first_name} "
                        f"{notion_contact.last_name}' to Google: {e}"
                    )
                    stats.errors.append(error_msg)
                    logger.error(f"  Error: {error_msg}")

                if i % 10 == 0 or i == len(notion_pages):
                    logger.info(f"Progress: {i}/{len(notion_pages)} contacts processed")

            except Exception as e:
                error_msg = f"Failed to process Notion page: {e}"
                stats.errors.append(error_msg)
                logger.error(f"  Error: {error_msg}")

        logger.info(f"\nNotion → Google sync complete:")
        logger.info(f"  Updated: {stats.updated}")
        logger.info(f"  Skipped (no Google ID): {stats.skipped}")
        logger.info(f"  Errors: {len(stats.errors)}")

        return stats

    async def full_sync(self) -> tuple[SyncStats, SyncStats]:
        """
        Perform full 2-way sync.

        1. Google → Notion (primary direction)
        2. Notion → Google (apply Hide Birthday, etc.)

        Returns: (google_to_notion_stats, notion_to_google_stats)
        """
        # Initialize indexes
        await self.initialize()

        # Sync Google → Notion
        google_stats = await self.sync_from_google()

        # Sync Notion → Google
        notion_stats = await self.sync_to_google()

        return google_stats, notion_stats
