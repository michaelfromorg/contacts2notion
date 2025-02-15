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
  updated: number;
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
    updated: 0,
    excluded: 0,
  };

  const parser = new GoogleContactsParser(csvPath);
  const googleContacts = parser.parse();

  const notionClient = new NotionClient();
  const notionContacts = await notionClient.getAllContacts();

  // Create indices for existing Notion contacts
  const notionContactIndex = new Map<string, NotionContact>();
  const notionContactByName = new Map<string, NotionContact>();

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

    const nameLookup = `${contact.firstName.toLowerCase()}-${contact.lastName.toLowerCase()}`;
    notionContactByName.set(nameLookup, contact);
  });

  for (const gContact of googleContacts) {
    if (gContact.excludeFromSync) {
      stats.excluded++;
      continue;
    }

    // Check all possible matching criteria
    const emails = gContact.email.map((e) => e.toLowerCase());
    const phones = gContact.phone.map((p) => p.replace(/\D/g, "")); // Strip non-digits
    const nameLookup = `${gContact.firstName.toLowerCase()}-${gContact.lastName.toLowerCase()}`;

    // Find existing contact
    let existingContact: NotionContact | undefined;
    let matchType: "email" | "phone" | "name" | undefined;

    // Check email matches
    for (const email of emails) {
      if (notionContactIndex.has(email)) {
        existingContact = notionContactIndex.get(email);
        matchType = "email";
        stats.duplicates.email++;
        break;
      }
    }

    // Check phone matches
    if (!existingContact) {
      for (const phone of phones) {
        if (notionContactIndex.has(phone)) {
          existingContact = notionContactIndex.get(phone);
          matchType = "phone";
          stats.duplicates.phone++;
          break;
        }
      }
    }

    // Check name match as last resort
    if (!existingContact && notionContactByName.has(nameLookup)) {
      existingContact = notionContactByName.get(nameLookup);
      matchType = "name";
      stats.duplicates.name++;
    }

    if (!options.dryRun) {
      if (existingContact && existingContact.id) {
        // Update existing contact
        const updatedContact: NotionContact = {
          firstName: gContact.firstName,
          lastName: gContact.lastName,
          company: gContact.organization?.name,
          title: gContact.organization?.title,
          primaryEmail: gContact.email[0],
          secondaryEmail: gContact.email[1],
          primaryPhone: gContact.phone[0],
          secondaryPhone: gContact.phone[1],
          birthday: gContact.birthday,
          website: gContact.website?.[0],
          lastSyncedAt: new Date().toISOString(),
        };

        if (options.verbose) {
          console.log(
            `Updating contact: ${updatedContact.firstName} ${updatedContact.lastName}`
          );
        }

        await notionClient.updateContact(existingContact.id, updatedContact);
        stats.updated++;
      } else {
        // Add new contact
        const newContact: NotionContact = {
          firstName: gContact.firstName,
          lastName: gContact.lastName,
          company: gContact.organization?.name,
          title: gContact.organization?.title,
          primaryEmail: gContact.email[0],
          secondaryEmail: gContact.email[1],
          primaryPhone: gContact.phone[0],
          secondaryPhone: gContact.phone[1],
          birthday: gContact.birthday,
          website: gContact.website?.[0],
          lastSyncedAt: new Date().toISOString(),
        };

        if (options.verbose) {
          console.log(
            `Adding new contact: ${newContact.firstName} ${newContact.lastName}`
          );
        }

        await notionClient.createContact(newContact);
        stats.added++;
      }
    } else if (options.verbose) {
      console.log(
        existingContact
          ? `Would update: ${gContact.firstName} ${gContact.lastName}`
          : `Would add: ${gContact.firstName} ${gContact.lastName}`
      );
    }
  }

  console.log("Sync completed:");
  console.log(`- Added ${stats.added} new contacts`);
  console.log(`- Updated ${stats.updated} existing contacts`);
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
  // await flush();
  await syncContacts("./data/contacts.csv", { verbose: true });
}

main();
