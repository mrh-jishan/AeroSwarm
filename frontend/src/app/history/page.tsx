import type { Metadata } from "next";
import { DashboardApp } from "@/components/DashboardApp";

export const metadata: Metadata = {
  title: "Session History",
  robots: {
    index: false,
    follow: false,
  },
};

export default function HistoryPage() {
  return <DashboardApp routeView="history" />;
}
