"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Tabs } from "@/components/ui";
import { OrderList } from "@/components/order-list";

export default function Page() {
  const [status, setStatus] = useState("");
  return (
    <RequireAuth>
      {() => (
        <div className="container-page max-w-3xl space-y-3 py-6">
          <h1 className="text-2xl font-bold">My orders</h1>
          <Tabs value={status} onChange={setStatus} tabs={[{ value: "", label: "All" }, { value: "pending_payment", label: "Unpaid" }, { value: "awaiting_buyer_confirmation", label: "To confirm" }, { value: "disputed", label: "Disputed" }, { value: "completed", label: "Completed" }]} />
          <OrderList path="/orders" query={{ status: status || undefined }} />
        </div>
      )}
    </RequireAuth>
  );
}
