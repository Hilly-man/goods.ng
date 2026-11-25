import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ProductCard } from "./types";
import {
  clearRecentlyViewed,
  clearRecentSearches,
  getRecentlyViewed,
  getRecentSearches,
  rememberSearch,
  rememberViewedProduct,
} from "./search-history";

const storage = new Map<string, string>();

const product = (id: string): ProductCard => ({
  id,
  slug: `listing-${id}`,
  title: `Listing ${id}`,
  price: "1000.00",
  currency: "NGN",
  negotiable: false,
  condition: "brand_new",
  state: "Lagos",
  city: "Ikeja",
  thumb_url: null,
  image_count: 0,
  is_featured: false,
  created_at: "2026-01-01T00:00:00Z",
  seller: {
    id: "seller-id",
    store_name: "Seller",
    slug: "seller",
    logo_url: null,
    verification_level: "unverified",
    is_premium: false,
    rating_avg: "0",
    rating_count: 0,
    state: "Lagos",
    city: "Ikeja",
    member_since: "2026-01-01T00:00:00Z",
    completed_sales: 0,
    whatsapp_available: false,
    phone_available: false,
  },
  category: { id: "category-id", name: "Phones", slug: "phones" },
  protected_checkout_enabled: true,
  bnpl_enabled: false,
  is_favourite: false,
});

beforeEach(() => {
  storage.clear();
  vi.stubGlobal("window", {});
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
});

afterEach(() => vi.unstubAllGlobals());

describe("search history", () => {
  it("keeps recent queries first, deduplicates case-insensitively, and can clear them", () => {
    rememberSearch("  Samsung   phone ");
    rememberSearch("camera");
    rememberSearch("samsung phone");

    expect(getRecentSearches()).toEqual(["samsung phone", "camera"]);
    clearRecentSearches();
    expect(getRecentSearches()).toEqual([]);
  });

  it("keeps recently viewed listings first, deduplicates, and can clear them", () => {
    rememberViewedProduct(product("1"));
    rememberViewedProduct(product("2"));
    rememberViewedProduct(product("1"));

    expect(getRecentlyViewed().map((item) => item.id)).toEqual(["1", "2"]);
    clearRecentlyViewed();
    expect(getRecentlyViewed()).toEqual([]);
  });
});
