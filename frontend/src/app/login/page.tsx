import type { Metadata } from "next";
import { Suspense } from "react";
import { AuthShell } from "@/components/auth-shell";
import { LoginForm } from "./form";

export const metadata: Metadata = {
  title: "Sign in",
  robots: { index: false, follow: true },
};

export default function LoginPage() {
  return (
    <AuthShell title="Welcome back" sub="Sign in to chat, make offers and buy safely.">
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
