import type { Metadata } from "next";
import { AuthPageShell } from "@/components/AuthPageShell";
import { AuthPanel } from "@/components/AuthPanel";

export const metadata: Metadata = {
  title: "Register",
  robots: {
    index: false,
    follow: false,
  },
};

export default function RegisterPage() {
  return (
    <AuthPageShell
      eyebrow="Create Account"
      title="Register a new AeroSwarm account"
      description="Create your operator profile on its own route with identity, role, company, timezone, and workspace details."
    >
      <AuthPanel initialMode="register" />
    </AuthPageShell>
  );
}
