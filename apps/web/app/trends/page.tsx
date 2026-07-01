"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "../components/badges";
import { TrendReport, money, sampleAnomalies } from "../lib/api";

const COLORS = ["#059669", "#2563eb", "#d97706", "#7c3aed", "#dc2626"];

export default function TrendsPage() {
  const [report, setReport] = useState<TrendReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sampleAnomalies()
      .then(setReport)
      .catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
  }, []);

  // Merge per-service series into rows keyed by period for a multi-line chart.
  const { rows, services } = useMemo(() => {
    if (!report) return { rows: [], services: [] as string[] };
    const services = Object.keys(report.series);
    const periods = report.series[services[0]]?.map((p) => p.period) ?? [];
    const rows = periods.map((period, i) => {
      const row: Record<string, string | number> = { period };
      for (const s of services) row[s] = report.series[s][i]?.cost ?? 0;
      return row;
    });
    return { rows, services };
  }, [report]);

  if (error) return <main className="p-8 text-red-600">Error: {error}</main>;
  if (!report) return <main className="p-8 text-gray-500">Loading…</main>;

  return (
    <main className="mx-auto max-w-5xl p-8">
      <Link href="/" className="text-sm text-gray-500 hover:underline">
        ← Home
      </Link>
      <h1 className="mt-4 text-2xl font-bold">Cost trends & anomalies</h1>
      <p className="mt-1 text-sm text-gray-500">
        Robust (median + MAD) spike detection over historical spend, with a
        next-period forecast. Sample data.
      </p>

      <section className="mt-6 rounded-xl border border-gray-200 p-4">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={rows} margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip formatter={(v: number) => money(v)} />
            {services.map((s, i) => (
              <Line
                key={s}
                type="monotone"
                dataKey={s}
                stroke={COLORS[i % COLORS.length]}
                dot={false}
                isAnimationActive={false}
              />
            ))}
            {report.anomalies.map((a) => (
              <ReferenceDot
                key={`${a.service}-${a.period}`}
                x={a.period}
                y={a.actual_cost}
                r={6}
                fill="#dc2626"
                stroke="white"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-500">
          {services.map((s, i) => (
            <span key={s} className="flex items-center gap-1">
              <span
                className="inline-block h-2 w-3 rounded"
                style={{ background: COLORS[i % COLORS.length] }}
              />
              {s}
            </span>
          ))}
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-red-600" /> anomaly
          </span>
        </div>
      </section>

      <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-200 p-5 sm:col-span-2">
          <h2 className="text-sm font-semibold text-gray-700">Anomalies</h2>
          {report.anomalies.length === 0 ? (
            <p className="mt-2 text-sm text-gray-500">No spikes detected.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {report.anomalies.map((a) => (
                <li key={`${a.service}-${a.period}`} className="text-sm">
                  <Badge level={a.severity} />{" "}
                  <span className="text-gray-800">{a.note}.</span>{" "}
                  <span className="text-gray-400">
                    ({money(a.actual_cost)} vs {money(a.expected_cost)}, z={a.z_score})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700">Next-period forecast</h2>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {money(report.forecast_total)}
          </p>
          <div className="mt-2 space-y-1 text-sm text-gray-600">
            {Object.entries(report.forecast_by_service).map(([s, v]) => (
              <div key={s} className="flex justify-between">
                <span>{s}</span>
                <span>{money(v)}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
