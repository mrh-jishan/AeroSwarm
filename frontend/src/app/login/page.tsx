import type { Metadata } from "next";
import { AuthPageShell } from "@/components/AuthPageShell";
import { AuthPanel } from "@/components/AuthPanel";

export const metadata: Metadata = {
  title: "Sign In",
  robots: {
    index: false,
    follow: false,
  },
};

export default function LoginPage() {
  return (
    <AuthPageShell
      eyebrow="Account Access"
      title="Sign in to your workspace"
      description="Access your dashboard, session history, worker views, and profile from a dedicated sign-in route."
    >
      <AuthPanel initialMode="login" />
    </AuthPageShell>
  );
}
