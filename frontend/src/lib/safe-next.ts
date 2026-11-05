/** Only allow same-site relative redirects after login (prevents open redirects). */
export function safeNext(n: string | null) {
  return n && n.startsWith("/") && !n.startsWith("//") ? n : "/";
}
