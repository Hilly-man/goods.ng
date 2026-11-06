import { describe, expect, it } from "vitest";
import { detectSource, landingSignal } from "./interest";

const P = (s: string) => new URLSearchParams(s);

describe("detectSource", () => {
  it("prefers utm_source, then ad click ids, then the referrer", () => {
    expect(detectSource("https://www.google.com/", P("utm_source=tiktok"), "goods.ng")).toBe("tiktok");
    expect(detectSource("", P("gclid=abc"), "goods.ng")).toBe("google");
    expect(detectSource("", P("fbclid=abc"), "goods.ng")).toBe("facebook");
    expect(detectSource("https://l.instagram.com/", P(""), "goods.ng")).toBe("instagram");
    expect(detectSource("https://www.bing.com/search", P(""), "goods.ng")).toBe("bing");
    expect(detectSource("https://t.co/xyz", P(""), "goods.ng")).toBe("x");
    expect(detectSource("https://someblog.ng/post", P(""), "goods.ng")).toBe("other");
  });
  it("ignores internal navigation and direct visits", () => {
    expect(detectSource("https://goods.ng/search", P(""), "goods.ng")).toBeNull();
    expect(detectSource("https://www.goods.ng/", P(""), "goods.ng")).toBeNull();
    expect(detectSource("", P(""), "goods.ng")).toBeNull();
  });
});

describe("landingSignal", () => {
  it("captures the ad keyword and the landing listing", () => {
    expect(landingSignal("https://goods.ng/item/iphone-13-0002?utm_source=google&utm_term=iphone%2013&utm_campaign=phones", "")).toEqual({
      kind: "landing", source: "google", query: "iphone 13", campaign: "phones", product_slug: "iphone-13-0002", category_slug: undefined,
    });
  });
  it("captures a category landing from social", () => {
    expect(landingSignal("https://goods.ng/c/mobile-phones", "https://www.tiktok.com/")?.category_slug).toBe("mobile-phones");
  });
  it("skips landings with nothing to learn", () => {
    expect(landingSignal("https://goods.ng/", "https://www.google.com/")).toBeNull();
  });
});
