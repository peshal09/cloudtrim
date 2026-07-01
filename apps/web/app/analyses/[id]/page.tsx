"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Badge } from "../../components/badges";
import { Charts } from "../../components/charts";
import {
  AnalysisAggregate,
  AnalysisSummary,
  Finding,
  FindingDetail,
  Narrative,
  Risk,
  Severity,
  getAnalysis,
  getFinding,
  getNarrative,
  getSummary,
  listFindings,
  money,
  reportUrl,
} from "../../lib/api";

const SEV_RANK: Record<string, number> = { high: 3, medium: 2, low: 1 };
type SortKey = "savings" | "severity" | "risk";

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>();
  const [summary, setSummary] = useState<AnalysisSummary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [narrative, setNarrative] = useState<Narrative | null>(null);
  const [aggregate, setAggregate] = useState<AnalysisAggregate | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("savings");
  const [sevFilter, setSevFilter] = useState<"all" | Severity>("all");
  const [riskFilter, setRiskFilter] = useState<"all" | Risk>("all");
  const [savingsOnly, setSavingsOnly] = useState(false);
  const [selected, setSelected] = useState<FindingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    async function load() {
      try {
        const s = await getAnalysis(id);
        if (cancelled) return;
        setSummary(s);
        if (s.status !== "complete") {
          timer = setTimeout(load, 1500); // poll while the worker runs
          return;
        }
        const [f, n, agg] = await Promise.all([
          listFindings(id),
          getNarrative(id),
          getSummary(id),
        ]);
        if (cancelled) return;
        setFindings(f);
        setNarrative(n);
        setAggregate(agg);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Load failed");
      }
    }

    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  const visible = useMemo(() => {
    const rows = findings.filter(
      (f) =>
        (sevFilter === "all" || f.severity === sevFilter) &&
        (riskFilter === "all" || f.risk === riskFilter) &&
        (!savingsOnly || f.monthly_savings > 0),
    );
    rows.sort((a, b) => {
      if (sortKey === "savings") return b.monthly_savings - a.monthly_savings;
      if (sortKey === "severity")
        return SEV_RANK[b.severity] - SEV_RANK[a.severity];
      return SEV_RANK[b.risk] - SEV_RANK[a.risk];
    });
    return rows;
  }, [findings, sortKey, sevFilter, riskFilter, savingsOnly]);

  if (error)
    return <main className="p-8 text-red-600">Error: {error}</main>;
  if (!summary) return <main className="p-8 text-gray-500">Loading…</main>;

  if (summary.status !== "complete") {
    return (
      <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center gap-4 p-8 text-center">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-gray-300 border-t-gray-900" />
        <p className="text-lg font-medium capitalize">{summary.status}…</p>
        <p className="text-sm text-gray-500">
          Your analysis is queued on the worker. This page will update automatically.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl p-8">
      <div className="flex items-center justify-between">
        <Link href="/" className="text-sm text-gray-500 hover:underline">
          ← New analysis
        </Link>
        <div className="flex gap-2">
          <a
            href={reportUrl(id, "md")}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Export .md
          </a>
          <a
            href={reportUrl(id, "pdf")}
            className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-700"
          >
            Export PDF
          </a>
        </div>
      </div>

      {/* Savings hero + severity breakdown */}
      <section className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-200 p-6 sm:col-span-2">
          <p className="text-sm text-gray-500">Identified monthly savings</p>
          <p className="mt-1 text-4xl font-bold text-emerald-600">
            {money(summary.total_monthly_savings)}
          </p>
          <p className="mt-1 text-sm text-gray-500">
            across {summary.findings_count} findings
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 p-6">
          <p className="text-sm text-gray-500">By severity</p>
          <div className="mt-3 flex flex-col gap-2">
            {(["high", "medium", "low"] as const).map((s) => (
              <div key={s} className="flex items-center justify-between">
                <Badge level={s} />
                <span className="font-medium">{summary.severity_counts[s]}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Prioritization narrative */}
      {narrative && (
        <section className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">
              Prioritization
            </h2>
            <span className="text-xs text-gray-400">
              source: {narrative.source}
            </span>
          </div>
          <p className="mt-2 whitespace-pre-line text-sm text-gray-800">
            {narrative.text}
          </p>
        </section>
      )}

      {/* Charts */}
      {aggregate && <Charts aggregate={aggregate} />}

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-center gap-3 text-sm">
        <FilterSelect
          label="Severity"
          value={sevFilter}
          onChange={(v) => setSevFilter(v as "all" | Severity)}
        />
        <FilterSelect
          label="Risk"
          value={riskFilter}
          onChange={(v) => setRiskFilter(v as "all" | Risk)}
        />
        <label className="flex items-center gap-1.5 text-gray-700">
          <input
            type="checkbox"
            checked={savingsOnly}
            onChange={(e) => setSavingsOnly(e.target.checked)}
          />
          With savings only
        </label>
        <span className="text-gray-400">
          {visible.length} of {findings.length}
        </span>
      </div>

      {/* Findings table */}
      <section className="mt-3 overflow-hidden rounded-xl border border-gray-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-gray-600">
            <tr>
              <th className="px-4 py-2">Finding</th>
              <SortHead label="Severity" k="severity" sortKey={sortKey} set={setSortKey} />
              <SortHead label="Risk" k="risk" sortKey={sortKey} set={setSortKey} />
              <SortHead label="Savings/mo" k="savings" sortKey={sortKey} set={setSortKey} />
            </tr>
          </thead>
          <tbody>
            {visible.map((f) => (
              <tr
                key={f.id}
                onClick={() => getFinding(f.id).then(setSelected)}
                className="cursor-pointer border-t border-gray-100 hover:bg-gray-50"
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{f.title}</div>
                  <div className="text-xs text-gray-500">{f.detector}</div>
                </td>
                <td className="px-4 py-3">
                  <Badge level={f.severity} />
                </td>
                <td className="px-4 py-3">
                  <Badge level={f.risk} />
                </td>
                <td className="px-4 py-3 font-medium text-emerald-600">
                  {f.monthly_savings > 0 ? money(f.monthly_savings) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {selected && (
        <Drawer detail={selected} onClose={() => setSelected(null)} />
      )}
    </main>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 text-gray-700">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-300 px-2 py-1"
      >
        <option value="all">all</option>
        <option value="high">high</option>
        <option value="medium">medium</option>
        <option value="low">low</option>
      </select>
    </label>
  );
}

function SortHead({
  label,
  k,
  sortKey,
  set,
}: {
  label: string;
  k: SortKey;
  sortKey: SortKey;
  set: (k: SortKey) => void;
}) {
  return (
    <th
      onClick={() => set(k)}
      className={`cursor-pointer select-none px-4 py-2 ${
        sortKey === k ? "text-gray-900" : ""
      }`}
    >
      {label} {sortKey === k ? "▾" : ""}
    </th>
  );
}

function Drawer({
  detail,
  onClose,
}: {
  detail: FindingDetail;
  onClose: () => void;
}) {
  const { finding, resource } = detail;
  return (
    <div className="fixed inset-0 z-10 flex justify-end bg-black/30" onClick={onClose}>
      <aside
        onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold">{finding.title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700">
            ✕
          </button>
        </div>

        <div className="mt-2 flex gap-2">
          <Badge level={finding.severity} label={`severity: ${finding.severity}`} />
          <Badge level={finding.risk} label={`risk: ${finding.risk}`} />
        </div>

        {resource && (
          <p className="mt-3 text-sm text-gray-600">
            <code>{resource.identifier}</code> · {resource.type}
            {resource.region ? ` · ${resource.region}` : ""}
          </p>
        )}

        <div className="mt-4 rounded-lg bg-emerald-50 p-3">
          <div className="text-sm text-gray-600">
            {money(finding.current_cost)}/mo → {money(finding.projected_cost)}/mo
          </div>
          <div className="text-lg font-semibold text-emerald-700">
            Save {money(finding.monthly_savings)}/mo
          </div>
        </div>

        <Section title="Explanation">
          <p className="text-sm text-gray-800">{finding.explanation}</p>
          {finding.explanation_source && (
            <p className="mt-1 text-xs text-gray-400">
              source: {finding.explanation_source}
            </p>
          )}
        </Section>

        {finding.remediation_diff && (
          <Section title="Proposed change">
            <pre className="overflow-x-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100">
              {finding.remediation_diff}
            </pre>
          </Section>
        )}

        <Section title="Evidence">
          <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
            {JSON.stringify(finding.evidence, null, 2)}
          </pre>
        </Section>
      </aside>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
        {title}
      </h3>
      <div className="mt-1">{children}</div>
    </div>
  );
}
