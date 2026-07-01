"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnalysisAggregate } from "../lib/api";

const SEV_COLORS: Record<string, string> = {
  high: "#dc2626",
  medium: "#d97706",
  low: "#9ca3af",
};

export function Charts({ aggregate }: { aggregate: AnalysisAggregate }) {
  const savings = Object.entries(aggregate.savings_by_detector)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const severity = (["high", "medium", "low"] as const).map((s) => ({
    name: s,
    value: aggregate.severity_counts[s] ?? 0,
  }));

  return (
    <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div className="rounded-xl border border-gray-200 p-4">
        <h3 className="mb-2 text-sm font-semibold text-gray-700">
          Savings by detector ($/mo)
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={savings} margin={{ left: 8, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} height={50} textAnchor="end" />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
            <Bar dataKey="value" fill="#059669" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-xl border border-gray-200 p-4">
        <h3 className="mb-2 text-sm font-semibold text-gray-700">
          Findings by severity
        </h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={severity} margin={{ left: 8, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {severity.map((s) => (
                <Cell key={s.name} fill={SEV_COLORS[s.name]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
