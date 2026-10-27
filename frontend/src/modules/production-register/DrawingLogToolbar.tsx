import React from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  search:string; onSearch:(v:string)=>void; floor:string; onFloor:(v:string)=>void;
  floors:string[]; onAdd:()=>void; onImport:()=>void; onExport:(mode:'legacy'|'extended')=>void;
  reload:()=>void;
}
export default function DrawingLogToolbar(props:Props) {
  const {t}=useTranslation();
  const button='rounded-lg border border-border px-3 py-2 text-sm text-content-primary hover:bg-surface-secondary focus-visible:outline focus-visible:outline-2';
  return <div className="flex flex-wrap items-center gap-2" role="toolbar">
    <input className="min-w-44 rounded-lg border border-border bg-surface-primary px-3 py-2 text-sm" value={props.search}
      onChange={e=>props.onSearch(e.target.value)} placeholder={t('productionRegister.search')} aria-label={t('productionRegister.search')} />
    <select className="rounded-lg border border-border bg-surface-primary px-3 py-2 text-sm" value={props.floor} onChange={e=>props.onFloor(e.target.value)} aria-label={t('productionRegister.floor')}>
      <option value="">{t('productionRegister.floor')}</option>
      {props.floors.map(v=><option key={v} value={v}>{v}</option>)}
    </select>
    <button className={button} onClick={props.onAdd}>{t('productionRegister.add')}</button>
    <button className={button} onClick={props.onImport}>{t('productionRegister.import')}</button>
    <button className={button} onClick={()=>props.onExport('legacy')}>{t('productionRegister.export')}</button>
    <button className={button} onClick={()=>props.onExport('extended')}>{t('productionRegister.export')} (+)</button>
    <button className={button} onClick={props.reload}>{t('productionRegister.reload')}</button>
  </div>;
}
