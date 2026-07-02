"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export default function Home() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!user) return;
    if (user.role === "Jefe" || user.canViewDashboard) {
      router.replace("/dashboard");
    } else {
      router.replace("/soporte");
    }
  }, [user, router]);

  return null;
}
