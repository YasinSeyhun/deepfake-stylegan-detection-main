import React from "react";
import { Mail } from "@/hooks/useMailStream";

interface MailListProps {
  mails: Mail[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

export default function MailList({ mails, selectedId, onSelect }: MailListProps) {
  return (
    <div className="flex flex-col gap-3">
      {mails.map((mail) => (
        <button
          key={mail.id}
          onClick={() => onSelect(mail.id)}
          className={`w-full text-left rounded-xl p-4 shadow transition-all flex flex-col gap-1 bg-neutral-800/80 hover:bg-neutral-700/80 border-2 ${
            mail.id === selectedId ? "border-blue-500" : "border-transparent"
          } ${mail.phishing ? "ring-2 ring-red-500" : ""}`}
        >
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white truncate max-w-[10rem]">{mail.subject || "(No Subject)"}</span>
            {mail.phishing && (
              <span className="ml-2 px-2 py-0.5 rounded bg-red-600 text-xs text-white font-bold">Phishing</span>
            )}
          </div>
          <span className="text-xs text-zinc-400 truncate max-w-[10rem]">{mail.from}</span>
          <span className="text-xs text-zinc-500">{new Date(mail.date).toLocaleString()}</span>
        </button>
      ))}
    </div>
  );
} 