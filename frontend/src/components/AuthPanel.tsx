/**
 * AuthPanel — register/login/password-reset form for AeroSwarm users.
 */

"use client";

import { useState } from "react";
import type { User } from "@/lib/types";
import {
  confirmPasswordReset,
  login,
  register,
  requestPasswordReset,
} from "@/lib/api";

interface AuthPanelProps {
  onAuthenticated: (user: User) => void;
}

type Mode = "login" | "register" | "reset-request" | "reset-confirm";

export function AuthPanel({ onAuthenticated }: AuthPanelProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [resetTokenPreview, setResetTokenPreview] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleAuthSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

    try {
      const response = mode === "login"
        ? await login({ email, password })
        : await register({ email, password });
      onAuthenticated(response.user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetRequest(e: React.FormEvent) {
    e.preventDefault();
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
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetConfirm(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);

    try {
      await confirmPasswordReset({ token: resetToken, newPassword: password });
      setMode("login");
      setPassword("");
      setResetTokenPreview(null);
      setInfo("Password updated. Sign in with the new password.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function renderForm() {
    if (mode === "reset-request") {
      return (
        <form onSubmit={handleResetRequest} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Working..." : "Send Reset"}
          </button>
        </form>
      );
    }

    if (mode === "reset-confirm") {
      return (
        <form onSubmit={handleResetConfirm} className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Reset Token</label>
            <input
              type="text"
              value={resetToken}
              onChange={(e) => setResetToken(e.target.value)}
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">New Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Working..." : "Reset Password"}
          </button>
        </form>
      );
    }

    return (
      <form onSubmit={handleAuthSubmit} className="space-y-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? "Working..." : mode === "login" ? "Sign In" : "Register"}
        </button>
      </form>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4 max-w-md">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {mode === "login" && "Sign In"}
          {mode === "register" && "Create Account"}
          {mode === "reset-request" && "Reset Password"}
          {mode === "reset-confirm" && "Set New Password"}
        </h2>
        {mode === "login" || mode === "register" ? (
          <button
            type="button"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
              setInfo(null);
            }}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            {mode === "login" ? "Need an account?" : "Have an account?"}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => {
              setMode("login");
              setError(null);
              setInfo(null);
            }}
            className="text-xs text-blue-400 hover:text-blue-300"
          >
            Back to sign in
          </button>
        )}
      </div>

      {renderForm()}

      {(mode === "login" || mode === "register") && (
        <button
          type="button"
          onClick={() => {
            setMode("reset-request");
            setError(null);
            setInfo(null);
          }}
          className="text-xs text-gray-400 hover:text-gray-300"
        >
          Forgot password?
        </button>
      )}

      {resetTokenPreview && mode === "reset-confirm" && (
        <p className="text-xs text-yellow-300 break-all">
          Development reset token: {resetTokenPreview}
        </p>
      )}
      {info && <p className="text-green-400 text-sm">{info}</p>}
      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  );
}
