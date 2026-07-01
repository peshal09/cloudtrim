"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createAnalysis, loadSample } from "./lib/api";

export default function UploadPage() {
  const router = useRouter();
  const [tf, setTf] = useState<File | null>(null);
  const [csv, setCsv] = useState<File | null>(null);
  const [k8s, setK8s] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function go(run: () => Promise<{ id: string }>) {
    setBusy(true);
    setError(null);
    try {
      const { id } = await run();
      router.push(`/analyses/${id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-8 p-8">
      <header className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">CloudTrim</h1>
        <p className="mt-2 text-gray-600">
          Shift-left cloud cost optimizer — a reviewer that remediates.
        </p>
        <Link
          href="/trends"
          className="mt-3 inline-block text-sm text-emerald-700 hover:underline"
        >
          Cost trends & anomaly detection →
        </Link>
      </header>

      <div className="rounded-xl border border-gray-200 p-6 shadow-sm">
        <label className="block text-sm font-medium text-gray-700">
          Terraform (.tf or plan JSON)
        </label>
        <input
          type="file"
          accept=".tf,.json"
          aria-label="Terraform file"
          onChange={(e) => setTf(e.target.files?.[0] ?? null)}
          className="mt-1 block w-full text-sm"
        />

        <label className="mt-4 block text-sm font-medium text-gray-700">
          Kubernetes manifests (optional)
        </label>
        <input
          type="file"
          accept=".yaml,.yml"
          aria-label="Kubernetes manifests"
          onChange={(e) => setK8s(e.target.files?.[0] ?? null)}
          className="mt-1 block w-full text-sm"
        />

        <label className="mt-4 block text-sm font-medium text-gray-700">
          Billing / utilization CSV (optional)
        </label>
        <input
          type="file"
          accept=".csv"
          aria-label="Billing CSV"
          onChange={(e) => setCsv(e.target.files?.[0] ?? null)}
          className="mt-1 block w-full text-sm"
        />

        <button
          disabled={(!tf && !k8s) || busy}
          onClick={() => go(() => createAnalysis(tf, csv, k8s))}
          className="mt-6 w-full rounded-lg bg-gray-900 py-2.5 font-medium text-white disabled:opacity-40"
        >
          {busy ? "Analyzing…" : "Analyze"}
        </button>

        <div className="my-4 flex items-center gap-3 text-xs text-gray-400">
          <div className="h-px flex-1 bg-gray-200" /> or{" "}
          <div className="h-px flex-1 bg-gray-200" />
        </div>

        <button
          disabled={busy}
          onClick={() => go(loadSample)}
          className="w-full rounded-lg border border-gray-300 py-2.5 font-medium text-gray-800 hover:bg-gray-50 disabled:opacity-40"
        >
          Load sample data
        </button>

        {error && (
          <p role="alert" className="mt-4 text-sm text-red-600">
            {error}
          </p>
        )}
      </div>

      {/* GitHub App — shift-left in code review (mocked "connect a repo" demo) */}
      <details className="rounded-xl border border-gray-200 p-5 text-sm">
        <summary className="cursor-pointer font-medium text-gray-800">
          Connect a repository — review cost in pull requests
        </summary>
        <div className="mt-3 space-y-2 text-gray-600">
          <p>
            CloudTrim ships as a GitHub App. On any PR touching{" "}
            <code>.tf</code>, it analyzes the change and comments the cost impact and
            waste — then, on <code>/cloudtrim fix</code>, opens a ready-to-merge PR
            that rightsizes the resources.
          </p>
          <ol className="list-decimal space-y-1 pl-5">
            <li>Install the CloudTrim GitHub App on your repo.</li>
            <li>
              Point the webhook at <code>/api/v1/github/webhook</code> with your
              signing secret.
            </li>
            <li>Open a PR — CloudTrim reviews it automatically.</li>
          </ol>
          <p className="text-gray-400">
            Setup guide: <code>docs/github-app.md</code>.
          </p>
        </div>
      </details>
    </main>
  );
}
