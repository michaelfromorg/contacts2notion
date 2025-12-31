"""Notion database schema definition for contacts."""

SCHEMA = {
    # Title field (required)
    "First Name": {"title": {}},
    # Core contact fields (synced with Google)
    "Last Name": {"rich_text": {}},
    "Company": {"rich_text": {}},
    "Job Title": {"rich_text": {}},
    "Department": {"rich_text": {}},
    "Primary Email": {"email": {}},
    "Secondary Email": {"email": {}},
    "Primary Phone": {"phone_number": {}},
    "Secondary Phone": {"phone_number": {}},
    "Birthday": {"date": {}},
    "Address": {"rich_text": {}},
    "Website": {"url": {}},
    # Notion-only fields (never sync to Google)
    "Hide Birthday": {"checkbox": {}},
    "Tags": {"multi_select": {"options": []}},
    "Notes": {"rich_text": {}},
    "Last Contacted": {"date": {}},
    # Metadata fields
    "Google ID": {"rich_text": {}},
    "Last Synced": {"date": {}},
}
