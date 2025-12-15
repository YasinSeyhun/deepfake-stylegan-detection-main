/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";

type MetricsBarChartProps = {
  data: { name: string; value: number }[];
  height?: number;
};

export function MetricsBarChart({ data, height = 180 }: MetricsBarChartProps) {
  // Radar chart için veri formatını ayarla
  const radarData = data.map(d => ({ metric: d.name, value: d.value }));
  // Tüm Recharts bileşenlerini as any ile kullan
  const RadarChartAny = RadarChart as any;
  const PolarGridAny = PolarGrid as any;
  const PolarAngleAxisAny = PolarAngleAxis as any;
  const PolarRadiusAxisAny = PolarRadiusAxis as any;
  const RadarAny = Radar as any;
  const ResponsiveContainerAny = ResponsiveContainer as any;

  return (
    <ResponsiveContainerAny width="100%" height={height}>
      <RadarChartAny data={radarData} outerRadius={200}>
        <PolarGridAny stroke="#444" />
        <PolarAngleAxisAny dataKey="metric" tick={{ fill: "#fff", fontWeight: 600, fontSize: 14 }} />
        <PolarRadiusAxisAny angle={30} domain={[0, 100]} tick={false} axisLine={false} />
        <RadarAny name="Metrikler" dataKey="value" stroke="#818cf8" fill="#818cf8" fillOpacity={0.5} />
      </RadarChartAny>
    </ResponsiveContainerAny>
  );
} 