// Money values are always decimal strings from the API (e.g. "1500000.00"). Never parse to float for maths.
export type Money = string;

export type VerificationLevel = "unverified" | "phone_verified" | "identity_verified" | "business_verified";
export type Condition = "brand_new" | "foreign_used" | "nigerian_used" | "refurbished";
export type ProductStatus = "draft" | "pending_review" | "active" | "sold" | "inactive" | "rejected";
export type OrderStatus =
  | "pending_payment"
  | "payment_confirmed"
  | "funds_safeguarded"
  | "awaiting_seller"
  | "processing"
  | "dispatched"
  | "delivered"
  | "awaiting_buyer_confirmation"
  | "completed"
  | "disputed"
  | "refund_pending"
  | "refunded"
  | "cancelled";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface SellerSummary {
  id: string;
  store_name: string;
  slug: string;
  verification_level: VerificationLevel;
  is_premium: boolean;
}

export interface User {
  id: string;
  email: string;
  phone: string | null;
  full_name: string;
  role: "user" | "admin" | "super_admin";
  admin_permissions: string[];
  email_verified: boolean;
  phone_verified: boolean;
  two_factor_enabled: boolean;
  created_at: string;
  avatar_url: string | null;
  google_linked?: boolean;
  state: string | null;
  city: string | null;
  seller: SellerSummary | null;
  account_type?: "customer" | "staff";
  admin_role_name?: string | null;
}

export interface SellerCard {
  id: string;
  store_name: string;
  slug: string;
  logo_url: string | null;
  verification_level: VerificationLevel;
  is_premium: boolean;
  rating_avg: Money;
  rating_count: number;
  state: string | null;
  city: string | null;
  member_since: string;
  completed_sales: number;
  whatsapp_available: boolean;
  phone_available: boolean;
}

export interface CategoryRef {
  id: string;
  name: string;
  slug: string;
}

export interface Category extends CategoryRef {
  icon: string | null;
  description: string | null;
  listing_count: number;
  parent_id: string | null;
  is_active: boolean;
  sort_order: number;
  children: Category[];
}

export interface ProductCard {
  id: string;
  slug: string;
  title: string;
  price: Money;
  currency: string;
  negotiable: boolean;
  condition: Condition;
  state: string;
  city: string;
  thumb_url: string | null;
  image_count: number;
  is_featured: boolean;
  sponsored?: boolean;
  created_at: string;
  seller: SellerCard;
  category: CategoryRef;
  protected_checkout_enabled: boolean;
  bnpl_enabled: boolean;
  is_favourite: boolean;
}

export interface DeliveryOption {
  type: "pickup" | "seller_delivery" | "courier";
  label: string;
  fee: Money;
  eta_days: number;
}

export interface ProductImage {
  id: string;
  url: string;
  thumb_url: string;
  width: number;
  height: number;
  position: number;
}

export interface ProductDetail extends ProductCard {
  description: string;
  brand: string | null;
  model: string | null;
  quantity: number;
  status: ProductStatus;
  images: ProductImage[];
  delivery_options: DeliveryOption[];
  views_count: number;
  favourites_count: number;
  published_at: string | null;
  updated_at: string;
  subcategory: CategoryRef | null;
  category_path: CategoryRef[];
}

export interface SellerProductDetail extends ProductDetail {
  enquiries_count: number;
  contact_clicks: number;
  rejection_reason: string | null;
}

export interface SellerProductRow extends ProductCard {
  status: ProductStatus;
  quantity: number;
  views_count: number;
  enquiries_count: number;
  contact_clicks: number;
  favourites_count: number;
  rejection_reason: string | null;
}

export interface Storefront extends SellerCard {
  description: string | null;
  banner_url: string | null;
  business_hours: string | null;
  website: string | null;
  active_listings: number;
}

export interface Offer {
  id: string;
  made_by: "buyer" | "seller";
  amount: Money;
  note: string | null;
  status: string;
  expires_at: string;
  created_at: string;
}

