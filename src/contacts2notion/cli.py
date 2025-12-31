"""CLI for contacts2notion."""

import asyncio

import click

from contacts2notion import __version__
from contacts2notion.config import Settings, get_settings
from contacts2notion.exceptions import ConfigurationError
from contacts2notion.google.client import GoogleContactsClient
from contacts2notion.notion.client import NotionClient
from contacts2notion.notion.schema import SCHEMA
from contacts2notion.notion.sync import ContactSyncer


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Sync Google Contacts with Notion database."""
    ctx.ensure_object(dict)

    # Load settings
    try:
        settings = get_settings()
        ctx.obj["settings"] = settings
    except Exception as e:
        ctx.obj["settings_error"] = str(e)


@main.command()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """Authorize with Google to get refresh token.

    Opens a browser for Google OAuth authorization, then displays
    the refresh token to add to your .env file.
    """
    settings: Settings | None = ctx.obj.get("settings")
    if settings is None:
        click.echo(f"Error loading settings: {ctx.obj.get('settings_error')}", err=True)
        ctx.exit(1)

    click.echo("Opening browser for Google authorization...")
    click.echo("(Make sure 'http://localhost:36133' is set as a redirect URI)")
    click.echo()

    google_client = GoogleContactsClient(settings)
    try:
        tokens = google_client.authorize(port=36133)
        click.echo()
        click.echo("Authorization successful!")
        click.echo()
        click.echo("Add this to your .env file:")
        click.echo(f'GOOGLE_REFRESH_TOKEN={tokens["refresh_token"]}')
        click.echo()
        if "access_token" in tokens:
            click.echo(f"Access token (expires): {tokens['access_token'][:20]}...")
        if "expires_in" in tokens:
            click.echo(f"Expires in: {tokens['expires_in']} seconds")
    except Exception as e:
        click.echo(f"Authorization failed: {e}", err=True)
        ctx.exit(1)


@main.command("init-schema")
@click.pass_context
def init_schema(ctx: click.Context) -> None:
    """Initialize Notion database schema.

    Creates or updates database properties to match the required schema.
    Safe to run multiple times - only adds missing properties.
    """
    settings: Settings | None = ctx.obj.get("settings")
    if settings is None:
        click.echo(f"Error loading settings: {ctx.obj.get('settings_error')}", err=True)
        ctx.exit(1)

    async def run() -> None:
        client = NotionClient(settings.notion_token)
        try:
            click.echo(f"Fetching database schema: {settings.database_id}")
            db = await client.get_database(settings.database_id)
            existing_props = set(db.get("properties", {}).keys())

            click.echo(f"Found {len(existing_props)} existing properties")

            # Find missing properties
            missing_props = {k: v for k, v in SCHEMA.items() if k not in existing_props}

            if not missing_props:
                click.echo("All properties already exist! Schema is up to date.")
                return

            click.echo(f"\nAdding {len(missing_props)} missing properties:")
            for prop_name in missing_props:
                click.echo(f"  - {prop_name}")

            # Update database
            await client.update_database(settings.database_id, missing_props)
            click.echo("\nSchema initialized successfully!")

        finally:
            await client.close()

    try:
        asyncio.run(run())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@main.command()
@click.option("--dry-run", is_flag=True, help="Preview changes without syncing")
@click.option("--google-only", is_flag=True, help="Only sync Google → Notion")
@click.option("--notion-only", is_flag=True, help="Only sync Notion → Google")
@click.pass_context
def sync(ctx: click.Context, dry_run: bool, google_only: bool, notion_only: bool) -> None:
    """Sync contacts between Google and Notion.

    Default: 2-way sync (Google ↔ Notion)

    Only contacts with a Google ID will sync back to Google.
    Manual Notion entries (without Google ID) are never synced to Google.
    """
    if dry_run:
        click.echo("DRY RUN MODE: No changes will be made")
        click.echo()

    if google_only and notion_only:
        click.echo("Error: Cannot use both --google-only and --notion-only", err=True)
        ctx.exit(1)

    settings: Settings | None = ctx.obj.get("settings")
    if settings is None:
        click.echo(f"Error loading settings: {ctx.obj.get('settings_error')}", err=True)
        ctx.exit(1)

    # Check for refresh token
    if not settings.google_refresh_token:
        click.echo("Error: GOOGLE_REFRESH_TOKEN not set in .env", err=True)
        click.echo("Run 'contacts2notion auth' first to get a refresh token", err=True)
        ctx.exit(1)

    async def run() -> None:
        notion_client = NotionClient(settings.notion_token)
        google_client = GoogleContactsClient(settings)
        syncer = ContactSyncer(notion_client, google_client, settings.database_id)

        try:
            if dry_run:
                click.echo("Dry run not implemented yet - exiting")
                return

            # Determine sync direction
            if notion_only:
                # Notion → Google only
                await syncer.initialize()
                await syncer.sync_to_google()
            elif google_only:
                # Google → Notion only
                await syncer.initialize()
                await syncer.sync_from_google()
            else:
                # Full 2-way sync
                google_stats, notion_stats = await syncer.full_sync()

                # Summary
                click.echo("\n" + "=" * 50)
                click.echo("SYNC COMPLETE")
                click.echo("=" * 50)
                click.echo(f"\nGoogle → Notion:")
                click.echo(f"  Created: {google_stats.created}")
                click.echo(f"  Updated: {google_stats.updated}")
                click.echo(f"  Errors: {len(google_stats.errors)}")
                if google_stats.errors:
                    click.echo("\n  Error details:")
                    for error in google_stats.errors[:5]:  # Show first 5
                        click.echo(f"    - {error}")
                    if len(google_stats.errors) > 5:
                        click.echo(f"    ... and {len(google_stats.errors) - 5} more")

                click.echo(f"\nNotion → Google:")
                click.echo(f"  Updated: {notion_stats.updated}")
                click.echo(f"  Skipped (no Google ID): {notion_stats.skipped}")
                click.echo(f"  Errors: {len(notion_stats.errors)}")
                if notion_stats.errors:
                    click.echo("\n  Error details:")
                    for error in notion_stats.errors[:5]:
                        click.echo(f"    - {error}")
                    if len(notion_stats.errors) > 5:
                        click.echo(f"    ... and {len(notion_stats.errors) - 5} more")

        finally:
            await notion_client.close()
            await google_client.close()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\nSync interrupted by user")
        ctx.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show database statistics."""
    settings: Settings | None = ctx.obj.get("settings")
    if settings is None:
        click.echo(f"Error loading settings: {ctx.obj.get('settings_error')}", err=True)
        ctx.exit(1)

    async def run() -> None:
        client = NotionClient(settings.notion_token)
        try:
            click.echo(f"Database: {settings.database_id}\n")

            # Count contacts
            total = 0
            with_google_id = 0
            with_birthday = 0
            hide_birthday_count = 0

            async for page in client.query_database_all(settings.database_id):
                total += 1
                props = page.get("properties", {})

                # Check Google ID
                google_id_prop = props.get("Google ID", {})
                rich_text = google_id_prop.get("rich_text", [])
                if rich_text and rich_text[0].get("plain_text"):
                    with_google_id += 1

                # Check Birthday
                birthday_prop = props.get("Birthday", {})
                if birthday_prop.get("date"):
                    with_birthday += 1

                # Check Hide Birthday
                hide_birthday_prop = props.get("Hide Birthday", {})
                if hide_birthday_prop.get("checkbox"):
                    hide_birthday_count += 1

            click.echo(f"Total contacts: {total}")
            click.echo(f"  With Google ID: {with_google_id}")
            click.echo(f"  Manual entries: {total - with_google_id}")
            click.echo(f"  With birthday: {with_birthday}")
            click.echo(f"  Hide birthday enabled: {hide_birthday_count}")

        finally:
            await client.close()

    try:
        asyncio.run(run())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


if __name__ == "__main__":
    main()
