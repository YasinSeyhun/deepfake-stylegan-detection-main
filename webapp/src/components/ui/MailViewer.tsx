import React, { useState } from "react";
import { Mail } from "@/hooks/useMailStream";
import DOMPurify from "isomorphic-dompurify";
import "./mailviewer.css";

interface MailViewerProps {
  mail?: Mail;
}

export default function MailViewer({ mail }: MailViewerProps) {
  const [modalImg, setModalImg] = useState<string | null>(null);
  if (!mail) {
    return <div className="flex items-center justify-center h-full text-zinc-400">Bir mail seçin…</div>;
  }
  return (
    <div className="flex flex-col gap-4">
      {mail.phishing && (
        <div className="p-3 rounded-lg bg-red-900/80 text-red-200 font-bold text-center shadow">
          Bu e-posta deepfake içeriyor, potansiyel phishing!
        </div>
      )}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
        <div>
          <div className="text-2xl font-bold text-white mb-1">{mail.subject || "(No Subject)"}</div>
          <div className="text-sm text-zinc-400 mb-1">{mail.from} → {mail.to.join(", ")}</div>
          <div className="text-xs text-zinc-500">{new Date(mail.date).toLocaleString()}</div>
        </div>
        <div className="flex flex-col items-end gap-1 min-w-[120px]">
          <span className="text-xs text-zinc-400">Dedektör Skoru</span>
          <div className="w-32 h-3 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-3 rounded-full bg-blue-500 transition-all"
              style={{ width: `${Math.round(mail.score)}%` }}
            />
          </div>
          <span className="text-xs text-zinc-300">%{Math.round(mail.score)}</span>
        </div>
      </div>
      <div
        className="my-2 prose prose-invert max-w-full bg-neutral-800/60 rounded-xl p-4 shadow max-h-[60vh] overflow-auto break-words prose-scrollbar"
        style={{ wordBreak: "break-word", overflowX: "auto" }}
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(mail.html) }}
      />
      {mail.attachments && mail.attachments.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-sm text-zinc-400">Ekler:</div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {mail.attachments.map((att, i) => (
              <img
                key={att}
                src={`/api/mails/${mail.id}/attachment/${encodeURIComponent(att.split("/").pop() || "")}`}
                alt={`attachment-${i}`}
                className="rounded-lg shadow cursor-pointer object-cover h-28 w-full border border-zinc-700 hover:scale-105 transition"
                onClick={() => setModalImg(`/api/mails/${mail.id}/attachment/${encodeURIComponent(att.split("/").pop() || "")}`)}
              />
            ))}
          </div>
        </div>
      )}
      {mail.skipped_attachments && mail.skipped_attachments.length > 0 && (
        <div className="mt-4">
          <div className="mb-2 text-sm text-yellow-400 font-semibold">Atlanan Ekler (boyut {'>'}2MB veya toplam {'>'}5):</div>
          <ul className="list-disc list-inside text-yellow-300 text-xs">
            {mail.skipped_attachments.map((fname) => (
              <li key={fname}>{fname}</li>
            ))}
          </ul>
        </div>
      )}
      {modalImg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80" onClick={() => setModalImg(null)}>
          <img src={modalImg} alt="attachment-full" className="max-h-[90vh] max-w-[90vw] rounded-lg shadow-2xl" />
        </div>
      )}
    </div>
  );
} 