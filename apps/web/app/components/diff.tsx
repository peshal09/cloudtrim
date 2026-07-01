export function DiffView({ diff }: { diff: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg bg-gray-900 p-3 text-xs leading-relaxed">
      {diff.split("\n").map((line, i) => {
        let color = "text-gray-300";
        if (line.startsWith("+++") || line.startsWith("---")) color = "text-gray-500";
        else if (line.startsWith("+")) color = "text-emerald-400";
        else if (line.startsWith("-")) color = "text-red-400";
        else if (line.startsWith("@@")) color = "text-cyan-400";
        return (
          <div key={i} className={color}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}
