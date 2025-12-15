import useSWR from "swr";
import { useEffect, useRef } from "react";

export interface Mail {
  id: string;
  uid: number;
  from: string;
  to: string[];
  subject: string;
  date: string;
  html: string;
  text: string;
  phishing: boolean;
  score: number;
  attachments: string[];
  skipped_attachments?: string[];
  deleted?: boolean;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useMailStream() {
  const { data, mutate } = useSWR<Mail[]>("/api/mails", fetcher, {
    refreshInterval: 60000,
    revalidateOnFocus: true,
  });
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (eventSourceRef.current) return;
    const es = new EventSource("http://127.0.0.1:8000/mails/stream");
    eventSourceRef.current = es;
    es.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data);
        mutate((prev) => prev ? [parsed, ...prev] : [parsed], false);
      } catch {}
    };
    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [mutate]);

  return {
    mails: data || [],
    mutate,
  };
} 