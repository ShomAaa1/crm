export type UserRole = "client" | "manager" | "head" | "admin";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  full_name: string;
  phone: string | null;
  is_active: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  errors?: Array<{ loc: (string | number)[]; msg: string; type: string }>;
}

// === Каталог ===

export interface Category {
  id: string;
  name: string;
  slug: string;
  parent_id: string | null;
}

export interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[];
}

export interface Part {
  id: string;
  article: string;
  name: string;
  description: string | null;
  manufacturer: string | null;
  category_id: string | null;
  price: string; // Decimal приходит строкой
  stock_quantity: number;
  unit: string;
  is_active: boolean;
}

export interface PriceHistoryEntry {
  id: string;
  old_price: string | null;
  new_price: string;
  changed_by: string | null;
  changed_at: string;
}

export interface CsvImportResult {
  created: number;
  updated: number;
  price_changes: number;
  errors: Array<{ line: number; reason: string }>;
}
