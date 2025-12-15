"use client";
import { BentoCard, BentoGrid } from "@/components/ui/bento-grid";
import { StarBorder } from "@/components/ui/star-border";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Navbar } from "@/components/ui/mini-navbar";
import React, { useEffect, useState } from "react";
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Component as EtheralShadows } from "@/components/ui/etheral-shadows";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

type Result = {
  label: string;
  score: number;
  image_id: string;
  file_name: string;
  date: string;
};

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleString();
}

function ResultsHistory() {
  const [results, setResults] = useState<Result[]>([]);
  useEffect(() => {
    fetch("http://127.0.0.1:8000/results")
      .then((res) => res.json())
      .then((data) => setResults(data));
  }, []);
  if (!results.length) return (
    <div className="w-full text-center text-gray-400 mb-8">Hiç eski sonuç yok.</div>
  );
  function goToResult(r: Result) {
    const params = new URLSearchParams({
      label: r.label,
      score: r.score.toString(),
      imageId: r.image_id,
    });
    window.location.href = `/results?${params.toString()}`;
  }
  return (
    <div className="w-full max-w-6xl mx-auto mb-8 mt-24">
      <h2 className="text-2xl font-bold mb-4 text-white">Geçmiş Sonuçlar</h2>
      <div className="overflow-x-auto rounded-2xl shadow-lg">
        <table className="min-w-full bg-neutral-900/80 text-white text-base">
          <thead>
            <tr>
              <th className="px-6 py-4">Dosya</th>
              <th className="px-6 py-4">Sonuç</th>
              <th className="px-6 py-4">Skor</th>
              <th className="px-6 py-4">Tarih</th>
              <th className="px-6 py-4">Görsel</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => (
              <tr
                key={i}
                className="border-t border-neutral-800 hover:bg-neutral-800/60 transition cursor-pointer group"
                onClick={() => goToResult(r)}
                tabIndex={0}
                style={{ height: 88 }}
              >
                <td className="px-6 py-4 max-w-[220px] truncate group-hover:underline">{r.file_name}</td>
                <td className="px-6 py-4 font-semibold capitalize">{r.label}</td>
                <td className="px-6 py-4">{typeof r.score === "number" ? (r.score).toFixed(2) : r.score}</td>
                <td className="px-6 py-4 whitespace-nowrap">{formatDate(r.date)}</td>
                <td className="px-6 py-4">
                  {r.image_id ? (
                    <img src={`http://127.0.0.1:8000/images/${r.image_id}`} alt="görsel" className="w-20 h-20 object-cover rounded-xl border border-neutral-700" />
                  ) : (
                    <span className="text-xs text-gray-500">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function ResultsPageContent() {
  const searchParams = useSearchParams();
  const label = searchParams.get("label");
  const confidence = searchParams.get("score");
  const imageId = searchParams.get("imageId");
  const gradcamUrlParam = searchParams.get("gradcam_url");
  const gradcamUrl = gradcamUrlParam
    ? `http://127.0.0.1:8000${gradcamUrlParam}`
    : imageId
      ? `http://127.0.0.1:8000/images/gradcam/gradcam_${imageId}.png`
      : null;
  const precision = Number(searchParams.get("precision")) || 0.80;
  const recall = Number(searchParams.get("recall")) || 0.82;
  const f1 = Number(searchParams.get("f1")) || 0.81;

  // Flip card state
  const [flipped, setFlipped] = React.useState(false);
  function handleFlip() {
    setFlipped((f) => !f);
  }

  // Dinamik toplam analiz sayısı
  const [totalAnaliz, setTotalAnaliz] = React.useState<number>(200);
  React.useEffect(() => {
    fetch("http://127.0.0.1:8000/results")
      .then((res) => res.json())
      .then((data) => setTotalAnaliz(data.length));
  }, []);

  // Sadece /results (query'siz) sayfasında geçmiş tabloyu göster
  const showHistory = !label && !confidence && !imageId;

  if (showHistory) {
    return (
      <>
        <Navbar />
        <div className="relative flex flex-col min-h-screen w-full items-center justify-center bg-background p-4 overflow-hidden">
          <EtheralShadows
            sizing="fill"
            color="rgba(128,128,128,0.15)"
            animation={{ scale: 60, speed: 40 }}
            noise={{ opacity: 0.2, scale: 2 }}
            style={{ position: 'absolute', inset: 0, zIndex: 0 }}
          />
          <div style={{ position: 'relative', zIndex: 1, width: '100%' }}>
            <ResultsHistory />
          </div>
        </div>
      </>
    );
  }
  if (!label || !confidence || !imageId) {
    return <div className="flex flex-col min-h-screen w-full items-center justify-center bg-background p-4"><div className="text-xl text-muted-foreground mt-32">Henüz analiz yapılmadı.</div></div>;
  }

  // Softmax skorlarını bar chart için hazırla
  let deepfakeScore = 0;
  let realScore = 0;
  if (label === "real") {
    realScore = Number(confidence);
    deepfakeScore = 100 - realScore;
  } else {
    deepfakeScore = Number(confidence);
    realScore = 100 - deepfakeScore;
  }
  const barData = {
    labels: ['Deepfake', 'Gerçek'],
    datasets: [
      {
        label: 'Olasılık (%)',
        data: [deepfakeScore, realScore],
        backgroundColor: [
          'rgba(239, 68, 68, 0.7)', // kırmızı
          'rgba(34, 197, 94, 0.7)', // yeşil
        ],
        borderRadius: 8,
      },
    ],
  };
  const barOptions = {
    indexAxis: 'y' as const,
    scales: {
      x: { min: 0, max: 100, ticks: { color: '#fff' }, grid: { color: '#333' } },
      y: { ticks: { color: '#fff' }, grid: { color: '#333' } },
    },
    plugins: {
      legend: { display: false },
      tooltip: { enabled: true },
    },
    responsive: true,
    maintainAspectRatio: false,
  };

  const result = {
    label: label === "real" ? "Gerçek" : "Deepfake",
    confidence: Number(confidence),
    imageUrl: `http://127.0.0.1:8000/images/${imageId}`,
    gradcamUrl,
    metrics: {
      accuracy: 0.815, // sabit kalabilir
      total: totalAnaliz, // dinamik
      precision,
      recall,
      f1,
    },
  };

  const features = [
    // Sol üst: Sonuç
    {
      customContent: (
        <div className="flex flex-col items-center justify-center h-full w-full gap-4">
          <span className={`px-4 py-2 rounded-full text-lg font-bold ${result.label === "Gerçek" ? "bg-green-500/20 text-green-600" : "bg-red-500/20 text-red-600"}`}>{`Sonuç: ${result.label}`}</span>
          <span className="text-sm text-muted-foreground">Güven: %{(result.confidence).toFixed(2)}</span>
        </div>
      ),
      className: "lg:col-start-1 lg:col-end-2 lg:row-start-1 lg:row-end-3",
    },
    // Orta: Yüklenen görsel + GradCAM flip
    {
      customContent: (
        <div className="flex flex-col items-center justify-center h-full w-full relative">
          <div
            className={`relative w-[420px] h-[420px] perspective cursor-pointer`}
            onClick={handleFlip}
            title={flipped ? "Orijinal görsele dön" : "Grad-CAM haritasını gör"}
          >
            <div className={`absolute w-full h-full transition-transform duration-500 [transform-style:preserve-3d] ${flipped ? "rotate-y-180" : ""}`}>
              <>
                {/* Ön yüz: Orijinal görsel */}
                <div className="absolute w-full h-full backface-hidden flex items-center justify-center rounded-3xl overflow-hidden">
                  <img src={result.imageUrl} alt="Yüklenen görsel" className="w-[420px] h-[420px] object-cover" />
                </div>
                {/* Arka yüz: GradCAM görseli + açıklama */}
                <div className="absolute w-full h-full backface-hidden rotate-y-180 flex flex-col items-center justify-center bg-neutral-900 rounded-3xl overflow-hidden shadow-lg">
                  {result.gradcamUrl ? (
                    <img src={result.gradcamUrl} alt="Grad-CAM" className="w-[300px] h-[300px] object-cover mb-2 rounded-2xl" />
                  ) : (
                    <span className="text-xs text-gray-400">Grad-CAM bulunamadı</span>
                  )}
                  <div className="text-xs text-gray-300 text-center px-2 w-[420px]">Modelin karar verirken en çok dikkat ettiği bölgeler kırmızı ile gösterilmiştir. (Attention Map)</div>
                </div>
              </>
            </div>
          </div>
          {/* Görselin altına açıklama */}
          <div className="mt-6 text-base text-white font-semibold drop-shadow bg-black/40 px-4 py-2 rounded-lg select-none text-center mx-auto w-fit">
            Grad-CAM ısı haritasını görmek için görsele tıklayın
          </div>
        </div>
      ),
      className: "lg:row-start-1 lg:row-end-4 lg:col-start-2 lg:col-end-3",
    },
    // Sol alt: Butonlar
    {
      customContent: (
        <div className="flex flex-row gap-2 w-full justify-center items-center">
          <StarBorder as={Link} href="/chat" className="max-w-xs px-2 py-1 text-sm">Görsel Analize Dön</StarBorder>
          <StarBorder as={Link} href="/results" className="max-w-xs px-2 py-1 text-sm">Sonuçlara Dön</StarBorder>
        </div>
      ),
      className: "lg:col-start-1 lg:col-end-2 lg:row-start-3 lg:row-end-4",
    },
    // Sağ üst: Model Performansı + metrik card grid (tek renk, açıklamalı, 1x4 yan yana)
    {
      customContent: (
        <div className="flex flex-col items-center justify-center h-full w-full gap-4">
          <div className="text-lg font-semibold mb-4">Model Performansı</div>
          {/* 1x4 grid of metric cards, tek renk neon gri */}
          <div className="grid grid-cols-4 gap-4 w-full max-w-3xl mb-2">
            {/* Accuracy */}
            <div className="flex flex-col items-center justify-center bg-black rounded-xl shadow border border-[#6b7280] p-4 neon-glow">
              <span className="text-xs text-gray-300 mb-1">Accuracy</span>
              <span className="text-2xl font-bold text-gray-100">%{(result.metrics.accuracy * 100).toFixed(2)}</span>
              <span className="text-xs text-gray-400 mt-1 text-center">Modelin tüm tahminlerindeki genel doğruluk oranı. Yani hem gerçek hem de deepfake görsellerdeki başarı yüzdesi.</span>
            </div>
            {/* Precision */}
            <div className="flex flex-col items-center justify-center bg-black rounded-xl shadow border border-[#6b7280] p-4 neon-glow">
              <span className="text-xs text-gray-300 mb-1">Precision</span>
              <span className="text-2xl font-bold text-gray-100">%{(result.metrics.precision * 100).toFixed(2)}</span>
              <span className="text-xs text-gray-400 mt-1 text-center">Modelin deepfake olarak işaretlediği görsellerin gerçekten deepfake olma oranı. Yanlış alarmı azaltma kabiliyeti.</span>
            </div>
            {/* Recall */}
            <div className="flex flex-col items-center justify-center bg-black rounded-xl shadow border border-[#6b7280] p-4 neon-glow">
              <span className="text-xs text-gray-300 mb-1">Recall</span>
              <span className="text-2xl font-bold text-gray-100">%{(result.metrics.recall * 100).toFixed(2)}</span>
              <span className="text-xs text-gray-400 mt-1 text-center">Gerçekten deepfake olan görsellerin model tarafından doğru şekilde yakalanma oranı. Kaçırılan deepfake&apos;leri azaltma kabiliyeti.</span>
            </div>
            {/* F1 */}
            <div className="flex flex-col items-center justify-center bg-black rounded-xl shadow border border-[#6b7280] p-4 neon-glow">
              <span className="text-xs text-gray-300 mb-1">F1</span>
              <span className="text-2xl font-bold text-gray-100">%{(result.metrics.f1 * 100).toFixed(2)}</span>
              <span className="text-xs text-gray-400 mt-1 text-center">Precision ve Recall&apos;un dengeli ortalaması. Modelin genel denge başarısı.</span>
            </div>
          </div>
          {/* Toplam analiz badge */}
          <div className="px-4 py-1 rounded-full bg-neutral-800 text-gray-200 text-xs font-semibold mb-2 shadow border border-neutral-700/40">Toplam analiz: {result.metrics.total}</div>
        </div>
      ),
      className: "lg:col-start-3 lg:col-end-3 lg:row-start-1 lg:row-end-3",
    },
    // Sağ alt: Bar chart (Deepfake/Real olasılıkları)
    {
      customContent: (
        <div className="flex flex-col items-center justify-center h-full w-full gap-4">
          <div className="w-full h-40">
            <Bar data={barData} options={barOptions} />
          </div>
        </div>
      ),
      className: "lg:col-start-3 lg:col-end-3 lg:row-start-3 lg:row-end-4",
    },
  ];

  return (
    <>
      <Navbar />
      <div className="relative flex flex-col min-h-screen w-full items-center justify-center bg-background p-4 overflow-hidden">
        <EtheralShadows
          sizing="fill"
          color="rgba(128,128,128,0.15)"
          animation={{ scale: 60, speed: 40 }}
          noise={{ opacity: 0.2, scale: 2 }}
          style={{ position: 'absolute', inset: 0, zIndex: 0 }}
        />
        <div style={{ position: 'relative', zIndex: 1, width: '100%' }}>
          <div className="mb-8 mt-4 w-full flex justify-center">
            {/* <GradualSpacing
            className="font-display text-center text-4xl font-bold -tracking-widest text-black dark:text-white md:text-7xl md:leading-[5rem]"
            text="Deepfake AI Sonuçları"
          /> */}
          </div>
          <BentoGrid className="w-full h-full min-h-[600px] lg:grid-rows-3">
            {features.map((feature, i) => (
              <BentoCard key={i} {...feature} />
            ))}
          </BentoGrid>
        </div>
      </div>
    </>
  );
}

export default function ResultsPage() {
  return (
    <React.Suspense fallback={<div className="flex h-screen w-full items-center justify-center">Yükleniyor...</div>}>
      <ResultsPageContent />
    </React.Suspense>
  );
}

/* Tailwind ile neon-glow efekti için ek CSS (global.css veya style etiketi ile eklenmeli):
.neon-glow {
  box-shadow: 0 0 12px 2px #6b7280cc, 0 0 2px 1px #23272f;
}
*/ 