type LogViewerProps = {
  lines: string[];
  maxLines?: number;
};

export function LogViewer({ lines, maxLines = 80 }: LogViewerProps) {
  const visible = lines.slice(-maxLines);
  return (
    <div className="log-viewer" role="log" aria-live="polite">
      {visible.map((line, i) => (
        <div key={`${i}-${line.slice(0, 24)}`} className="log-line">
          {line}
        </div>
      ))}
    </div>
  );
}
