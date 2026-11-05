import {
  Baby,
  Briefcase,
  Building2,
  Car,
  Dumbbell,
  Factory,
  Footprints,
  Laptop,
  Package,
  Refrigerator,
  Shirt,
  Smartphone,
  Sofa,
  Sparkles,
  Sprout,
  Tv,
  Wrench,
  type LucideIcon,
} from "lucide-react";

const MAP: Record<string, LucideIcon> = {
  smartphone: Smartphone,
  laptop: Laptop,
  tv: Tv,
  shirt: Shirt,
  footprints: Footprints,
  sofa: Sofa,
  refrigerator: Refrigerator,
  car: Car,
  wrench: Wrench,
  "building-2": Building2,
  sparkles: Sparkles,
  dumbbell: Dumbbell,
  baby: Baby,
  briefcase: Briefcase,
  factory: Factory,
  sprout: Sprout,
  package: Package,
};

// Soft tints per category tile — keeps the grid scannable like a market aisle.
const TINTS = [
  "bg-emerald-50 text-emerald-700",
  "bg-sky-50 text-sky-700",
  "bg-violet-50 text-violet-700",
  "bg-rose-50 text-rose-700",
  "bg-amber-50 text-amber-700",
  "bg-teal-50 text-teal-700",
  "bg-indigo-50 text-indigo-700",
  "bg-orange-50 text-orange-700",
  "bg-lime-50 text-lime-700",
  "bg-cyan-50 text-cyan-700",
  "bg-pink-50 text-pink-700",
  "bg-fuchsia-50 text-fuchsia-700",
];

export function CategoryIcon({ name, className }: { name: string | null | undefined; className?: string }) {
  const Icon = (name && MAP[name]) || Package;
  return <Icon className={className} aria-hidden />;
}

export function tintFor(key: string) {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return TINTS[h % TINTS.length];
}

export const ROOT_CATEGORY_ICON: Record<string, string> = {
  "phones-tablets": "smartphone",
  "computers-accessories": "laptop",
  electronics: "tv",
  fashion: "shirt",
  "shoes-bags": "footprints",
  "home-furniture": "sofa",
  "home-appliances": "refrigerator",
  vehicles: "car",
  "automobile-parts": "wrench",
  "property-real-estate": "building-2",
  "beauty-personal-care": "sparkles",
  "sports-fitness": "dumbbell",
  "baby-kids": "baby",
  "business-equipment": "briefcase",
  "industrial-equipment": "factory",
  agriculture: "sprout",
  "general-merchandise": "package",
};
