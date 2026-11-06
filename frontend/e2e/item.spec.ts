import { expect, test } from "@playwright/test";
import { createListing } from "./helpers";

test("product page shows the gallery, spec sheet, sharing and contact actions", async ({ page, request }) => {
  const product = await createListing(request, `E2E Layout ${Date.now()}`, "250000.00");
  await page.goto(`/item/${product.slug}`);

  await expect(page.getByRole("heading", { level: 1 })).toContainText("E2E Layout");
  await expect(page.getByText("Condition", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Protected Checkout", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Share on WhatsApp/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save item" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Show contact" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Buy with Protected Checkout/ }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Post an ad like this/ })).toBeVisible();
  await expect(page.getByText("Hide details")).toBeVisible();
});
