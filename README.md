# contacts2notion

2-way sync between Google Contacts and Notion database.

## Features

- **2-way sync**: Google Contacts ↔ Notion with intelligent conflict resolution
- **OAuth2 authentication**: Secure Google Contacts API integration with automatic token refresh
- **Smart deduplication**: Matches contacts by Google ID, email, or phone number
- **Notion-only fields**: Add personal metadata (tags, notes, last contacted) that never syncs to Google
- **Hide Birthday feature**: Remove birthdays from Google Contacts while keeping them in Notion
- **Automated sync**: GitHub Actions workflow runs weekly
- **Migration support**: Seamlessly imports existing Notion contacts and links them to Google

## Installation

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
# Clone the repository
git clone https://github.com/michaelfromorg/contacts2notion.git
cd contacts2notion

# Install dependencies
uv sync
```

## Setup

### 1. Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google People API**:
   - Navigate to **APIs & Services** → **Library**
   - Search for "Google People API" → Enable
4. Configure OAuth consent screen:
   - Go to **APIs & Services** → **OAuth consent screen**
   - Choose **External** user type
   - Fill in app name and support email
   - Add scope: `https://www.googleapis.com/auth/contacts`
   - Add your email as a test user
5. Create OAuth credentials:
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Application type: **Web application**
   - Add authorized redirect URI: `http://localhost:36133`
   - Save the **Client ID** and **Client Secret**

### 2. Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click **New integration**
3. Name it "contacts2notion" and select your workspace
4. Copy the **Internal Integration Token**
5. Create a new database in Notion (or use existing)
6. Share the database with your integration:
   - Open database → Click ⋯ → Add connections → Select your integration

### 3. Environment Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Notion
TOKEN_V3=ntn_your_notion_token_here
DATABASE_ID=your_notion_database_id_here

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your_secret_here
GOOGLE_REFRESH_TOKEN=  # Leave empty, will be filled by auth command
```

### 4. Initialize

Run the authorization flow to get your Google refresh token:

```bash
make auth
# or: uv run contacts2notion auth
```

This will:
1. Open your browser for Google authorization
2. Display the refresh token
3. Add it to your `.env` file manually

Initialize the Notion database schema:

```bash
make init-schema
# or: uv run contacts2notion init-schema
```

## Usage

### CLI Commands

```bash
# Show help
make run

# Authorize with Google (one-time setup)
make auth

# Initialize Notion database schema
make init-schema

# 2-way sync (default)
make sync

# One-way sync: Google → Notion only
make sync-google

# One-way sync: Notion → Google only (applies "Hide Birthday" changes)
make sync-notion

# View database statistics
make status
```

### Sync Behavior

**Google → Notion (Primary Direction)**
- Fetches all Google contacts
- Matches against existing Notion entries by Google ID, email, or phone
- Creates new Notion pages for new contacts
- Updates existing pages while preserving Notion-only fields
- Adds Google ID to matched contacts for future syncs

**Notion → Google (Selective)**
- Only syncs contacts that have a Google ID (came from Google originally)
- Respects "Hide Birthday" checkbox: removes birthday from Google when checked
- Manual Notion entries (without Google ID) are never synced to Google

**Conflict Resolution**
- Google Contacts is the source of truth for shared fields
- Notion-only fields are always preserved (Tags, Notes, Last Contacted, Hide Birthday)

## Notion Database Schema

The database includes these fields:

**Core Fields (synced with Google)**
- First Name (title)
- Last Name
- Company
- Job Title
- Department
- Primary Email
- Secondary Email
- Primary Phone
- Secondary Phone
- Birthday
- Address
- Website

**Notion-Only Fields (never synced to Google)**
- **Hide Birthday** (checkbox): When checked, removes birthday from Google Contacts
- **Tags** (multi-select): Personal organization tags
- **Notes** (rich text): Personal notes about the contact
- **Last Contacted** (date): Track when you last reached out

**Metadata**
- Google ID (rich text): Links contact to Google (auto-populated)
- Last Synced (date): Timestamp of last sync

## Automated Sync with GitHub Actions

The repository includes a workflow that syncs weekly (Sundays at midnight UTC). You can also trigger it manually anytime from the Actions tab.

### Setup GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions, and add:

- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
- `GOOGLE_REFRESH_TOKEN`: Your refresh token (from `make auth`)
- `NOTION_TOKEN`: Your Notion integration token
- `NOTION_DATABASE_ID`: Your Notion database ID

The workflow runs automatically every 6 hours, or you can trigger it manually from the Actions tab.

## Development

```bash
# Run linter
make check

# Format code
make format

# Type check
make typecheck

# Run tests
make test

# Clean build artifacts
make clean
```

## Architecture

```
src/contacts2notion/
├── cli.py              # Click CLI commands
├── config.py           # pydantic-settings configuration
├── models.py           # Contact Pydantic model
├── exceptions.py       # Custom exception hierarchy
├── google/
│   └── client.py       # Async Google People API client with OAuth2
└── notion/
    ├── client.py       # Async Notion API client
    ├── schema.py       # Database schema definition
    └── sync.py         # ContactSyncer with 2-way sync logic
```

## Migration from TypeScript Version

If you have an existing database from the TypeScript version:

1. Your existing contacts will be preserved
2. Run `make init-schema` to add new fields (Hide Birthday, Tags, Google ID)
3. First sync will match existing contacts by email/phone and add Google IDs
4. Future syncs will be faster with direct Google ID matching

## Troubleshooting

**"No refresh token configured" error**
- Run `make auth` to get a refresh token
- Make sure `GOOGLE_REFRESH_TOKEN` is set in `.env`

**"redirect_uri_mismatch" error**
- Verify `http://localhost:36133` is added as a redirect URI in Google Cloud Console
- The port must match exactly

**Contacts not syncing**
- Check database permissions (integration must have access)
- Run `make status` to see current database state
- Check that Google ID field is being populated

**Birthday not removing from Google**
- Only contacts with Google ID can sync back to Google
- Make sure "Hide Birthday" checkbox is checked in Notion
- Run `make sync` (not `make sync-google`)

## Contributing

This is a personal project, but suggestions and bug reports are welcome via GitHub issues.

## License

MIT