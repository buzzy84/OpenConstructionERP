import { useEffect, useState } from 'react';
import type { Workstream } from './types';

interface Props {
  workstream: Workstream;
  disabled: boolean;
  onSave: (changes: { label: string; sort_order: number; enabled: boolean }) => Promise<unknown>;
}
export default function WorkstreamConfigRow({ workstream, disabled, onSave }: Props) {
  const [label, setLabel] = useState(workstream.label);
  const [order, setOrder] = useState(workstream.sort_order);
  const [enabled, setEnabled] = useState(workstream.enabled);
  useEffect(() => {
    setLabel(workstream.label);
    setOrder(workstream.sort_order);
    setEnabled(workstream.enabled);
  }, [workstream]);
  const changed = label !== workstream.label || order !== workstream.sort_order || enabled !== workstream.enabled;
  return <div className="flex flex-wrap items-center gap-2 border-b border-border py-2 text-sm">
    <span className="w-32 font-mono text-xs">{workstream.code}</span>
    <input className="min-w-40 rounded border border-border bg-surface-primary p-2" aria-label={`Label ${workstream.code}`}
      maxLength={160} value={label} onChange={e => setLabel(e.target.value)} />
    <input type="number" className="w-20 rounded border border-border bg-surface-primary p-2"
      aria-label={`Order ${workstream.code}`} value={order} onChange={e => setOrder(Number(e.target.value))} />
    <label><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> Enabled</label>
    <button className="rounded border border-border px-3 py-2 disabled:opacity-40"
      disabled={disabled || !changed || !label.trim() || !Number.isSafeInteger(order)}
      onClick={() => void onSave({ label: label.trim(), sort_order: order, enabled })}>Save</button>
  </div>;
}
