import { Client } from "@notionhq/client";
import { NotionContact } from "./types.js";
import { config } from "./config.js";

export class NotionClient {
  private notion: Client;

  constructor() {
    this.notion = new Client({ auth: config.notion.auth });
  }

  async getAllContacts(): Promise<NotionContact[]> {
    if (!config.notion.databaseId) {
      throw new Error("Notion database ID is not set.");
    }
    const response = await this.notion.databases.query({
      database_id: config.notion.databaseId,
    });

    return response.results.map((page) => this.parseNotionPage(page));
  }

  /**
   * Deletes all pages from the Notion database
   * @param {boolean} dryRun If true, only logs pages that would be deleted without actually deleting them
   * @returns {Promise<number>} Number of pages deleted
   */
  async flushDatabase(dryRun: boolean = false): Promise<number> {
    if (!config.notion.databaseId) {
      throw new Error("Notion database ID is not set.");
    }

    let deletedCount = 0;
    let hasMore = true;
    let startCursor: string | undefined = undefined;

    while (hasMore) {
      const response = await this.notion.databases.query({
        database_id: config.notion.databaseId,
        start_cursor: startCursor,
        page_size: 100, // Maximum allowed by Notion API
      });

      if (dryRun) {
        console.log(`Would delete ${response.results.length} pages...`);
        deletedCount += response.results.length;
      } else {
        for (const page of response.results) {
          try {
            await this.notion.pages.update({
              page_id: page.id,
              archived: true,
            });
            deletedCount++;

            // Add a small delay to avoid rate limiting
            await new Promise((resolve) => setTimeout(resolve, 100));
          } catch (error) {
            console.error(`Failed to delete page ${page.id}:`, error);
          }
        }
      }

      hasMore = response.has_more;
      startCursor = response.next_cursor || undefined;
    }

    if (dryRun) {
      console.log(
        `Dry run complete. Would have deleted ${deletedCount} pages.`
      );
    } else {
      console.log(`Successfully deleted ${deletedCount} pages.`);
    }

    return deletedCount;
  }

  private propertyMap = {
    firstName: "First_Name",
    lastName: "Last_Name",
    company: "Company",
    department: "Department",
    title: "Job_Title",
    primaryEmail: "Primary_Email",
    secondaryEmail: "Secondary_Email",
    primaryPhone: "Primary_Phone",
    secondaryPhone: "Secondary_Phone",
    birthday: "Birthday",
    address: "Address",
    website: "Website",
    lastSyncedAt: "Last_Synced",
  };

  private formatContactForNotion(contact: NotionContact): any {
    return {
      parent: {
        database_id: config.notion.databaseId,
      },
      properties: {
        "First Name": {
          type: "title",
          title: [
            {
              type: "text",
              text: {
                content: contact.firstName || "",
              },
            },
          ],
        },
        "Last Name": {
          type: "rich_text",
          rich_text: [
            {
              type: "text",
              text: {
                content: contact.lastName || "",
              },
            },
          ],
        },
        Company: contact.company
          ? {
              type: "rich_text",
              rich_text: [
                {
                  type: "text",
                  text: {
                    content: contact.company,
                  },
                },
              ],
            }
          : { type: "rich_text", rich_text: [] },
        "Job Title": contact.title
          ? {
              type: "rich_text",
              rich_text: [
                {
                  type: "text",
                  text: {
                    content: contact.title,
                  },
                },
              ],
            }
          : { type: "rich_text", rich_text: [] },
        "Primary Email": contact.primaryEmail
          ? {
              type: "email",
              email: contact.primaryEmail,
            }
          : { type: "email", email: null },
        "Secondary Email": contact.secondaryEmail
          ? {
              type: "email",
              email: contact.secondaryEmail,
            }
          : { type: "email", email: null },
        "Primary Phone": contact.primaryPhone
          ? {
              type: "phone_number",
              phone_number: contact.primaryPhone,
            }
          : { type: "phone_number", phone_number: null },
        "Secondary Phone": contact.secondaryPhone
          ? {
              type: "phone_number",
              phone_number: contact.secondaryPhone,
            }
          : { type: "phone_number", phone_number: null },
        Birthday: contact.birthday
          ? {
              type: "date",
              date: { start: contact.birthday },
            }
          : { type: "date", date: null },
        "Last Synced": {
          type: "date",
          date: { start: new Date().toISOString() },
        },
      },
    };
  }

  async createContact(contact: NotionContact): Promise<void> {
    if (!config.notion.databaseId) {
      throw new Error("Notion database ID is not set.");
    }

    const formattedContact = this.formatContactForNotion(contact);
    await this.notion.pages.create(formattedContact);
  }

  private parseNotionPage(page: any): NotionContact {
    return {
      id: page.id,
      firstName: page.properties["First Name"]?.title?.[0]?.text?.content || "",
      lastName:
        page.properties["Last Name"]?.rich_text?.[0]?.text?.content || "",
      company: page.properties["Company"]?.rich_text?.[0]?.text?.content,
      title: page.properties["Job Title"]?.rich_text?.[0]?.text?.content,
      primaryEmail: page.properties["Primary Email"]?.email,
      secondaryEmail: page.properties["Secondary Email"]?.email,
      primaryPhone: page.properties["Primary Phone"]?.phone_number,
      secondaryPhone: page.properties["Secondary Phone"]?.phone_number,
      birthday: page.properties["Birthday"]?.date?.start,
      lastSyncedAt: page.properties["Last Synced"]?.date?.start,
    };
  }
}
