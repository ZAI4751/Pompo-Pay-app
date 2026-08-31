/** Admin-portal view of a Pompo staff/user account (app/models/user.py). */

export interface StaffUser {
  id: string;
  email: string;
  full_name: string;
  role_id: string;
  role_name: string;
  merchant_id: string | null;
  merchant_name: string | null;
  branch_id: string | null;
  branch_name: string | null;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}
