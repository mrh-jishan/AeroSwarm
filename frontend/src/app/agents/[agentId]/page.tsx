import type { Metadata } from "next";
import { DashboardApp } from "@/components/DashboardApp";

export const metadata: Metadata = {
  title: "Worker",
  robots: {
    index: false,
    follow: false,
  },
};

interface AgentPageProps {
  params: Promise<{
    agentId: string;
  }>;
}

export default async function AgentPage({ params }: AgentPageProps) {
  const { agentId } = await params;
  return <DashboardApp routeView="agent" agentId={agentId} />;
}
