import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const PASSWORD = "GoodsNG2026!";
export const SELLER = "chinedu@demo.goods.ng";
export const BUYER = "buyer@demo.goods.ng";

export async function login(page: Page, email: string) {
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
}

/** Creates a fresh listing through the API as the demo seller so tests never exhaust seeded stock. */
export async function createListing(request: APIRequestContext, title: string, price = "250000.00") {
  const auth = await request.post("/api/v1/auth/login", { data: { email: SELLER, password: PASSWORD } });
  expect(auth.ok()).toBeTruthy();
  const token = (await auth.json()).access_token;
  const cats = await (await request.get("/api/v1/categories")).json();
  const phones = cats.find((c: { slug: string }) => c.slug === "phones-tablets");
  const leaf = phones.children.find((c: { slug: string }) => c.slug === "mobile-phones");
  const r = await request.post("/api/v1/seller/products", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      title, description: "End-to-end test listing in excellent condition with charger.", category_id: leaf.id,
      brand: "TestBrand", condition: "foreign_used", price, negotiable: true, quantity: 1, state: "Lagos", city: "Ikeja",
      delivery_options: [{ type: "courier", label: "Courier", fee: "3500", eta_days: 2 }], bnpl_enabled: true,
    },
  });
  expect(r.ok()).toBeTruthy();
  return r.json();
}

export async function payOnMockProvider(page: Page, outcome: "success" | "failed" = "success") {
  await page.waitForURL(/\/dev\/mock-checkout/);
  await expect(page.getByText("Mock payment provider")).toBeVisible();
  await page.getByRole("button", { name: outcome === "success" ? "Simulate successful payment" : "Simulate failed payment" }).click();
}
