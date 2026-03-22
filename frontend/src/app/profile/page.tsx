import type { Metadata } from "next";
import { DashboardApp } from "@/components/DashboardApp";

export const metadata: Metadata = {
  title: "Profile",
  robots: {
    index: false,
    follow: false,
  },
};

export default function ProfilePage() {
  return <DashboardApp routeView="profile" />;
}
