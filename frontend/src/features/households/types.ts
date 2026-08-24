export type HouseholdRole = "owner" | "admin" | "member";

export interface Household {
  id: string;
  name: string;
  created_by: string;
  my_role: HouseholdRole | null;
  created_at: string;
  updated_at: string;
}

export interface HouseholdMembership {
  id: string;
  user: {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    date_joined: string;
  };
  role: HouseholdRole;
  created_at: string;
}
