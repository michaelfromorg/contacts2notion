export interface GoogleContact {
  firstName: string;
  lastName: string;
  organization?: {
    name: string;
    title: string;
    department?: string;
  };
  email: string[];
  phone: string[];
  birthday?: string;
  address?: {
    formatted?: string;
    street?: string;
    city?: string;
    region?: string;
    postalCode?: string;
    country?: string;
  };
  website?: string[];
  excludeFromSync?: boolean;
}

export interface NotionContact {
  id?: string;
  firstName: string;
  lastName: string;
  company?: string;
  department?: string;
  title?: string;
  primaryEmail?: string;
  secondaryEmail?: string;
  primaryPhone?: string;
  secondaryPhone?: string;
  birthday?: string;
  address?: string;
  website?: string;
  lastSyncedAt: string;
}
