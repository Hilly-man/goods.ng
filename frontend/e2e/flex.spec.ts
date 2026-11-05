import { expect, test, type APIRequestContext } from "@playwright/test";
import { PASSWORD, createListing, login } from "./helpers";

const unique = () => String(Date.now()).slice(-8);
const phone = () => `+23480${unique()}`;
const bvn = () => `1${String(Date.now()).slice(-9)}${Math.floor(Math.random() * 10)}`;

async function newBuyer(request: APIRequestContext) {
  const email = `flex-${Date.now()}-${Math.floor(Math.random() * 1000)}@example.com`;
  const reg = await request.post("/api/v1/auth/register", {
    data: { full_name: "Flex E2E Buyer", email, phone: phone(), password: PASSWORD },
  });
  expect(reg.status()).toBe(201);
  const token = (await reg.json()).access_token as string;
  const headers = { Authorization: `Bearer ${token}` };

  const otp = await request.post("/api/v1/auth/otp/request", { headers, data: {} });
  expect(otp.ok()).toBeTruthy();
  const verified = await request.post("/api/v1/auth/otp/verify", {
    headers, data: { code: (await otp.json()).dev_code },
  });
  expect(verified.ok()).toBeTruthy();

  // BVN + bank statement, but deliberately no guarantor yet.
  expect((await request.post("/api/v1/bnpl/profile/bvn", { headers, data: { bvn: bvn() } })).ok()).toBeTruthy();
  expect((await request.post("/api/v1/bnpl/profile/bank/connect",
    { headers, data: { code: "mock:salary_earner:GTBank" } })).ok()).toBeTruthy();
  return { email, headers };
}

test("Goods Flex requires a guarantor and only allows one running plan", async ({ page, request }) => {
  const buyer = await newBuyer(request);
  const product = await createListing(request, `E2E Flex ${Date.now()}`, "150000.00");

  await login(page, buyer.email);
  await page.goto(`/checkout/${product.slug}?flex=1`);

  // No guarantor yet → setup message, no usable limit and the apply button is blocked.
  await expect(page.getByText("You need a guarantor to consent before you can use Goods Flex.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Apply for Goods Flex" })).toBeDisabled();

  // Add and consent a guarantor through the API, then the limit becomes available.
  const guarantor = await request.post("/api/v1/bnpl/profile/guarantor", {
    headers: buyer.headers,
    data: { full_name: "Emeka Obi", phone: "08099990077", relationship: "Brother", bvn: bvn() },
  });
  expect(guarantor.ok()).toBeTruthy();
  const token = (await guarantor.json()).dev_link.split("/").pop();
  const consent = await request.post(`/api/v1/bnpl/guarantor/${token}`, { data: { agree: true } });
  expect((await consent.json()).status).toBe("consented");

  await page.reload();
  await expect(page.getByText("Your Goods Flex limit")).toBeVisible();
  await page.getByRole("checkbox").check();
  await expect(page.getByRole("button", { name: "Apply for Goods Flex" })).toBeEnabled();

  // Start a plan via the API (apply → accept → pay the down payment).
  const address = { full_name: "Flex E2E Buyer", phone: phone(), state: "Lagos", city: "Ikeja", street: "12 Test Street" };
  const application = await request.post("/api/v1/bnpl/applications", {
    headers: buyer.headers,
    data: { product_id: product.id, tenor_months: 3, consent: true, delivery_option_index: 0, address },
  });
  expect(application.ok()).toBeTruthy();
  const appId = (await application.json()).id;
  const accepted = await request.post(`/api/v1/bnpl/applications/${appId}/accept`, {
    headers: buyer.headers, data: { accept_terms: true },
  });
  expect(accepted.ok()).toBeTruthy();
  const reference = (await accepted.json()).payment_reference;
  const paid = await request.post(`/api/v1/dev/mock-provider/payments/${reference}/simulate`,
    { headers: buyer.headers, data: { outcome: "success" } });
  expect(paid.ok()).toBeTruthy();

  // A second checkout is blocked by the one-running-plan rule.
  await page.reload();
  await expect(page.getByText("One Goods Flex plan at a time")).toBeVisible();
  await expect(page.getByRole("button", { name: "Apply for Goods Flex" })).toBeDisabled();
});
