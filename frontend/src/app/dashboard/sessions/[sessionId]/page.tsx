import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Session Details",
  robots: {
    index: false,
    follow: false,
  },
};

interface DashboardSessionDetailsPageProps {
  params: Promise<{
    sessionId: string;
  }>;
}

export default async function DashboardSessionDetailsPage({
  params,
}: DashboardSessionDetailsPageProps) {
  const { sessionId } = await params;
  redirect(`/history/${sessionId}`);
}
