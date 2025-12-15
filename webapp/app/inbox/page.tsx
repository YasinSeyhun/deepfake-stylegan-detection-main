"use client";
import React, { useState } from "react";
import { Navbar } from "@/components/ui/mini-navbar";
import { useMailStream } from "@/hooks/useMailStream";
import MailList from "@/components/ui/MailList";
import MailViewer from "@/components/ui/MailViewer";
import { Component as EtheralShadows } from "@/components/ui/etheral-shadows";

export default function InboxPage() {
  const { mails } = useMailStream();
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const sortedMails = [...mails].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  const selectedMail = sortedMails.find((m) => m.id === selectedId) || sortedMails[0];

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex flex-col relative overflow-hidden">
      <EtheralShadows
        sizing="fill"
        color="rgba(128,128,128,0.15)"
        animation={{ scale: 60, speed: 40 }}
        noise={{ opacity: 0.2, scale: 2 }}
        style={{ position: 'absolute', inset: 0, zIndex: 0 }}
      />
      <div style={{ position: 'relative', zIndex: 1 }}>
        <Navbar />
        {/* Sidebar: Mail List */}
        <aside className="fixed left-0 top-0 w-[400px] h-screen bg-[#18181b] shadow-xl z-20 flex flex-col p-4">
          <h2 className="text-lg font-bold mb-4 pl-2">Gelen Kutusu</h2>
          <div className="flex-1 min-h-0 overflow-y-auto prose-scrollbar pr-2">
            <MailList mails={sortedMails} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
        </aside>
        {/* Main: Mail Detail */}
        <main className="ml-[400px] flex-1 flex justify-center items-center min-h-screen">
          <div className="w-full max-w-5xl bg-neutral-900/90 rounded-2xl shadow-2xl p-10">
            <MailViewer mail={selectedMail} />
          </div>
        </main>
      </div>
    </div>
  );
} 