"use client";

import { useState } from "react";

type LeadSource = "contact" | "pilot";

interface LeadCaptureFormProps {
  source: LeadSource;
  submitLabel: string;
  successMessage: string;
  intro?: string;
}

interface LeadSubmissionState {
  status: "idle" | "submitting" | "success" | "error";
  message: string | null;
}

export function LeadCaptureForm({
  source,
  submitLabel,
  successMessage,
  intro,
}: LeadCaptureFormProps) {
  const [state, setState] = useState<LeadSubmissionState>({
    status: "idle",
    message: null,
  });

  async function handleSubmit(formData: FormData) {
    setState({ status: "submitting", message: null });

    try {
      const payload = {
        source,
        name: String(formData.get("name") ?? "").trim(),
        email: String(formData.get("email") ?? "").trim(),
        company: String(formData.get("company") ?? "").trim(),
        role: String(formData.get("role") ?? "").trim(),
        teamSize: String(formData.get("teamSize") ?? "").trim(),
        repoUrl: String(formData.get("repoUrl") ?? "").trim(),
        workflowType: String(formData.get("workflowType") ?? "").trim(),
        message: String(formData.get("message") ?? "").trim(),
      };

      const response = await fetch("/api/leads", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const result = (await response.json().catch(() => null)) as { error?: string } | null;

      if (!response.ok) {
        throw new Error(result?.error ?? "Submission failed.");
      }

      setState({
        status: "success",
        message: successMessage,
      });
    } catch (error) {
      setState({
        status: "error",
        message: error instanceof Error ? error.message : "Submission failed.",
      });
    }
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
      <h2 className="text-2xl font-semibold text-white">
        {source === "pilot" ? "Request a pilot" : "Send a commercial inquiry"}
      </h2>
      {intro ? <p className="mt-3 text-slate-300">{intro}</p> : null}
      <form
        action={handleSubmit}
        className="mt-6 grid gap-4"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 text-sm text-slate-300">
            <span>Name</span>
            <input
              name="name"
              required
              className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
              placeholder="Jane Doe"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            <span>Work email</span>
            <input
              name="email"
              type="email"
              required
              className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
              placeholder="jane@company.com"
            />
          </label>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 text-sm text-slate-300">
            <span>Company</span>
            <input
              name="company"
              required
              className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
              placeholder="Acme"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            <span>Role</span>
            <input
              name="role"
              className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
              placeholder="Engineering lead"
            />
          </label>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 text-sm text-slate-300">
            <span>Team size</span>
            <input
              name="teamSize"
              className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
              placeholder="8 engineers"
            />
          </label>
          <label className="grid gap-2 text-sm text-slate-300">
            <span>Repository or org URL</span>
            <input
              name="repoUrl"
              type="url"
              className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
              placeholder="https://github.com/org/repo"
            />
          </label>
        </div>
        <label className="grid gap-2 text-sm text-slate-300">
          <span>Workflow type</span>
          <input
            name="workflowType"
            className="rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
            placeholder={source === "pilot" ? "Refactor, migration, or review-heavy changes" : "Pilot, pricing, or deployment discussion"}
          />
        </label>
        <label className="grid gap-2 text-sm text-slate-300">
          <span>What are you trying to evaluate?</span>
          <textarea
            name="message"
            rows={6}
            required
            className="rounded-3xl border border-white/10 bg-slate-950 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-sky-400"
            placeholder="Describe the repo setup, workflow, and what success would look like."
          />
        </label>
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={state.status === "submitting"}
            className="rounded-full bg-sky-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {state.status === "submitting" ? "Sending..." : submitLabel}
          </button>
          {state.message ? (
            <p
              className={state.status === "error" ? "text-sm text-rose-300" : "text-sm text-emerald-300"}
            >
              {state.message}
            </p>
          ) : null}
        </div>
      </form>
    </section>
  );
}
