import { describe, expect, it } from "vitest";
import { date, naira, safeNextForTest, toMoneyString } from "./format.test-helpers";

describe("naira", () => {
  it("groups thousands without float maths", () => {
    expect(naira("1500000.00")).toBe("₦1,500,000");
    expect(naira("999.50", { kobo: true })).toBe("₦999.50");
    expect(naira("12345678901234567.89", { kobo: true })).toBe("₦12,345,678,901,234,567.89");
    expect(naira(null)).toBe("—");
  });
});

describe("toMoneyString", () => {
  it("normalises user input to 2dp decimal strings", () => {
    expect(toMoneyString("1,350,000")).toBe("1350000.00");
    expect(toMoneyString("₦ 450,000.5")).toBe("450000.50");
    expect(toMoneyString("007")).toBe("7.00");
  });
  it("rejects invalid or over-precise amounts", () => {
    expect(toMoneyString("12.345")).toBeNull();
    expect(toMoneyString("-5")).toBeNull();
    expect(toMoneyString("1e6")).toBeNull();
    expect(toMoneyString("")).toBeNull();
  });
});

describe("date", () => {
  it("formats deterministically in West Africa Time", () => {
    expect(date("2026-11-05T23:30:00Z")).toBe("6 Nov 2026");
    expect(date("2026-11-05T10:05:00Z", true)).toBe("5 Nov 2026, 11:05");
  });
});

describe("safeNext", () => {
  it("blocks open redirects", () => {
    expect(safeNextForTest("/orders")).toBe("/orders");
    expect(safeNextForTest("//evil.com")).toBe("/");
    expect(safeNextForTest("https://evil.com")).toBe("/");
    expect(safeNextForTest(null)).toBe("/");
  });
});
