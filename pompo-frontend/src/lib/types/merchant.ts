/** Mirrors app/models/organization.py (Merchant, Branch, Till). */

export type MerchantStatus = "active" | "inactive";

export interface Merchant {
  id: string;
  name: string;
  legal_name: string | null;
  contact_email: string;
  contact_phone: string;
  is_active: boolean;
  branch_count: number;
  created_at: string;
}

export interface Branch {
  id: string;
  merchant_id: string;
  merchant_name: string;
  name: string;
  address: string | null;
  is_active: boolean;
  till_count: number;
}

export interface Till {
  id: string;
  branch_id: string;
  branch_name: string;
  code: string;
  name: string;
  is_active: boolean;
}
