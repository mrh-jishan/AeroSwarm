/**
 * AuthPanel — redesigned login/register/password-reset surface for AeroSwarm users.
 */

"use client";

import { useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { User } from "@/lib/types";
import {
  confirmPasswordReset,
  login,
  register,
  requestPasswordReset,
} from "@/lib/api";

interface AuthPanelProps {
  initialMode?: "login" | "register";
  onAuthenticated?: (user: User) => void;
}

type Mode = "login" | "register" | "reset-request" | "reset-confirm";

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-[0.28em] text-slate-500">{label}</span>
      {children}
      {hint && <p className="mt-2 text-xs text-slate-500">{hint}</p>}
    </label>
  );
}

function inputClassName() {
  return "mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500";
}

export function AuthPanel({ initialMode = "login", onAuthenticated }: AuthPanelProps) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [timezone, setTimezone] = useState(
    typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "",
  );
  const [bio, setBio] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [resetTokenPreview, setResetTokenPreview] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const panelTitle = useMemo(() => {
    if (mode === "login") return "Welcome back";
    if (mode === "register") return "Create your operator profile";
    if (mode === "reset-request") return "Reset your password";
    return "Set a new password";
  }, [mode]);

  async function handleAuthSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

    try {
      const response = mode === "login"
        ? await login({ email, password })
        : await register({
            email,
            password,
            fullName,
            jobTitle,
            companyName,
            timezone,
            bio,
          });
      if (onAuthenticated) {
        onAuthenticated(response.user);
      } else {
        router.push("/dashboard");
      }
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetRequest(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    setResetTokenPreview(null);

    try {
      const response = await requestPasswordReset({ email });
      if (response.reset_token) {
        setResetToken(response.reset_token);
        setResetTokenPreview(response.reset_token);
        setMode("reset-confirm");
        setInfo("Reset token issued for development. Use it to set a new password.");
      } else {
        setInfo("If an account exists for that email, reset instructions were issued.");
      }
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetConfirm(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

    try {
      await confirmPasswordReset({ token: resetToken, newPassword: password });
      setMode("login");
      setPassword("");
      setResetTokenPreview(null);
      setInfo("Password updated. Sign in with the new password.");
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function resetMessages(nextMode: Mode) {
    setMode(nextMode);
    setError(null);
    setInfo(null);
  }

  function renderAuthForm() {
    if (mode === "reset-request") {
      return (
        <form onSubmit={handleResetRequest} className="space-y-5">
          <Field label="Email">
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className={inputClassName()}
            />
          </Field>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-400"
          >
            {loading ? "Working..." : "Send Reset Link"}
          </button>
        </form>
      );
    }

    if (mode === "reset-confirm") {
      return (
        <form onSubmit={handleResetConfirm} className="space-y-5">
          <Field label="Reset Token">
            <input
              type="text"
              value={resetToken}
              onChange={(event) => setResetToken(event.target.value)}
              required
              className={inputClassName()}
            />
          </Field>
          <Field label="New Password" hint="Use at least 8 characters.">
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              className={inputClassName()}
            />
          </Field>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-400"
          >
            {loading ? "Working..." : "Reset Password"}
          </button>
        </form>
      );
    }

    return (
      <form onSubmit={handleAuthSubmit} className="space-y-5">
        {mode === "register" && (
          <>
            <Field label="Full Name" hint="This becomes your visible workspace identity.">
              <input
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                minLength={2}
                className={inputClassName()}
              />
            </Field>
            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Role">
                <input
                  type="text"
                  value={jobTitle}
                  onChange={(event) => setJobTitle(event.target.value)}
                  placeholder="Staff Engineer"
                  className={inputClassName()}
                />
              </Field>
              <Field label="Company">
                <input
                  type="text"
                  value={companyName}
                  onChange={(event) => setCompanyName(event.target.value)}
                  placeholder="AeroSwarm"
                  className={inputClassName()}
                />
              </Field>
            </div>
            <Field label="Timezone">
              <input
                type="text"
                value={timezone}
                onChange={(event) => setTimezone(event.target.value)}
                placeholder="America/New_York"
                className={inputClassName()}
              />
            </Field>
            <Field label="Bio" hint="Optional, but useful when reviewing your account later.">
              <textarea
                value={bio}
                onChange={(event) => setBio(event.target.value)}
                rows={4}
                className={inputClassName()}
              />
            </Field>
          </>
        )}

        <Field label="Email">
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            className={inputClassName()}
          />
        </Field>

        <Field label="Password" hint={mode === "login" ? undefined : "Use at least 8 characters."}>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={8}
            className={inputClassName()}
          />
        </Field>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-400"
        >
          {loading ? "Working..." : mode === "login" ? "Sign In" : "Create Account"}
        </button>
      </form>
    );
  }

  return (
    <div className="w-full max-w-6xl overflow-hidden rounded-[2rem] border border-slate-800 bg-slate-950/95 shadow-[0_40px_120px_rgba(2,6,23,0.65)] lg:grid lg:grid-cols-[1.1fr_0.9fr]">
      <section className="relative overflow-hidden border-b border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.24),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.18),_transparent_32%),linear-gradient(145deg,_rgba(15,23,42,0.96),_rgba(2,6,23,0.98))] p-8 lg:border-b-0 lg:border-r lg:p-10">
        <div className="absolute inset-0 bg-[linear-gradient(120deg,transparent_0%,transparent_46%,rgba(148,163,184,0.05)_46.5%,transparent_47%,transparent_100%)]" />
        <div className="relative">
          <p className="text-xs uppercase tracking-[0.4em] text-sky-300/80">AeroSwarm Access</p>
          <h2 className="mt-4 max-w-xl text-4xl font-semibold tracking-tight text-white">
            Run parallel software sessions with an account that actually has context.
          </h2>
          <p className="mt-5 max-w-xl text-sm leading-7 text-slate-300">
            Sign in to review history, configure providers, and manage your profile. New accounts now capture the
            details that make your workspace feel owned instead of anonymous.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">What you get</p>
              <p className="mt-2 text-sm text-white">Session history, retries, workers, and GitHub-backed runs.</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Profile aware</p>
              <p className="mt-2 text-sm text-white">Name, role, company, timezone, and bio stored on your account.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="p-8 lg:p-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Account</p>
            <h3 className="mt-3 text-3xl font-semibold text-white">{panelTitle}</h3>
          </div>

          {(mode === "login" || mode === "register") ? (
            <Link
              href={mode === "login" ? "/register" : "/login"}
              className="rounded-full border border-slate-800 px-4 py-2 text-xs font-medium uppercase tracking-[0.2em] text-sky-300 transition hover:border-sky-500 hover:text-sky-200"
            >
              {mode === "login" ? "Create Account" : "Sign In Instead"}
            </Link>
          ) : (
            <button
              type="button"
              onClick={() => resetMessages(initialMode)}
              className="rounded-full border border-slate-800 px-4 py-2 text-xs font-medium uppercase tracking-[0.2em] text-sky-300 transition hover:border-sky-500 hover:text-sky-200"
            >
              Back
            </button>
          )}
        </div>

        <p className="mt-4 text-sm leading-7 text-slate-400">
          {mode === "login" && "Use your account to return to your dashboard and continue previous runs."}
          {mode === "register" && "Set up your account once and keep your identity available across sessions."}
          {mode === "reset-request" && "Enter your email and we will issue reset instructions."}
          {mode === "reset-confirm" && "Paste the token and choose a new password to regain access."}
        </p>

        <div className="mt-8">{renderAuthForm()}</div>

        {(mode === "login" || mode === "register") && (
          <button
            type="button"
            onClick={() => resetMessages("reset-request")}
            className="mt-5 text-sm text-slate-400 transition hover:text-slate-200"
          >
            Forgot password?
          </button>
        )}

        {resetTokenPreview && mode === "reset-confirm" && (
          <div className="mt-5 rounded-2xl border border-amber-900/80 bg-amber-950/40 p-4">
            <p className="text-xs uppercase tracking-[0.25em] text-amber-300/80">Development Reset Token</p>
            <p className="mt-2 break-all text-sm text-amber-100">{resetTokenPreview}</p>
          </div>
        )}
        {info && <p className="mt-5 text-sm text-emerald-300">{info}</p>}
        {error && <p className="mt-5 text-sm text-rose-300">{error}</p>}
      </section>
    </div>
  );
}
