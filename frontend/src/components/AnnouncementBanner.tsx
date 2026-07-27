"use client";

import { useEffect } from "react";
import { useSignalR } from "@/lib/SignalRProvider";

export default function AnnouncementBanner() {
  const { announcement, setAnnouncement } = useSignalR();

  useEffect(() => {
    const hostname = window.location.hostname;
    fetch(`http://${hostname}:5000/api/announcements`)
      .then((r) => r.json())
      .then((d) => { if (d.message) setAnnouncement(d.message); })
      .catch(() => {});
  }, [setAnnouncement]);

  if (!announcement) return null;

  return (
    <div className="sticky top-0 z-50 flex items-center justify-center gap-3 bg-gradient-to-r from-red-600/90 via-red-500/90 to-amber-500/90 px-4 py-3 text-center text-sm font-bold text-white shadow-lg backdrop-blur-sm">
      <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
      <span>{announcement}</span>
    </div>
  );
}
