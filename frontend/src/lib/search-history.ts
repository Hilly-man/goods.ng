import type { ProductCard } from "./types";

const SEARCHES_KEY = "gng_recent_searches";
const VIEWS_KEY = "gng_recently_viewed";
const SEARCH_LIMIT = 8;
const VIEW_LIMIT = 12;

function readList<T>(key: string, isItem: (value: unknown) => value is T): T[] {
  if (typeof window === "undefined") return [];
  try {
    const stored: unknown = JSON.parse(localStorage.getItem(key) ?? "[]");
    return Array.isArray(stored) ? stored.filter(isItem) : [];
  } catch {
    return [];
  }
}

function isSearch(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isProductCard(value: unknown): value is ProductCard {
  if (!value || typeof value !== "object") return false;
  const product = value as Partial<ProductCard>;
  return typeof product.id === "string"
    && typeof product.slug === "string"
    && typeof product.title === "string"
    && typeof product.price === "string"
    && !!product.seller
    && typeof product.seller === "object"
    && !!product.category
    && typeof product.category === "object";
}

export function getRecentSearches(): string[] {
  return readList(SEARCHES_KEY, isSearch).slice(0, SEARCH_LIMIT);
}

export function rememberSearch(query: string) {
  const value = query.trim().replace(/\s+/g, " ").slice(0, 100);
  if (!value || typeof window === "undefined") return;
  try {
    const searches = getRecentSearches().filter((item) => item.toLowerCase() !== value.toLowerCase());
    localStorage.setItem(SEARCHES_KEY, JSON.stringify([value, ...searches].slice(0, SEARCH_LIMIT)));
  } catch {
    return;
  }
}

export function clearRecentSearches() {
  try {
    localStorage.removeItem(SEARCHES_KEY);
  } catch {
    return;
  }
}

export function getRecentlyViewed(): ProductCard[] {
  return readList(VIEWS_KEY, isProductCard).slice(0, VIEW_LIMIT);
}

export function rememberViewedProduct(product: ProductCard) {
  if (typeof window === "undefined") return;
  const card: ProductCard = {
    id: product.id,
    slug: product.slug,
    title: product.title,
    price: product.price,
    currency: product.currency,
    negotiable: product.negotiable,
    condition: product.condition,
    state: product.state,
    city: product.city,
    thumb_url: product.thumb_url,
    image_count: product.image_count,
    is_featured: product.is_featured,
    promoted_tier: product.promoted_tier,
    sponsored: product.sponsored,
    image_width: product.image_width,
    image_height: product.image_height,
    snippet: product.snippet,
    created_at: product.created_at,
    seller: product.seller,
    category: product.category,
    protected_checkout_enabled: product.protected_checkout_enabled,
    bnpl_enabled: product.bnpl_enabled,
    is_favourite: product.is_favourite,
  };
  try {
    const products = getRecentlyViewed().filter((item) => item.id !== card.id);
    localStorage.setItem(VIEWS_KEY, JSON.stringify([card, ...products].slice(0, VIEW_LIMIT)));
  } catch {
    return;
  }
}

export function clearRecentlyViewed() {
  try {
    localStorage.removeItem(VIEWS_KEY);
  } catch {
    return;
  }
}
