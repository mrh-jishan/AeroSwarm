import { NextResponse } from "next/server";

interface LeadPayload {
  source: "contact" | "pilot";
  name: string;
  email: string;
  company: string;
  role?: string;
  teamSize?: string;
  repoUrl?: string;
  workflowType?: string;
  message: string;
}

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function clean(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function buildLeadText(payload: LeadPayload) {
  return [
    `Source: ${payload.source}`,
    `Name: ${payload.name}`,
    `Email: ${payload.email}`,
    `Company: ${payload.company}`,
    `Role: ${payload.role || "n/a"}`,
    `Team Size: ${payload.teamSize || "n/a"}`,
    `Repository URL: ${payload.repoUrl || "n/a"}`,
    `Workflow Type: ${payload.workflowType || "n/a"}`,
    "",
    "Message:",
    payload.message,
  ].join("\n");
}

async function sendToWebhook(payload: LeadPayload) {
  const webhookUrl = process.env.LEADS_WEBHOOK_URL;

  if (!webhookUrl) {
    return false;
  }

  const response = await fetch(webhookUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(process.env.LEADS_WEBHOOK_BEARER_TOKEN
        ? { Authorization: `Bearer ${process.env.LEADS_WEBHOOK_BEARER_TOKEN}` }
        : {}),
    },
    body: JSON.stringify({
      ...payload,
      submittedAt: new Date().toISOString(),
      product: "AeroSwarm",
    }),
  });

  if (!response.ok) {
    throw new Error(`Lead webhook returned ${response.status}.`);
  }

  return true;
}

async function sendWithResend(payload: LeadPayload) {
  const apiKey = process.env.RESEND_API_KEY;
  const to = process.env.LEADS_EMAIL_TO;
  const from = process.env.LEADS_FROM_EMAIL;

  if (!apiKey || !to || !from) {
    return false;
  }

  const response = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from,
      to: [to],
      reply_to: payload.email,
      subject: `[AeroSwarm] ${payload.source === "pilot" ? "Pilot request" : "Commercial inquiry"} from ${payload.company}`,
      text: buildLeadText(payload),
    }),
  });

  if (!response.ok) {
    throw new Error(`Resend returned ${response.status}.`);
  }

  return true;
}

export async function POST(request: Request) {
  let body: Partial<LeadPayload>;

  try {
    body = (await request.json()) as Partial<LeadPayload>;
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const payload: LeadPayload = {
    source: body.source === "pilot" ? "pilot" : "contact",
    name: clean(body.name),
    email: clean(body.email),
    company: clean(body.company),
    role: clean(body.role),
    teamSize: clean(body.teamSize),
    repoUrl: clean(body.repoUrl),
    workflowType: clean(body.workflowType),
    message: clean(body.message),
  };

  if (!payload.name || !payload.company || !payload.message || !isValidEmail(payload.email)) {
    return NextResponse.json(
      { error: "Name, company, message, and a valid email are required." },
      { status: 400 },
    );
  }

  if (payload.message.length < 20) {
    return NextResponse.json(
      { error: "Add a bit more detail so the team can qualify the inquiry." },
      { status: 400 },
    );
  }

  try {
    const webhookDelivered = await sendToWebhook(payload);
    const emailDelivered = await sendWithResend(payload);

    if (!webhookDelivered && !emailDelivered) {
      if (process.env.NODE_ENV !== "production") {
        console.log("[AeroSwarm lead submission]", buildLeadText(payload));
      } else {
        return NextResponse.json(
          { error: "Lead delivery is not configured on this deployment." },
          { status: 500 },
        );
      }
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("[AeroSwarm lead submission failed]", error);
    return NextResponse.json(
      { error: "Submission could not be delivered. Try email or try again later." },
      { status: 502 },
    );
  }
}
