/**
 * Mirrors app/schemas/organization.py MerchantResponse / BranchResponse.
 * branch_count / till_count / created_at are not on the live contract.
 */

export interface Merchant {
  id: string;
  name: string;
  legal_name: string | null;
  registration_number: string | null;
  contact_email: string;
  contact_phone: string;
  is_active: boolean;
}

export interface MerchantCreate {
  name: string;
  legal_name?: string | null;
  registration_number?: string | null;
  contact_email: string;
  contact_phone: string;
}

export interface MerchantUpdate {
  name?: string;
  legal_name?: string | null;
  registration_number?: string | null;
  contact_email?: string;
  contact_phone?: string;
  is_active?: boolean;
}

export interface Branch {
  id: string;
  merchant_id: string;
  name: string;
  address: string | null;
  is_active: boolean;
}

export interface BranchCreate {
  name: string;
  address?: string | null;
}

export interface BranchUpdate {
  name?: string;
  address?: string | null;
  is_active?: boolean;
}

export interface Till {
  id: string;
  branch_id: string;
  merchant_id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface TillCreate {
  code: string;
  name: string;
}

export interface TillUpdate {
  name?: string;
  is_active?: boolean;
}
