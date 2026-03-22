/**
 * ProfileSettingsPanel — editable account profile for the authenticated user.
 */

"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { updateMyProfile } from "@/lib/api";
import type { User } from "@/lib/types";

interface ProfileSettingsPanelProps {
  user: User;
  onUserUpdated: (user: User) => void;
}

function formatMemberSince(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function ProfileSettingsPanel({ user, onUserUpdated }: ProfileSettingsPanelProps) {
  const [fullName, setFullName] = useState(user.full_name ?? "");
  const [jobTitle, setJobTitle] = useState(user.job_title ?? "");
  const [companyName, setCompanyName] = useState(user.company_name ?? "");
  const [timezone, setTimezone] = useState(user.timezone ?? "");
  const [bio, setBio] = useState(user.bio ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setFullName(user.full_name ?? "");
    setJobTitle(user.job_title ?? "");
    setCompanyName(user.company_name ?? "");
    setTimezone(user.timezone ?? "");
    setBio(user.bio ?? "");
  }, [user]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);

    try {
      const updatedUser = await updateMyProfile({
        fullName,
        jobTitle,
        companyName,
        timezone,
        bio,
      });
      onUserUpdated(updatedUser);
      setNotice("Profile updated.");
    } catch (submitError: unknown) {
      setError(submitError instanceof Error ? submitError.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-[2rem] border border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_38%),linear-gradient(135deg,_rgba(15,23,42,0.96),_rgba(2,6,23,0.98))] p-8">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-sky-300/80">Profile</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">
              {user.full_name || "Complete your account profile"}
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
              Keep your account details current so the workspace feels personal and session history is tied to a
              clear owner identity.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Email</p>
              <p className="mt-2 text-sm text-white">{user.email}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Member Since</p>
              <p className="mt-2 text-sm text-white">{formatMemberSince(user.created_at)}</p>
            </div>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="rounded-[2rem] border border-slate-800 bg-slate-950/80 p-8">
          <div className="grid gap-5 md:grid-cols-2">
            <label className="block">
              <span className="text-xs uppercase tracking-[0.25em] text-slate-500">Full Name</span>
              <input
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                required
                minLength={2}
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500"
              />
            </label>

            <label className="block">
              <span className="text-xs uppercase tracking-[0.25em] text-slate-500">Job Title</span>
              <input
                type="text"
                value={jobTitle}
                onChange={(event) => setJobTitle(event.target.value)}
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500"
              />
            </label>

            <label className="block">
              <span className="text-xs uppercase tracking-[0.25em] text-slate-500">Company</span>
              <input
                type="text"
                value={companyName}
                onChange={(event) => setCompanyName(event.target.value)}
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500"
              />
            </label>

            <label className="block">
              <span className="text-xs uppercase tracking-[0.25em] text-slate-500">Timezone</span>
              <input
                type="text"
                value={timezone}
                onChange={(event) => setTimezone(event.target.value)}
                placeholder="America/New_York"
                className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500"
              />
            </label>
          </div>

          <label className="mt-5 block">
            <span className="text-xs uppercase tracking-[0.25em] text-slate-500">Bio</span>
            <textarea
              value={bio}
              onChange={(event) => setBio(event.target.value)}
              rows={6}
              placeholder="Tell your collaborators what you build, what stack you use, or how you want AeroSwarm to work with you."
              className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm leading-7 text-white outline-none transition focus:border-sky-500"
            />
          </label>
        </div>

        <aside className="rounded-[2rem] border border-slate-800 bg-slate-950/80 p-8">
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Account Summary</p>
          <div className="mt-4 space-y-4 text-sm text-slate-300">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Display Identity</p>
              <p className="mt-2 text-white">{fullName || "Not set yet"}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Work Context</p>
              <p className="mt-2 text-white">{jobTitle || "Role not provided"}</p>
              <p className="mt-1 text-slate-400">{companyName || "Company not provided"}</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Timezone</p>
              <p className="mt-2 text-white">{timezone || "Timezone not provided"}</p>
            </div>
          </div>

          {notice && <p className="mt-5 text-sm text-emerald-300">{notice}</p>}
          {error && <p className="mt-5 text-sm text-rose-300">{error}</p>}

          <button
            type="submit"
            disabled={saving}
            className="mt-6 w-full rounded-2xl bg-sky-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-sky-400 disabled:bg-slate-700 disabled:text-slate-400"
          >
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </aside>
      </form>
    </section>
  );
}
