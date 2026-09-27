import { motion, AnimatePresence } from 'framer-motion';
import type { ReactNode } from 'react';
import { useGhostStore } from '../../state/store';

export function DetailSurface() {
  const selection = useGhostStore((s) => s.selection);
  const assets = useGhostStore((s) => s.assets);
  const worlds = useGhostStore((s) => s.worlds);
  const tasks = useGhostStore((s) => s.tasks);
  const workers = useGhostStore((s) => s.workers);
  const artifacts = useGhostStore((s) => s.artifacts);
  const claims = useGhostStore((s) => s.claims);
  const decisions = useGhostStore((s) => s.decisions);

  let body: ReactNode = null;

  if (selection?.kind === 'asset') {
    const a = assets[selection.id];
    if (a) {
      body = (
        <>
          <h2>{a.hostname}</h2>
          <Row label="OS" value={a.os_family} />
          <Row label="Role" value={a.role} />
          {a.fractured && <Row label="State" value="Compromised (fracture)" />}
        </>
      );
    }
  } else if (selection?.kind === 'world') {
    const w = worlds[selection.id];
    if (w) {
      body = (
        <>
          <h2>{w.label}</h2>
          <Row label="Status" value={w.status} />
          <Row label="World" value={w.id} />
          {w.failure_reason && <Row label="Reason" value={w.failure_reason} />}
        </>
      );
    }
  } else if (selection?.kind === 'task') {
    const t = tasks[selection.id];
    const d = Object.values(decisions).find((x) => x.task_id === t?.id);
    if (t) {
      body = (
        <>
          <h2>{t.label ?? t.id}</h2>
          <Row label="Status" value={t.status} />
          <Row label="Priority" value={String(t.priority ?? '—')} />
          {t.stopped_reason && <Row label="Stopped" value={t.stopped_reason} />}
          {d && (
            <>
              <Section title="Why GPU?" />
              {d.cpu_runtime_sec != null && <Row label="CPU est." value={`${d.cpu_runtime_sec} sec`} />}
              {d.gpu_runtime_sec != null && <Row label="GPU est." value={`${d.gpu_runtime_sec} sec`} />}
              <Row label="Incremental" value={`+$${d.estimated_cost_usd.toFixed(3)}`} />
              <Row label="Decision" value={d.reason_codes.join(', ')} />
            </>
          )}
        </>
      );
    }
  } else if (selection?.kind === 'worker') {
    const w = workers[selection.id];
    if (w) {
      body = (
        <>
          <h2>{w.id}</h2>
          <Row label="Class" value={w.resource_class} />
          <Row label="Status" value={w.status} />
          {w.provider && <Row label="Provider" value={w.provider} />}
          {w.provider_instance_id && (
            <Row label="Vultr resource" value={w.provider_instance_id.slice(0, 18)} />
          )}
          <Row label="Region" value={w.region} />
          <Row label="Est. cost/hr" value={`$${w.cost_per_hour_usd.toFixed(3)}`} />
        </>
      );
    }
  } else if (selection?.kind === 'artifact') {
    const a = artifacts[selection.id];
    if (a) {
      body = (
        <>
          <h2>ARTIFACT #{a.id.slice(-4).toUpperCase()}</h2>
          <Row label="Type" value={a.artifact_type} />
          <Row label="World" value={a.world_id} />
          <Row label="Source" value={a.source_hostname ?? '—'} />
          <Row label="SHA-256" value={`${a.content_hash.slice(0, 8)}…`} />
          {a.command && (
            <>
              <Section title="Command" />
              <pre>{a.command}</pre>
            </>
          )}
          {a.output && (
            <>
              <Section title="Output" />
              <pre>{a.output}</pre>
            </>
          )}
        </>
      );
    }
  } else if (selection?.kind === 'claim') {
    const c = claims[selection.id];
    if (c) {
      body = (
        <>
          <h2>Claim</h2>
          <p className="claim">{c.statement}</p>
          <Row label="Anchored" value={c.anchored ? 'Yes' : 'Unstable'} />
          <Row label="Verified" value={c.verified ? 'Yes' : 'Pending'} />
        </>
      );
    }
  }

  return (
    <AnimatePresence>
      {body && (
        <motion.aside
          className="detail-surface"
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 16 }}
        >
          {body}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="row">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
    </div>
  );
}

function Section({ title }: { title: string }) {
  return <div className="section">{title}</div>;
}
