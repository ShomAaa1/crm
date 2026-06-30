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

// === Корзина ===

export interface CartItem {
  id: string;
  part_id: string;
  article: string;
  name: string;
  manufacturer: string | null;
  unit: string;
  price: string;
  quantity: number;
  line_total: string;
  in_stock: boolean;
  stock_quantity: number;
}

export interface CartSummary {
  items: CartItem[];
  items_count: number;
  total: string;
}

// === Заявки ===

export type RequestStatus =
  | "new"
  | "in_progress"
  | "cp_sent"
  | "accepted"
  | "rejected"
  | "revision_needed"
  | "closed_success"
  | "closed_fail"
  | "cancelled";

export interface RequestItem {
  id: string;
  part_id: string | null;
  article: string | null;
  name: string | null;
  description: string | null;
  quantity: number;
  price_at_moment: string | null;
  line_total: string | null;
}

export interface RequestListItem {
  id: string;
  request_number: string;
  status: RequestStatus;
  client_id: string;
  client_company: string | null;
  manager_id: string | null;
  manager_name: string | null;
  items_count: number;
  total: string;
  comment: string | null;
  created_at: string;
  taken_at: string | null;
  sla_deadline: string | null;
  closed_at: string | null;
  sla_overdue: boolean;
}

export interface ClientFinance {
  inn: string | null;
  kpp: string | null;
  ogrn: string | null;
  credit_limit: string;
  debt: string;
  phone: string | null;
  email: string | null;
}

export interface RequestDetail extends RequestListItem {
  items: RequestItem[];
  client: ClientFinance | null;
}

// === Коммерческие предложения ===

export type CPStatus = "draft" | "sent" | "accepted" | "rejected" | "expired";

export interface CPItem {
  id: string;
  part_id: string | null;
  article: string | null;
  name: string;
  quantity: number;
  unit_price: string;
  discount_percent: string;
  total_price: string;
}

export interface CPListItem {
  id: string;
  cp_number: string;
  request_id: string;
  request_number: string | null;
  client_company: string | null;
  manager_id: string;
  manager_name: string | null;
  status: CPStatus;
  valid_until: string | null;
  total_amount: string | null;
  version: number;
  created_at: string;
  sent_at: string | null;
}

export interface CPDetail extends CPListItem {
  payment_terms: string | null;
  delivery_terms: string | null;
  items: CPItem[];
}

// === Заказы ===

export type OrderStatus =
  | "created"
  | "confirmed"
  | "shipped"
  | "delivered"
  | "cancelled";

export interface OrderItem {
  id: string;
  part_id: string;
  article: string | null;
  name: string | null;
  quantity: number;
  unit_price: string;
  total_price: string;
}

export interface OrderListItem {
  id: string;
  order_number: string;
  status: OrderStatus;
  client_id: string;
  client_company: string | null;
  manager_id: string | null;
  manager_name: string | null;
  cp_id: string | null;
  cp_number: string | null;
  items_count: number;
  total_amount: string;
  delivery_address: string | null;
  tracking_number: string | null;
  created_at: string;
  delivered_at: string | null;
}

export interface OrderDetail extends OrderListItem {
  payment_terms: string | null;
  items: OrderItem[];
}

// === Уведомления ===

export type NotificationType = "info" | "warning" | "task" | "system";

export interface NotificationItem {
  id: string;
  type: NotificationType;
  title: string;
  message: string | null;
  is_read: boolean;
  related_entity_type: string | null;
  related_entity_id: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationSummary {
  items: NotificationItem[];
  unread_count: number;
}

// === Дашборд ===

export interface CounterItem {
  label: string;
  value: number;
}

export interface RevenuePoint {
  date: string; // ISO YYYY-MM-DD
  value: number;
}

export interface ConversionPoint {
  month: string; // YYYY-MM
  conversion: number;
}

export interface FunnelStage {
  stage: string;
  value: number;
  conversion_pct: number | null;
}

export interface ManagerScore {
  manager_name: string;
  revenue: number;
  deals_count: number;
}

export type PeriodPreset = "day" | "week" | "month" | "quarter" | "year";

export interface DashboardSummary {
  // Период
  period_label: string;
  period_days: number;
  period_start: string; // YYYY-MM-DD
  period_end: string; // YYYY-MM-DD

  // Snapshot
  requests_by_status: CounterItem[];
  proposals_by_status: CounterItem[];
  orders_by_status: CounterItem[];
  sales_funnel: FunnelStage[];
  active_requests: number;
  total_clients: number;
  total_managers: number;

  // За выбранный период
  revenue_period: string;
  deals_won: number;
  avg_deal_size: string;
  cp_conversion: number;
  revenue_by_day: RevenuePoint[];
  previous_revenue_by_day: RevenuePoint[];
  manager_leaderboard: ManagerScore[];

  // Дельты к эквивалентному предыдущему периоду
  revenue_delta_pct: number | null;
  conversion_delta_pct: number | null;
  deals_won_delta_pct: number | null;
  avg_deal_size_delta_pct: number | null;

  // Тренд за последние 6 месяцев
  conversion_by_month: ConversionPoint[];
}
