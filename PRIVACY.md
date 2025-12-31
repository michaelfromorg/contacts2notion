# Privacy Policy for contacts2notion

**Last Updated: December 31, 2024**

## Overview

contacts2notion is a personal contact management tool that syncs your Google Contacts with your Notion database. This privacy policy explains how your data is handled.

## What Data We Access

contacts2notion accesses the following data from your Google account:
- Contact names (first and last)
- Email addresses
- Phone numbers
- Birthdays
- Organizations (company, job title, department)
- Physical addresses
- Website URLs

This data is accessed through the Google People API using OAuth 2.0 authentication.

## How We Use Your Data

contacts2notion:
- **Reads** your Google Contacts data via the Google People API
- **Syncs** this data to your personal Notion database
- **Updates** Google Contacts with information you add in Notion (if fields are empty in Google)
- **Stores** all data exclusively in your own Notion workspace

We do **NOT**:
- Store your data on any third-party servers
- Share your data with anyone
- Sell or monetize your data in any way
- Use your data for analytics or tracking

## Data Storage

All contact data is stored in:
1. **Your Google Contacts** - Managed by Google's privacy policy
2. **Your Notion Database** - Managed by Notion's privacy policy

contacts2notion acts only as a sync tool between these two services. No contact data is stored by contacts2notion itself.

## Authentication & Security

- OAuth 2.0 tokens are stored locally in your `.env` file or GitHub repository secrets
- Refresh tokens allow the app to sync without repeated authorization
- You can revoke access at any time through [Google Account Permissions](https://myaccount.google.com/permissions)

## Third-Party Services

contacts2notion interacts with:
- **Google People API** - To read and update your contacts (Privacy Policy: https://policies.google.com/privacy)
- **Notion API** - To sync contacts to your database (Privacy Policy: https://www.notion.so/Privacy-Policy-3468d120cf614d4c9014c09f6adc9091)

## Data Retention

- Contact data is retained in your Google Contacts and Notion database as long as you choose to keep it
- Deleting the Notion integration or revoking Google permissions will stop all data access
- No data is retained by contacts2notion after you stop using it

## User Rights

You have the right to:
- Access all your data (it's in your Google Contacts and Notion)
- Export your data from Google or Notion at any time
- Delete your data by removing it from Google Contacts or Notion
- Revoke contacts2notion's access to Google Contacts at any time

## Open Source

contacts2notion is open source software. You can:
- Review all source code at https://github.com/michaelfromorg/contacts2notion
- Verify exactly what data is accessed and how it's used
- Self-host the application for complete control

## Children's Privacy

contacts2notion is not intended for use by children under 13. We do not knowingly collect data from children.

## Changes to This Policy

We may update this privacy policy from time to time. Changes will be reflected in the "Last Updated" date above and documented in the project's version history.

## Contact

For questions or concerns about this privacy policy, please:
- Open an issue at https://github.com/michaelfromorg/contacts2notion/issues
- Contact the developer at https://michaeldemar.co

## Consent

By using contacts2notion, you consent to this privacy policy and the handling of your data as described herein.

---

**Note:** This is a personal, self-hosted tool. When you run contacts2notion, all operations happen locally or between Google and Notion APIs directly. There are no intermediary servers collecting or processing your data.
