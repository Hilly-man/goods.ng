import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth-shell";
import { RegisterForm } from "./form";

export const metadata: Metadata = {
  title: "Create account",
  robots: { index: false, follow: true },
};

export default function RegisterPage() {
  return (
    <AuthShell title="Create your account" sub="Buy and sell across Nigeria in minutes.">
      <Suspense>
        <RegisterForm />
      </Suspense>
    </AuthShell>
  );
}
