import type { NextConfig } from "next";

const rawApi = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
// Render can inject a private "host:port" value; Next needs an absolute URL for rewrites.
const API = (/^https?:\/\//i.test(rawApi) ? rawApi : `http://${rawApi}`).replace(/\/+$/, "");
const isDev = process.env.NODE_ENV !== "production";

// Nonce-based CSP is incompatible with PPR/Cache Components, so we use a header policy with
// 'unsafe-inline' for Next.js's inline bootstrap and allowlist Mono Connect for bank linking.
// "I'm not a robot" widgets: Google reCAPTCHA v2 and Cloudflare Turnstile.
const CAPTCHA = "https://www.google.com https://www.gstatic.com https://www.recaptcha.net https://challenges.cloudflare.com";
// Ad measurement (Meta Pixel, Google tag). Scripts are only injected after marketing-cookie consent.
const ADS_SCRIPT = "https://connect.facebook.net https://www.googletagmanager.com https://www.googleadservices.com https://googleads.g.doubleclick.net";
const ADS_CONNECT = "https://www.facebook.com https://connect.facebook.net https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com https://*.doubleclick.net https://www.googleadservices.com";
const ADS_IMG = "https://www.facebook.com https://*.google-analytics.com https://www.googletagmanager.com https://*.doubleclick.net https://www.google.com https://www.google.com.ng";

const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""} https://connect.mono.co ${CAPTCHA} ${ADS_SCRIPT}`,
  "style-src 'self' 'unsafe-inline'",
  `img-src 'self' data: blob: https://connect.mono.co https://*.mono.co https://*.blob.vercel-storage.com ${ADS_IMG}`,
  "font-src 'self' data:",
  `connect-src 'self'${isDev ? " ws: wss:" : ""} https://connect.mono.co https://*.mono.co https://api.withmono.com ${CAPTCHA} ${ADS_CONNECT}`,
  `frame-src 'self' https://connect.mono.co https://link.mono.co ${CAPTCHA} https://www.facebook.com https://td.doubleclick.net`,
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(isDev ? [] : ["upgrade-insecure-requests"]),
].join("; ");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  // Lets the dev server serve the admin subdomain (admin.localhost) without cross-origin blocking.
  allowedDevOrigins: ["admin.localhost"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // Same-origin API + media: the browser only ever talks to the Next.js origin, so the
  // httpOnly refresh cookie is first-party and no CORS is needed in production.
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${API}/api/v1/:path*` },
      { source: "/media/:path*", destination: `${API}/media/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          ...(!isDev ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" }] : []),
        ],
      },
    ];
  },
};

export default nextConfig;
