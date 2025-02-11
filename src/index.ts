import { GoogleContactsParser } from "./googleContactsParser.js";
import { NotionClient } from "./notionClient.js";
import { NotionContact } from "./types.js";

interface SyncStats {
  duplicates: {
    email: number;
    phone: number;
    name: number;
  };
  added: number;
  excluded: number;
}

interface SyncOptions {
  dryRun?: boolean;
  verbose?: boolean;
}

async function syncContacts(
  csvPath: string,
  options: SyncOptions = {}
): Promise<SyncStats> {
  const stats: SyncStats = {
    duplicates: {
      email: 0,
      phone: 0,
      name: 0,
    },
    added: 0,
    excluded: 0,
  };
  // Parse Google Contacts
  const parser = new GoogleContactsParser(csvPath);
  const googleContacts = parser.parse();

  // Get existing Notion contacts
  const notionClient = new NotionClient();
  const notionContacts = await notionClient.getAllContacts();

  // Create an index of existing Notion contacts for faster lookup
  const notionContactIndex = new Map<string, NotionContact>();

  // Index by all email addresses and phone numbers
  notionContacts.forEach((contact) => {
    if (contact.primaryEmail)
      notionContactIndex.set(contact.primaryEmail.toLowerCase(), contact);
    if (contact.secondaryEmail)
      notionContactIndex.set(contact.secondaryEmail.toLowerCase(), contact);
    if (contact.primaryPhone)
      notionContactIndex.set(contact.primaryPhone.replace(/\D/g, ""), contact);
    if (contact.secondaryPhone)
      notionContactIndex.set(
        contact.secondaryPhone.replace(/\D/g, ""),
        contact
      );

    // Also index by name combination for cases without email/phone
    const nameLookup = `${contact.firstName.toLowerCase()}-${contact.lastName.toLowerCase()}`;
    notionContactIndex.set(nameLookup, contact);
  });

  // Find contacts to add to Notion
  const contactsToAdd = googleContacts.filter((gContact) => {
    if (gContact.excludeFromSync) return false;

    // Check all possible matching criteria
    const emails = gContact.email.map((e) => e.toLowerCase());
    const phones = gContact.phone.map((p) => p.replace(/\D/g, "")); // Strip non-digits
    const nameLookup = `${gContact.firstName.toLowerCase()}-${gContact.lastName.toLowerCase()}`;

    // Check if any identifier matches an existing contact
    return ![...emails, ...phones, nameLookup].some((id) =>
      notionContactIndex.has(id)
    );
  });

  // Add new contacts to Notion
  if (!options.dryRun) {
    for (const contact of contactsToAdd) {
      console.log("Adding", contact);
      await notionClient.createContact({
        firstName: contact.firstName,
        lastName: contact.lastName,
        company: contact.organization?.name,
        title: contact.organization?.title,
        primaryEmail: contact.email[0],
        secondaryEmail: contact.email[1],
        primaryPhone: contact.phone[0],
        secondaryPhone: contact.phone[1],
        lastSyncedAt: new Date().toISOString(),
      });
    }
  } else {
    contactsToAdd.forEach(console.log);
  }

  stats.added = contactsToAdd.length;

  console.log("Sync completed:");
  console.log(`- Added ${stats.added} new contacts`);
  console.log(`- Found ${stats.duplicates.email} email matches`);
  console.log(`- Found ${stats.duplicates.phone} phone matches`);
  console.log(`- Found ${stats.duplicates.name} name matches`);
  console.log(`- Excluded ${stats.excluded} contacts by label`);

  return stats;
}

async function flush() {
  const notionClient = new NotionClient();
  await notionClient.flushDatabase();
}

// Example usage
// syncContacts("./data/contacts.csv");

async function main() {
  await flush();
  await syncContacts("./data/contacts.csv", { verbose: true });
}

main();