export interface Negotiation {
  id: string;
  status: "open" | "accepted" | "rejected" | "cancelled" | "expired" | "converted";
  role: "buyer" | "seller";
  product: { id: string; title: string; slug: string; price: Money; thumb_url: string | null; status: string; bnpl_enabled: boolean };
  seller: { id: string; store_name: string; slug: string };
  listed_price: Money;
  agreed_price: Money | null;
  accepted_at: string | null;
  checkout_expires_at: string | null;
  conversation_id: string | null;
  awaiting: "buyer" | "seller" | null;
  your_turn: boolean;
  offers: Offer[];
  created_at: string;
  updated_at: string;
}

export interface OrderItem {
  product_id: string;
  title: string;
  image_url: string | null;
  unit_price: Money;
  listed_price: Money;
  quantity: number;
  line_total: Money;
}

export interface Order {
  id: string;
  order_number: string;
  status: OrderStatus;
  payment_method: "full" | "bnpl";
  role: "buyer" | "seller" | "admin";
  currency: string;
  subtotal: Money;
  delivery_fee: Money;
  protection_fee: Money;
  total: Money;
  items: OrderItem[];
  seller: { id: string; store_name: string; slug: string };
  buyer: { id: string; name: string };
  created_at: string;
  paid_at: string | null;
  completed_at: string | null;
  expires_at: string | null;
  negotiated: boolean;
  seller_earnings?: Money;
  platform_fees?: Money;
}

export interface OrderDetail extends Order {
  delivery_option: DeliveryOption;
  delivery_address: Record<string, string> | null;
  buyer_note: string | null;
  cancellation_reason: string | null;
  delivery: {
    status: string;
    method: string;
    carrier: string | null;
    tracking_reference: string | null;
    tracking_url: string | null;
    evidence_urls: string[];
    dispatched_at: string | null;
    delivered_at: string | null;
    updates: { at: string; status: string; note: string }[];
  } | null;
  escrow: {
    status: OrderStatus;
    funded_at: string | null;
    release_eligible_at: string | null;
    released_at: string | null;
    refunded_at: string | null;
    timeline: { from: string | null; to: string; actor: string; note: string | null; at: string }[];
  };
  payment: { reference: string; status: string; purpose: string; amount: Money; authorization_url: string | null } | null;
  disputes: {
    id: string;
    status: string;
    reason: string;
    opened_by: string;
    description: string;
    resolution_notes: string | null;
    created_at: string;
    messages: { author_role: string; body: string; evidence_urls: string[]; created_at: string }[];
  }[];
  refunds: { id: string; amount: Money; status: string; reason: string; created_at: string; completed_at: string | null }[];
  actions: string[];
  financing?: Record<string, string | null> | null;
}

export interface Notification {
  id: string;
  event_type: string;
  title: string;
  body: string;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export interface Review {
  id: string;
  rating: number;
  title: string | null;
  comment: string | null;
  reviewer: string;
  is_verified_purchase: boolean;
  seller_reply: string | null;
  product_id: string | null;
  created_at: string;
}

export interface FinancingOption {
  tenor_months: number;
  down_payment: Money;
  financed_amount: Money;
  financing_charge: Money;
  total_payable: Money;
  monthly_installment: Money;
  schedule: { sequence: number; due_date: string; amount: Money }[];
  apr_disclosure: string;
}

export interface Plan {
  id: string;
  code: string;
  name: string;
  price: Money;
  interval_days: number;
  featured_listing_quota: number;
  features: string[];
}

export interface HomeFeed {
  featured: ProductCard[];
  trending: ProductCard[];
  recent: ProductCard[];
  premium: ProductCard[];
  verified_sellers: SellerCard[];
  premium_sellers: SellerCard[];
}

export interface Facets {
  total: number;
  price_ranges: { min: number | null; max: number | null; count: number }[];
  conditions: Partial<Record<Condition, number>>;
  brands: { name: string; count: number }[];
  flags: { verified_only: number; premium_only: number; negotiable: number; bnpl: number; protected: number; with_photos: number };
  categories: {
    parent: { slug: string; name: string; count: number } | null;
    current: string | null;
    items: { slug: string; name: string; count: number }[];
  };
}
