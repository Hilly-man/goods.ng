// Realistic public-traffic load test for Goods.ng.
//
//   k6 run backend/perf/load.js
//   BASE_URL=http://localhost:8000 QUERY_MODE=cold k6 run backend/perf/load.js
//
// QUERY_MODE=hot  (default) replays a pool of realistic search terms (cache-friendly, like real users).
// QUERY_MODE=cold generates unique long-tail queries, so every search misses the 15s cache and hits Postgres.
//
// Each virtual user gets a stable X-Anon-Id, matching the browser's per-device anonymous id. This keeps the
// per-identity rate limit honest without every VU sharing one bucket.

import http from "k6/http";
import { check, sleep } from "k6";

const MAX_VUS = Number(__ENV.MAX_VUS || 120);

export const options = {
  scenarios: {
    browse: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "20s", target: Math.round(MAX_VUS * 0.25) },
        { duration: "60s", target: Math.round(MAX_VUS * 0.5) },
        { duration: "40s", target: MAX_VUS },
        { duration: "20s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:home}": ["p(95)<800"],
    "http_req_duration{endpoint:search}": ["p(95)<800"],
    "http_req_duration{endpoint:category}": ["p(95)<800"],
    "http_req_duration{endpoint:detail}": ["p(95)<800"],
    "http_req_duration{endpoint:facets}": ["p(95)<1000"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const MODE = __ENV.QUERY_MODE || "hot";

const QUERIES = [
  "iphone", "laptop", "generator", "sofa", "tv", "nike", "toyota", "fridge", "phone", "land",
  "macbook", "air conditioner", "washing machine", "office chair", "bed frame", "playstation",
  "baby cot", "solar panel", "inverter", "gas cooker", "microwave", "rice cooker", "blender",
  "sneakers", "handbag", "wristwatch", "gold chain", "school bag", "desk", "bookshelf",
  "honda", "lexus", "keke", "motorcycle", "bicycle", "building materials", "cement", "tiles",
  "paint", "plumbing", "electrical cable", "security door", "water tank", "borehole pump",
  "projector", "camera", "drone", "smart watch", "tablet", "keyboard", "monitor", "printer",
];
const CATEGORIES = [
  "phones-tablets", "computers-accessories", "electronics", "fashion", "shoes-bags",
  "home-furniture", "home-appliances", "vehicles", "automobile-parts", "property-real-estate",
  "baby-kids", "beauty-personal-care", "sports-fitness", "business-equipment",
  "industrial-equipment", "agriculture", "general-merchandise",
];
const STATES = ["Lagos", "Abuja", "Rivers", "Oyo", "Kano", "Enugu", "Kaduna", "Delta"];
const SORTS = ["relevance", "newest", "price_asc", "price_desc"];

const FALLBACK_SLUG = "apple-iphone-15-pro-max-256gb-natural-titanium-0000";

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function randomInt(min, max) {
  return min + Math.floor(Math.random() * (max - min + 1));
}

function query() {
  if (MODE === "cold") {
    const a = Math.random().toString(36).slice(2, 10);
    const b = Math.random().toString(36).slice(2, 6);
    return `${a} ${b}`;
  }
  return pick(QUERIES);
}

function headers() {
  // Stable per VU, 8-64 chars, like the browser's localStorage anonymous id.
  return {
    Accept: "application/json",
    "X-Anon-Id": `k6-vu-${__VU}-${__VU * 7919 + 100003}`.slice(0, 64),
  };
}

export function setup() {
  const res = http.get(`${BASE}/api/v1/products?page_size=24`, { headers: { Accept: "application/json" } });
  let slugs = [];
  if (res.status === 200) {
    try {
      slugs = res.json("items").map((i) => i.slug).filter(Boolean);
    } catch (_) {
      slugs = [];
    }
  }
  if (!slugs.length) slugs = [FALLBACK_SLUG];
  return { slugs };
}

export default function (data) {
  const h = headers();
  const r = Math.random();
  let res;
  let endpoint;

  if (r < 0.28) {
    endpoint = "home";
    res = http.get(`${BASE}/api/v1/products/feed/home`, { headers: h, tags: { endpoint } });
  } else if (r < 0.62) {
    endpoint = "search";
    let url = `${BASE}/api/v1/products?q=${encodeURIComponent(query())}`;
    if (Math.random() < 0.35) url += `&state=${encodeURIComponent(pick(STATES))}`;
    if (Math.random() < 0.2) url += `&page=${randomInt(1, 3)}`;
    res = http.get(url, { headers: h, tags: { endpoint } });
  } else if (r < 0.77) {
    endpoint = "category";
    const sort = pick(SORTS);
    res = http.get(
      `${BASE}/api/v1/products?category=${pick(CATEGORIES)}&sort=${sort}` +
        (Math.random() < 0.3 ? `&posted_within=${pick([7, 30, 90])}` : ""),
      { headers: h, tags: { endpoint } },
    );
  } else if (r < 0.89) {
    endpoint = "detail";
    res = http.get(`${BASE}/api/v1/products/${pick(data.slugs)}`, { headers: h, tags: { endpoint } });
  } else if (r < 0.95) {
    endpoint = "facets";
    res = http.get(`${BASE}/api/v1/products/facets?q=${encodeURIComponent(query())}`, {
      headers: h,
      tags: { endpoint },
    });
  } else {
    endpoint = "locations";
    res = http.get(`${BASE}/api/v1/locations`, { headers: h, tags: { endpoint } });
  }

  check(res, { "status 200": (x) => x.status === 200 });
  sleep(0.3 + Math.random() * 1.2);
}
