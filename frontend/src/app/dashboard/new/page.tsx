import type { Metadata } from "next";
import { DashboardApp } from "@/components/DashboardApp";

export const metadata: Metadata = {
  title: "New Session",
  robots: {
    index: false,
    follow: false,
  },
};

export default function DashboardNewSessionPage() {
  return <DashboardApp routeView="new" />;
}
