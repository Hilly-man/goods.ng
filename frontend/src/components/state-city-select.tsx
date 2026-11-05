"use client";

import { useEffect, useState } from "react";
import { http } from "@/lib/api";
import { NG_STATES } from "@/lib/format";
import { Select } from "./ui";

type Locations = { states: string[]; cities: Record<string, string[]> };

// One request per page load, shared by every dropdown on the page.
let cache: Promise<Locations> | null = null;
function loadLocations() {
  cache ??= http.get<Locations>("/locations").catch((e) => {
    cache = null;
    throw e;
  });
  return cache;
}

export function useLocations() {
  const [data, setData] = useState<Locations | null>(null);
  useEffect(() => {
    let alive = true;
    loadLocations().then((d) => alive && setData(d)).catch(() => {});
    return () => {
      alive = false;
    };
  }, []);
  return data;
}

/**
 * Linked State → City dropdowns. Cities come from the server's `cities` table, and the server
 * re-validates that the city belongs to the state on save.
 */
export function StateCitySelect({
  state,
  city,
  onChange,
  errors = {},
  required,
  stateLabel = "State",
  cityLabel = "City / area",
}: {
  state: string;
  city: string;
  onChange: (v: { state: string; city: string }) => void;
  errors?: { state?: string; city?: string };
  required?: boolean;
  stateLabel?: string;
  cityLabel?: string;
}) {
  const loc = useLocations();
  const cities = (state && loc?.cities[state]) || [];
  // Keep a legacy/unknown saved value visible so editing an old record doesn't silently drop it.
  const showLegacy = !!city && !!loc && !cities.includes(city);
  return (
    <>
      <Select label={stateLabel} required={required} value={state} error={errors.state}
        onChange={(e) => onChange({ state: e.target.value, city: "" })}>
        <option value="">Select state</option>
        {(loc?.states ?? NG_STATES).map((s) => <option key={s}>{s}</option>)}
      </Select>
      <Select label={cityLabel} required={required} value={city} error={errors.city} disabled={!state || !loc}
        onChange={(e) => onChange({ state, city: e.target.value })}
        hint={!state ? "Select a state first" : undefined}>
        <option value="">{!state ? "Select state first" : loc ? "Select city / area" : "Loading…"}</option>
        {showLegacy && <option value={city}>{city} (please update)</option>}
        {cities.map((c) => <option key={c}>{c}</option>)}
      </Select>
    </>
  );
}
