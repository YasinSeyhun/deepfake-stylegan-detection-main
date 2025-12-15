'use client';
// -- coding: utf-8 --
import React, { useState, useEffect } from "react";
import TemplateSelector from "@/components/ui/TemplateSelector";
import ImagePicker from "@/components/ui/ImagePicker";
import { Navbar } from "@/components/ui/mini-navbar";
import { Button } from "@/components/ui/button";
import { Component as EtheralShadows } from "@/components/ui/etheral-shadows";

interface Target {
  email: string;
  first_name: string;
  last_name: string;
  selected?: boolean;
}

export default function MailSenderPage() {
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [htmlBody, setHtmlBody] = useState<string>("");
  const [targets, setTargets] = useState<Target[]>([]);
  const [progress, setProgress] = useState<number>(0);
  const [sending, setSending] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [success, setSuccess] = useState<boolean>(false);
  const [subject, setSubject] = useState<string>("");
  const [singleEmail, setSingleEmail] = useState<string>("");
  const [uploadingImage, setUploadingImage] = useState<boolean>(false);
  const [mailTitle, setMailTitle] = useState<string>("");
  const [mailDescription, setMailDescription] = useState<string>("");
  const [buttonText, setButtonText] = useState<string>("Hesabımı Kontrol Et");
  const [buttonUrl, setButtonUrl] = useState<string>("https://example.com/verify");

  // Şablon seçildiğinde otomatik olarak HTML body'yi doldur
  useEffect(() => {
    if (selectedTemplate) {
      fetch(`/mail_templates/${selectedTemplate}`)
        .then(res => res.json())
        .then(data => setHtmlBody(data.html_body || ""));
    }
  }, [selectedTemplate]);

  // Otomatik HTML template
  useEffect(() => {
    const html = `
<html>
  <body style="background: #18181b; font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0;">
    <div style="max-width: 420px; margin: 40px auto; background: #23232a; border-radius: 18px; box-shadow: 0 4px 24px #0002; padding: 32px 24px; text-align: center; color: #fff;">
      <h2 style="color: #ff5252; font-size: 2rem; margin-bottom: 18px; letter-spacing: 1px;">${mailTitle}</h2>
      <div style="display: flex; justify-content: center; margin-bottom: 18px;">
        <img src="cid:resim1" alt="Avatar" style="width: 96px; height: 96px; border-radius: 50%; object-fit: cover; box-shadow: 0 2px 8px #0005; border: 3px solid #ff5252; background: #fff;" />
      </div>
      <p style="font-size: 1.1rem; margin-bottom: 24px; color: #e0e0e0;">${mailDescription}</p>
      <a href="${buttonUrl}" style="display: inline-block; padding: 12px 32px; background: linear-gradient(90deg, #ff5252 60%, #ff1744 100%); color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 1rem; box-shadow: 0 2px 8px #0003; transition: background 0.2s;">${buttonText}</a>
    </div>
  </body>
</html>
`;
    setHtmlBody(html);
  }, [mailTitle, mailDescription, buttonText, buttonUrl]);

  // CSV upload handler
  function handleCSVUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target?.result as string;
      const lines = text.split(/\r?\n/).filter(Boolean);
      const [header, ...rows] = lines;
      const cols = header.split(",");
      const emailIdx = cols.indexOf("email");
      const firstIdx = cols.indexOf("first_name");
      const lastIdx = cols.indexOf("last_name");
      const parsed: Target[] = rows.map(row => {
        const vals = row.split(",");
        return {
          email: vals[emailIdx],
          first_name: vals[firstIdx],
          last_name: vals[lastIdx],
          selected: true,
        };
      });
      setTargets(parsed);
    };
    reader.readAsText(file);
  }

  // Alıcı seçimini değiştir
  function toggleTarget(idx: number) {
    setTargets(tgts => tgts.map((t, i) => i === idx ? { ...t, selected: !t.selected } : t));
  }

  // Tekil e-posta ekle
  function handleAddSingleEmail() {
    if (!singleEmail || !singleEmail.includes("@")) return;
    setTargets(prev => [
      ...prev,
      { email: singleEmail, first_name: "", last_name: "", selected: true }
    ]);
    setSingleEmail("");
  }

  // Görsel yükle
  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch("http://127.0.0.1:8000/upload-image", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error("Yükleme başarısız!");
      const data = await res.json();
      setSelectedImage(data.filename); // image_name olarak backend'den dönen dosya adını kullan
    } catch {
      alert("Görsel yüklenemedi.");
    } finally {
      setUploadingImage(false);
    }
  }

  // Gönderim başlat
  async function handleSend() {
    setSending(true);
    setProgress(0);
    setError("");
    setSuccess(false);
    try {
      const selectedTargets = targets.filter(t => t.selected).map(t => t.email);
      const payload = {
        subject: subject || "Phishing Test",
        html_body: htmlBody,
        image_name: selectedImage,
        targets: selectedTargets,
      };
      const token = localStorage.getItem("token");
      // 1. POST ile task başlat, task_id al
      const res = await fetch("http://127.0.0.1:8000/send-phishing", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        setError("Gönderim başlatılamadı: " + (await res.text()));
        setSending(false);
        return;
      }
      const data = await res.json();
      const taskId = data.task_id;
      if (!taskId) {
        setError("task_id alınamadı.");
        setSending(false);
        return;
      }
      // 2. SSE ile ilerleme takibi
      const sse = new EventSource(`http://127.0.0.1:8000/send-phishing/${taskId}`);
      sse.onmessage = (e) => {
        const percent = parseInt(e.data);
        setProgress(percent);
        if (percent >= 100) {
          setSending(false);
          setSuccess(true);
          sse.close();
        }
      };
      sse.onerror = () => {
        setError("Bağlantı hatası veya gönderim tamamlandı.");
        setSending(false);
        sse.close();
      };
    } catch (err: unknown) {
      let msg = "Beklenmeyen hata";
      if (err && typeof err === "object" && "message" in err) {
        msg = (err as { message?: string }).message || msg;
      }
      setError("Beklenmeyen hata: " + msg);
      setSending(false);
    }
  }

  return (
    <>
      <div className="relative min-h-screen" style={{ overflow: 'visible' }}>
        <EtheralShadows
          sizing="fill"
          color="rgba(128,128,128,0.15)"
          animation={{ scale: 60, speed: 40 }}
          noise={{ opacity: 0.2, scale: 2 }}
          style={{ position: 'absolute', inset: 0, zIndex: -1 }}
        />
        <div style={{ position: 'relative', zIndex: 1 }}>
      <Navbar />
          <div className="flex flex-col items-center min-h-screen bg-black/40 py-12 px-2">
            <div className="w-full max-w-5xl bg-neutral-900/40 rounded-2xl shadow-lg p-8 flex flex-col md:flex-row gap-8 mt-8">
          {/* Sol panel */}
          <div className="flex-1 flex flex-col gap-8 mt-4">
            <h2 className="text-2xl font-bold text-white mb-4">Phishing Mail Gönder</h2>
            <div className="flex flex-col gap-4">
              <label className="block font-semibold text-white">Konu (Subject):</label>
              <input
                className="w-full p-3 rounded-xl shadow bg-neutral-800 text-white border border-neutral-700 focus:border-blue-500 focus:outline-none"
                value={subject}
                onChange={e => setSubject(e.target.value)}
                placeholder="E-posta konusu girin..."
              />
            </div>
            <div className="flex flex-col gap-4">
              <label className="block font-semibold text-white">Başlık</label>
              <input
                className="w-full p-3 rounded-xl shadow bg-neutral-800 text-white border border-neutral-700 focus:border-blue-500 focus:outline-none"
                value={mailTitle}
                onChange={e => setMailTitle(e.target.value)}
                placeholder="Güvenlik Uyarısı"
              />
            </div>
            <div className="flex flex-col gap-4">
              <label className="block font-semibold text-white">Açıklama</label>
              <textarea
                className="w-full min-h-[80px] p-4 rounded-xl shadow bg-neutral-800 text-white border border-neutral-700 focus:border-blue-500 focus:outline-none"
                value={mailDescription}
                onChange={e => setMailDescription(e.target.value)}
                placeholder="Hesabınızda olağandışı bir oturum algılandı. Lütfen şifrenizi doğrulayın."
              />
            </div>
            <div className="flex gap-4 mb-2">
              <div className="flex-1 flex flex-col gap-2">
                <label className="block font-semibold text-white">Buton Metni</label>
                <input
                  className="w-full p-3 rounded-xl shadow bg-neutral-800 text-white border border-neutral-700 focus:border-blue-500 focus:outline-none"
                  value={buttonText}
                  onChange={e => setButtonText(e.target.value)}
                  placeholder="Hesabımı Kontrol Et"
                />
              </div>
              <div className="flex-1 flex flex-col gap-2">
                <label className="block font-semibold text-white">Buton Linki</label>
                <input
                  className="w-full p-3 rounded-xl shadow bg-neutral-800 text-white border border-neutral-700 focus:border-blue-500 focus:outline-none"
                  value={buttonUrl}
                  onChange={e => setButtonUrl(e.target.value)}
                  placeholder="https://example.com/verify"
                />
              </div>
            </div>
            <div className="flex flex-col gap-4 mt-2">
              <label className="block font-semibold text-white">Tek Alıcı Ekle</label>
              <div className="flex gap-2">
                <input
                  type="email"
                  className="flex-1 p-3 rounded-xl bg-neutral-800 text-white border border-neutral-700 focus:border-blue-500 focus:outline-none"
                  value={singleEmail}
                  onChange={e => setSingleEmail(e.target.value)}
                  placeholder="ornek@eposta.com"
                />
                <Button
                  className="px-4 py-2 rounded-xl font-semibold"
                  onClick={handleAddSingleEmail}
                >
                  Ekle
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-4 mt-2">
              <label className="block font-semibold text-white">CSV ile Alıcıları Yükle</label>
              <input type="file" accept=".csv" onChange={handleCSVUpload} className="text-white" />
              {targets.length > 0 && (
                <div className="max-h-40 overflow-y-auto border rounded-xl p-2 bg-neutral-800 text-white mt-2">
                  <div className="mb-2 font-semibold text-blue-300">Seçili Alıcılar:</div>
                  {targets.filter(t => t.selected).map((t, i) => (
                    <label key={t.email} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={!!t.selected} onChange={() => toggleTarget(i)} />
                      <span>{t.email} ({t.first_name} {t.last_name})</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
          {/* Sağ panel */}
          <div className="flex-1 flex flex-col gap-8 mt-4">
            <TemplateSelector onSelect={setSelectedTemplate} />
            <div className="flex flex-col gap-4">
              <label className="block font-semibold text-white">Görsel Yükle</label>
              <input type="file" accept="image/*" onChange={handleImageUpload} className="text-white" />
              {uploadingImage && <span className="text-xs text-blue-300 ml-2">Yükleniyor...</span>}
              <ImagePicker selected={selectedImage} onSelect={setSelectedImage} />
              {selectedImage && (
                <div className="mt-2 text-sm text-blue-300">Seçili Görsel: <span className="font-mono">{selectedImage}</span></div>
              )}
            </div>
          </div>
        </div>
        <div className="w-full max-w-5xl flex flex-col items-center mt-12">
          <Button
            className="px-10 py-4 rounded-2xl font-bold text-lg"
            onClick={handleSend}
            disabled={sending || !selectedImage || !htmlBody || targets.filter(t => t.selected).length === 0 || !subject}
          >
            Gönder
          </Button>
          {sending && (
            <div className="w-full max-w-md mt-4">
              <div className="bg-neutral-800 rounded-full h-6 overflow-hidden">
                <div
                  className="bg-blue-500 h-6 transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="text-center text-white mt-2">Gönderiliyor... %{progress}</div>
            </div>
          )}
          {error && <div className="text-red-500 mt-4">{error}</div>}
          {success && <div className="text-green-500 mt-4">Gönderim tamamlandı!</div>}
            </div>
          </div>
        </div>
      </div>
    </>
  );
} 