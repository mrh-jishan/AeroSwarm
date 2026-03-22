import type { Metadata } from "next";
import { DashboardApp } from "@/components/DashboardApp";

export const metadata: Metadata = {
  title: "Session Details",
  robots: {
    index: false,
    follow: false,
  },
};

interface HistorySessionPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function HistorySessionPage({ params }: HistorySessionPageProps) {
  const { sessionId } = await params;
  return <DashboardApp routeView="session" sessionId={sessionId} />;
}
