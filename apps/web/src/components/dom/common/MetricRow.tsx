export function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
    </div>
  );
}
