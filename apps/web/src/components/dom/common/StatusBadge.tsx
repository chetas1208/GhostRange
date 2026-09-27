type StatusBadgeProps = {
  status: string;
  tone?: 'neutral' | 'active' | 'success' | 'warning' | 'error';
};

export function StatusBadge({ status, tone = 'neutral' }: StatusBadgeProps) {
  return <span className={`status-badge tone-${tone}`}>{status}</span>;
}
