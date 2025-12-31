"""Quick script to check database schema."""

import asyncio

from contacts2notion.config import get_settings
from contacts2notion.notion.client import NotionClient


async def main():
    settings = get_settings()
    client = NotionClient(settings.notion_token)

    try:
        db = await client.get_database(settings.database_id)
        props = db.get("properties", {})

        print(f"Database has {len(props)} properties:\n")
        for prop_name, prop_def in props.items():
            prop_type = prop_def.get("type", "unknown")
            print(f"  {prop_name}: {prop_type}")

        # Also check first contact to see actual data
        print("\n" + "=" * 50)
        print("Sample contact (first entry):")
        print("=" * 50 + "\n")

        result = await client.query_database(settings.database_id, page_size=1)
        if result.get("results"):
            page = result["results"][0]
            page_props = page.get("properties", {})

            for prop_name, prop_value in page_props.items():
                prop_type = prop_value.get("type")
                if prop_type == "title":
                    title_list = prop_value.get("title", [])
                    value = title_list[0].get("plain_text", "") if title_list else ""
                elif prop_type == "rich_text":
                    rich_text = prop_value.get("rich_text", [])
                    value = rich_text[0].get("plain_text", "") if rich_text else ""
                elif prop_type == "email":
                    value = prop_value.get("email", "")
                elif prop_type == "phone_number":
                    value = prop_value.get("phone_number", "")
                elif prop_type == "date":
                    date_obj = prop_value.get("date")
                    value = date_obj.get("start", "") if date_obj else ""
                elif prop_type == "checkbox":
                    value = prop_value.get("checkbox", False)
                elif prop_type == "url":
                    value = prop_value.get("url", "")
                elif prop_type == "select":
                    select_obj = prop_value.get("select")
                    value = select_obj.get("name", "") if select_obj else ""
                elif prop_type == "multi_select":
                    options = prop_value.get("multi_select", [])
                    value = [opt.get("name", "") for opt in options]
                else:
                    value = f"<{prop_type}>"

                if value:
                    print(f"  {prop_name}: {value}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
