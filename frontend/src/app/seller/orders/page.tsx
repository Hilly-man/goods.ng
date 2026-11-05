"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Tabs } from "@/components/ui";
import { OrderList } from "@/components/order-list";

export default function Page() {
  const [bucket, setBucket] = useState("action");
  return (
    <RequireAuth seller>
      {() => (
        <div className="space-y-3">
          <h1 className="text-2xl font-bold">Orders</h1>
          <Tabs value={bucket} onChange={setBucket} tabs={[{ value: "action", label: "Needs action" }, { value: "transit", label: "In transit" }, { value: "done", label: "Closed" }, { value: "all", label: "All" }]} />
          <OrderList path="/seller/orders" query={{ bucket }} seller />
        </div>
      )}
    </RequireAuth>
  );
}
