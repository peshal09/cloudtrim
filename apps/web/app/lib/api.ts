export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Severity = "low" | "medium" | "high";
export type Risk = "low" | "medium" | "high";

export interface AnalysisSummary {
  id: string;
  status: string;
  created_at: string;
  total_monthly_savings: number;
  findings_count: number;
  severity_counts: Record<Severity, number>;
  source_meta: Record<string, unknown>;
}

export interface Finding {
  id: string;
  resource_id: string;
  detector: string;
  title: string;
  severity: Severity;
  risk: Risk;
  current_cost: number;
  projected_cost: number;
  monthly_savings: number;
  evidence: Record<string, unknown>;
  remediation_diff: string | null;
  confidence: number;
  explanation: string | null;
  explanation_source: "template" | "llm" | null;
}

export interface Resource {
  id: string;
  identifier: string;
  type: string;
  region: string | null;
  instance_type: string | null;
  monthly_cost: number | null;
  utilization: number | null;
  tags: Record<string, string>;
}

export interface FindingDetail {
  finding: Finding;
  resource: Resource | null;
}

export interface Narrative {
  text: string;
  source: "template" | "llm";
}

export interface AnalysisAggregate {
  realistic_monthly_savings: number;
  gross_monthly_savings: number;
  savings_by_detector: Record<string, number>;
  severity_counts: Record<string, number>;
  top_opportunities: unknown[];
}

export interface TrendPoint {
  id: string;
  created_at: string;
  total_monthly_savings: number;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export function createAnalysis(
  terraform: File | null,
  billing: File | null,
  kubernetes: File | null,
): Promise<AnalysisSummary> {
  const form = new FormData();
  if (terraform) form.append("terraform", terraform);
  if (billing) form.append("billing", billing);
  if (kubernetes) form.append("kubernetes", kubernetes);
  return fetch(`${API_URL}/api/v1/analyses`, { method: "POST", body: form }).then(
    json<AnalysisSummary>,
  );
}

export function loadSample(): Promise<AnalysisSummary> {
  return fetch(`${API_URL}/api/v1/analyses/sample`, { method: "POST" }).then(
    json<AnalysisSummary>,
  );
}

export function getAnalysis(id: string): Promise<AnalysisSummary> {
  return fetch(`${API_URL}/api/v1/analyses/${id}`).then(json<AnalysisSummary>);
}

export function listFindings(id: string): Promise<Finding[]> {
  return fetch(`${API_URL}/api/v1/analyses/${id}/findings`).then(
    json<Finding[]>,
  );
}

export function getFinding(id: string): Promise<FindingDetail> {
  return fetch(`${API_URL}/api/v1/findings/${id}`).then(json<FindingDetail>);
}

export function getNarrative(id: string): Promise<Narrative> {
  return fetch(`${API_URL}/api/v1/analyses/${id}/narrative`).then(
    json<Narrative>,
  );
}

export function getSummary(id: string): Promise<AnalysisAggregate> {
  return fetch(`${API_URL}/api/v1/analyses/${id}/summary`).then(
    json<AnalysisAggregate>,
  );
}

export function reportUrl(id: string, fmt: "md" | "pdf"): string {
  return `${API_URL}/api/v1/analyses/${id}/report.${fmt}`;
}

export function money(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD" });
}
