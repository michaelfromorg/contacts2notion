import { parse } from "csv-parse/sync";
import { readFileSync } from "fs";
import { GoogleContact } from "./types.js";
import { config } from "./config.js";

export class GoogleContactsParser {
  private rawContacts: any[];

  constructor(csvPath: string) {
    const fileContent = readFileSync(csvPath, "utf-8");
    this.rawContacts = parse(fileContent, {
      columns: true,
      skip_empty_lines: true,
    });
  }

  parse(): GoogleContact[] {
    return this.rawContacts
      .filter(
        (contact) =>
          contact["First Name"]?.trim() || contact["Last Name"]?.trim()
      )
      .map((contact) => ({
        firstName: contact["Middle Name"]
          ? `${contact["First Name"]?.trim() || ""} ${contact[
              "Middle Name"
            ]?.trim()}`
          : contact["First Name"]?.trim() || "",
        lastName: contact["Last Name"]?.trim() || "",
        organization: {
          name: contact["Organization Name"]?.trim() || "",
          title: contact["Organization Title"]?.trim() || "",
          department: contact["Organization Department"]?.trim() || undefined,
        },
        email: this.parseEmails(contact),
        phone: this.parsePhones(contact),
        birthday: this.parseBirthday(contact["Birthday"]?.trim()),
        address: this.parseAddress(contact),
        website: this.parseWebsites(contact),
        excludeFromSync: this.checkExcludeLabel(contact),
      }));
  }

  private parseEmails(contact: any): string[] {
    const emails: string[] = [];
    for (let i = 1; i <= 4; i++) {
      const email = contact[`E-mail ${i} - Value`];
      if (email) emails.push(email?.trim());
    }
    return emails;
  }

  private parsePhones(contact: any): string[] {
    const phones: string[] = [];
    for (let i = 1; i <= 2; i++) {
      const phone = contact[`Phone ${i} - Value`];
      if (phone) phones.push(phone?.trim());
    }
    return phones;
  }

  private parseBirthday(birthday: string): string | undefined {
    if (!birthday) return undefined;

    // Handle partial dates like '--07-01'
    if (birthday.startsWith("--")) {
      // Use a placeholder year that's clearly artificial
      return `1900${birthday.substring(2)}`;
    }

    if (birthday.length !== 10) {
      console.warn("Expected birthday, but got:", birthday);
      return undefined;
    }

    return birthday;
  }

  private parseAddress(contact: any): GoogleContact["address"] | undefined {
    // Return undefined if no address components exist
    if (
      !contact["Address 1 - Formatted"] &&
      !contact["Address 1 - Street"] &&
      !contact["Address 1 - City"] &&
      !contact["Address 1 - Region"] &&
      !contact["Address 1 - Postal Code"] &&
      !contact["Address 1 - Country"]
    ) {
      return undefined;
    }

    return {
      formatted: contact["Address 1 - Formatted"]?.trim(),
      street: contact["Address 1 - Street"]?.trim(),
      city: contact["Address 1 - City"]?.trim(),
      region: contact["Address 1 - Region"]?.trim(),
      postalCode: contact["Address 1 - Postal Code"]?.trim(),
      country: contact["Address 1 - Country"]?.trim(),
    };
  }

  private parseWebsites(contact: any): string[] {
    const websites: string[] = [];
    if (contact["Website 1 - Value"]) {
      websites.push(contact["Website 1 - Value"]?.trim());
    }
    return websites;
  }

  private checkExcludeLabel(contact: any): boolean {
    return contact["Labels"]?.includes(config.syncLabel) || false;
  }
}
