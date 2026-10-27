import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { registerApi } from './api';

interface Candidate {
  id: string;
  ordinal: string;
  description: string;
  unit: string;
  quantity: string;
}
interface Props {
  projectId: string;
  onClose: () => void;
  onUse: (positions: Candidate[]) => void;
}

/** Commercial BOQ positions are candidates, not production items. A person must
 * choose the grouping and enter a new internal item code before anything is made. */
export default function BoqCandidatePanel({ projectId, onClose, onUse }: Props) {
  const { t } = useTranslation();
  const { data, isPending, error } = useQuery({
    queryKey: ['production-register', projectId, 'candidates'],
    queryFn: () => registerApi.candidates(projectId),
  });
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const positions = (data?.items ?? []) as Candidate[];
  const filtered = useMemo(() => positions.filter(p =>
    `${p.ordinal} ${p.description}`.toLocaleLowerCase().includes(search.toLocaleLowerCase())), [positions, search]);
  const chosen = positions.filter(p => selected.has(p.id));

  return <section className="rounded-xl border border-border bg-surface-primary p-4" aria-label={t('productionRegister.boqCandidates')}>
    <div className="flex items-center justify-between gap-3">
      <div><h2 className="font-semibold">{t('productionRegister.boqCandidates')}</h2>
        <p className="text-sm text-content-secondary">{t('productionRegister.boqCandidatesHelp')}</p></div>
      <button className="rounded border border-border px-3 py-2" onClick={onClose}>{t('productionRegister.cancel')}</button>
    </div>
    <label className="mt-3 block text-sm">{t('productionRegister.search')}
      <input className="mt-1 w-full rounded border border-border bg-surface-primary px-3 py-2" value={search}
        onChange={e => setSearch(e.target.value)} />
    </label>
    {isPending && <p role="status">{t('productionRegister.loading')}</p>}
    {error && <p role="alert">{String(error)}</p>}
    <div className="mt-3 max-h-72 overflow-y-auto" role="group" aria-label={t('productionRegister.boqCandidates')}>
      {filtered.map(pos => <label key={pos.id} className="flex cursor-pointer items-start gap-2 border-b border-border py-2 text-sm">
        <input type="checkbox" checked={selected.has(pos.id)} aria-label={pos.ordinal} onChange={e => {
          const checked = e.target.checked;
          setSelected(previous => {
            const next = new Set(previous);
            if (checked) next.add(pos.id); else next.delete(pos.id);
            return next;
          });
        }} />
        <span><strong>{pos.ordinal}</strong> — {pos.description} ({pos.quantity} {pos.unit})</span>
      </label>)}
    </div>
    <p className="mt-3 text-sm">{selected.size} {t('productionRegister.selected')}</p>
    <button disabled={!chosen.length} className="mt-2 rounded bg-oe-blue px-4 py-2 text-white disabled:opacity-40"
      onClick={() => onUse(chosen)}>{t('productionRegister.useSelection')}</button>
  </section>;
}
