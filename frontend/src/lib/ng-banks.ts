/**
 * Nigerian bank directory for the seller payout form.
 *
 * Codes follow the CBN/Paystack/Flutterwave conventions used by most payout partners. A licensed
 * payout adapter should still resolve the account and may map codes; verify this list against the
 * partner's directory before go-live.
 */

export type BankGroup = "Commercial banks" | "Microfinance banks (MFB)" | "Mobile money / PSB";

export type NgBank = { name: string; code: string; group: BankGroup };

export const NG_BANKS: NgBank[] = [
  // Commercial banks
  { name: "Access Bank", code: "044", group: "Commercial banks" },
  { name: "Access Bank (Diamond)", code: "063", group: "Commercial banks" },
  { name: "Citibank Nigeria", code: "023", group: "Commercial banks" },
  { name: "Ecobank Nigeria", code: "050", group: "Commercial banks" },
  { name: "Fidelity Bank", code: "070", group: "Commercial banks" },
  { name: "First Bank of Nigeria", code: "011", group: "Commercial banks" },
  { name: "First City Monument Bank (FCMB)", code: "214", group: "Commercial banks" },
  { name: "Globus Bank", code: "103", group: "Commercial banks" },
  { name: "Guaranty Trust Bank (GTBank)", code: "058", group: "Commercial banks" },
  { name: "Jaiz Bank", code: "301", group: "Commercial banks" },
  { name: "Keystone Bank", code: "082", group: "Commercial banks" },
  { name: "Lotus Bank", code: "303", group: "Commercial banks" },
  { name: "Optimus Bank", code: "107", group: "Commercial banks" },
  { name: "Parallex Bank", code: "104", group: "Commercial banks" },
  { name: "Polaris Bank", code: "076", group: "Commercial banks" },
  { name: "PremiumTrust Bank", code: "105", group: "Commercial banks" },
  { name: "Providus Bank", code: "101", group: "Commercial banks" },
  { name: "Stanbic IBTC Bank", code: "221", group: "Commercial banks" },
  { name: "Standard Chartered Bank", code: "068", group: "Commercial banks" },
  { name: "Sterling Bank", code: "232", group: "Commercial banks" },
  { name: "SunTrust Bank", code: "100", group: "Commercial banks" },
  { name: "TAJBank", code: "302", group: "Commercial banks" },
  { name: "Titan Trust Bank", code: "102", group: "Commercial banks" },
  { name: "Union Bank of Nigeria", code: "032", group: "Commercial banks" },
  { name: "United Bank for Africa (UBA)", code: "033", group: "Commercial banks" },
  { name: "Unity Bank", code: "215", group: "Commercial banks" },
  { name: "Wema Bank", code: "035", group: "Commercial banks" },
  { name: "Zenith Bank", code: "057", group: "Commercial banks" },

  // Microfinance banks
  { name: "Accion Microfinance Bank", code: "602", group: "Microfinance banks (MFB)" },
  { name: "Carbon (One Finance)", code: "565", group: "Microfinance banks (MFB)" },
  { name: "FairMoney Microfinance Bank", code: "51318", group: "Microfinance banks (MFB)" },
  { name: "Kuda Microfinance Bank", code: "50211", group: "Microfinance banks (MFB)" },
  { name: "Mint Microfinance Bank", code: "50304", group: "Microfinance banks (MFB)" },
  { name: "Moniepoint Microfinance Bank", code: "50515", group: "Microfinance banks (MFB)" },
  { name: "Rubies Microfinance Bank", code: "125", group: "Microfinance banks (MFB)" },
  { name: "Sparkle Microfinance Bank", code: "51310", group: "Microfinance banks (MFB)" },
  { name: "VFD Microfinance Bank", code: "566", group: "Microfinance banks (MFB)" },

  // Mobile money / payment service banks
  { name: "9 Payment Service Bank (9PSB)", code: "120001", group: "Mobile money / PSB" },
  { name: "Airtel SmartCash PSB", code: "120004", group: "Mobile money / PSB" },
  { name: "Hope Payment Service Bank", code: "120002", group: "Mobile money / PSB" },
  { name: "MoneyMaster PSB", code: "120005", group: "Mobile money / PSB" },
  { name: "MTN MoMo PSB", code: "120003", group: "Mobile money / PSB" },
  { name: "OPay (Paycom)", code: "999992", group: "Mobile money / PSB" },
  { name: "Paga", code: "100002", group: "Mobile money / PSB" },
  { name: "PalmPay", code: "999991", group: "Mobile money / PSB" },
];

export const BANK_GROUPS: BankGroup[] = ["Commercial banks", "Microfinance banks (MFB)", "Mobile money / PSB"];

export function findBank(code: string): NgBank | undefined {
  return NG_BANKS.find((b) => b.code === code);
}
