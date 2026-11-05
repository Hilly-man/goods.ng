import { expect, test } from "@playwright/test";
import { BUYER, SELLER, createListing, login, payOnMockProvider } from "./helpers";

test("protected checkout: buy → seller fulfils → buyer confirms → completed", async ({ page, request }) => {
  const product = await createListing(request, `E2E Phone ${Date.now()}`);

  await login(page, BUYER);
  await page.goto(`/item/${product.slug}`);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("E2E Phone");
  await page.locator("#actions").getByRole("link", { name: /Buy with Protected Checkout/ }).click();

  await page.getByLabel("Street address").fill("12 Herbert Macaulay Way");
  await expect(page.getByText("₦257,250").first()).toBeVisible(); // 250,000 + 3,500 courier + 3,750 protection (1.5%)
  await page.getByRole("button", { name: /Pay ₦257,250 securely/ }).click();
  await payOnMockProvider(page);

  await page.waitForURL(/\/orders\/[\w-]+\?paid=1/);
  const orderUrl = page.url().split("?")[0];
  await expect(page.getByText("Awaiting seller").first()).toBeVisible();
  await expect(page.getByText("Funds safeguarded")).toBeVisible();

  await login(page, SELLER);
  await page.goto(orderUrl);
  await page.getByRole("button", { name: "Accept order" }).click();
  await expect(page.getByText("Processing").first()).toBeVisible();
  await page.getByRole("button", { name: "Mark as dispatched" }).click();
  await page.getByLabel(/Tracking \/ waybill number/).fill("GIG-E2E-1");
  await page.getByRole("button", { name: "Confirm dispatch" }).click();
  await expect(page.getByText("GIG-E2E-1").first()).toBeVisible();
  await page.getByRole("button", { name: "Mark as delivered" }).click();
  await page.getByRole("button", { name: "Confirm delivery" }).click();
  await expect(page.getByText("Awaiting confirmation").first()).toBeVisible();

  await login(page, BUYER);
  await page.goto(orderUrl);
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Confirm receipt" }).click();
  await expect(page.getByText("Completed").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Rate this seller" })).toBeVisible();
});

test("negotiation: offer → seller accepts → checkout at agreed price", async ({ page, request }) => {
  const product = await createListing(request, `E2E Offer ${Date.now()}`, "500000.00");

  await login(page, BUYER);
  await page.goto(`/item/${product.slug}`);
  await page.locator("#actions").getByRole("button", { name: "Make an offer" }).click();
  await page.getByLabel("Your offer (₦)").fill("450,000");
  await page.getByRole("button", { name: "Send offer" }).click();
  await page.waitForURL(/\/offers\/[\w-]+/);
  const negotiationId = page.url().split("/").pop();
  await expect(page.getByText("Waiting for the seller")).toBeVisible();

  await login(page, SELLER);
  await page.goto(`/seller/offers/${negotiationId}`);
  await page.getByRole("button", { name: "Accept ₦450,000" }).click();
  await expect(page.getByText("You accepted ₦450,000")).toBeVisible();

  await login(page, BUYER);
  await page.goto(`/offers/${negotiationId}`);
  await page.getByRole("link", { name: /Checkout at ₦450,000/ }).click();
  await expect(page.getByText("Agreed offer price")).toBeVisible();
  // Public listing price is unchanged
  const pub = await request.get(`/api/v1/products/${product.slug}`);
  expect((await pub.json()).price).toBe("500000.00");
});

test("direct contact requires acknowledging the off-platform warning", async ({ page }) => {
  await page.goto("/item/apple-iphone-15-pro-max-256gb-natural-titanium-0000");
  await page.getByRole("button", { name: "WhatsApp" }).click();
  await expect(page.getByText("not covered by our escrow protection")).toBeVisible();
  const open = page.getByRole("button", { name: "Open WhatsApp" });
  await expect(open).toBeDisabled();
  await page.getByLabel(/I understand that deals made outside/).check();
  await expect(open).toBeEnabled();
});
