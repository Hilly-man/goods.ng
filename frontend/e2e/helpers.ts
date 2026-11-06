import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const PASSWORD = "GoodsNG2026!";
export const SELLER = "chinedu@demo.goods.ng";
export const BUYER = "buyer@demo.goods.ng";

/** Unique per worker and per run, so parallel specs never collide on the users.phone unique index. */
export const uniquePhone = () => `+23480${String(Math.floor(Math.random() * 1e8)).padStart(8, "0")}`;

/** New browser contexts get the (dev mock) "I'm not a robot" check on the sign-in form. */
export async function passRobotCheck(page: Page) {
  const robot = page.getByRole("checkbox", { name: "I'm not a robot" });
  // The form asks the API whether a check is needed; wait for that answer (not "network idle",
  // which never settles while the dev server keeps its live-reload connection open).
  // A fresh browser always gets the check; give the form up to 5s to show it, then carry on if it doesn't.
  await robot.waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
  if (await robot.isVisible().catch(() => false)) {
    await robot.click();
    await expect(robot).toHaveAttribute("aria-checked", "true");
  }
}

/** Note: while Next streams /login, React briefly keeps a *hidden* copy of the form (`<div hidden>`),
 *  so field locators filter to visible elements. Users never see the duplicate. */
export async function login(page: Page, email: string) {
  // Leave the current page first: an open page that polls the API would otherwise notice the cleared
  // session and redirect itself to /login at the same moment we navigate there.
  await page.goto("about:blank");
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Email").filter({ visible: true }).fill(email);
  await page.getByLabel("Password").filter({ visible: true }).fill(PASSWORD);
  await passRobotCheck(page);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));
}

/** Creates a fresh listing through the API as the demo seller so tests never exhaust seeded stock. */
export async function createListing(request: APIRequestContext, title: string, price = "250000.00") {
  // Dev servers use the mock captcha; a fresh API client is a "new device", so send its token.
  const auth = await request.post("/api/v1/auth/login", { data: { email: SELLER, password: PASSWORD, captcha_token: "mock-ok" } });
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
