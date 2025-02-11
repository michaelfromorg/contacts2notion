import dotenv from "dotenv";

dotenv.config();

export const config = {
  notion: {
    auth: process.env.NOTION_API_KEY,
    databaseId: process.env.NOTION_DATABASE_ID,
  },
  syncLabel: "ExcludeFromNotion", // Label to use in Google Contacts
};
