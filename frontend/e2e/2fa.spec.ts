import crypto from "node:crypto";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { PASSWORD, uniquePhone, passRobotCheck } from "./helpers";

const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";

function base32Decode(secret: string): Buffer {
  let bits = 0;
  let value = 0;
  const out: number[] = [];
  for (const ch of secret.toUpperCase().replace(/=+$/, "")) {
    const idx = ALPHABET.indexOf(ch);
    if (idx < 0) continue;
    value = (value << 5) | idx;
    bits += 5;
    if (bits >= 8) {
      out.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  return Buffer.from(out);
}

function totp(secret: string, at = Date.now()): string {
  const counter = Math.floor(at / 1000 / 30);
  const msg = Buffer.alloc(8);
  msg.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac("sha1", base32Decode(secret)).update(msg).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const code = (digest.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return String(code).padStart(6, "0");
}

async function register(request: APIRequestContext) {
  const email = `mfa-${crypto.randomUUID()}@example.com`;
  const res = await request.post("/api/v1/auth/register", {
    data: { full_name: "MFA E2E", email, phone: uniquePhone(), password: PASSWORD },
  });
  expect(res.status()).toBe(201);
  const token = (await res.json()).access_token as string;
  return { email, headers: { Authorization: `Bearer ${token}` } };
}

test("admin 2FA: set up, login challenge and recovery", async ({ page, request }) => {
  const user = await register(request);
  const setup = await request.post("/api/v1/auth/2fa/setup", { headers: user.headers });
  expect(setup.ok()).toBeTruthy();
  const secret = (await setup.json()).secret as string;
  const enable = await request.post("/api/v1/auth/2fa/enable", {
    headers: user.headers, data: { code: totp(secret) },
  });
  expect(enable.ok()).toBeTruthy();
  expect((await enable.json()).recovery_codes).toHaveLength(8);

  await page.goto("/login");
  await page.getByLabel("Email").filter({ visible: true }).fill(user.email);
  await page.getByLabel("Password").filter({ visible: true }).fill(PASSWORD);
  await passRobotCheck(page);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByText("Two-factor authentication", { exact: false })).toBeVisible();
  await expect(page.getByLabel("Authentication code")).toBeVisible();

  await page.getByLabel("Authentication code").fill(totp(secret, Date.now() + 30_000));
  await page.getByRole("button", { name: "Verify and sign in" }).click();
  await page.waitForURL((u) => !u.pathname.startsWith("/login"));

  await page.goto("/account");
  await expect(page.getByText("Two-factor authentication")).toBeVisible();
  await expect(page.getByText("Enabled")).toBeVisible();
});
