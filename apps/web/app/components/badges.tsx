const COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-gray-100 text-gray-700",
};

export function Badge({ level, label }: { level: string; label?: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        COLORS[level] ?? "bg-gray-100 text-gray-700"
      }`}
    >
      {label ?? level}
    </span>
  );
}
