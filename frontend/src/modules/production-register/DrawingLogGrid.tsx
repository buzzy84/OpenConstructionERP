import React from 'react';
import { useTranslation } from 'react-i18next';
import type { Item,Workstream,CheckpointStatus } from './types';
interface Props {
 items:Item[]; workstreams:Workstream[]; selectedId?:string; onSelect:(i:Item)=>void;
 checkedIds:Set<string>; onToggle:(id:string,checked:boolean)=>void;
 onStatusUpdate:(item:Item,workstream:Workstream,status:CheckpointStatus)=>void;
}
const BASE=[['room','ROOM'],['boq','BOQ REF.'],['item_code','INTERNAL CODE'],['description','DESCRIZIONE'],
  ['specification','SPECIFICHE DI PROGETTO'],['quoted_qty_raw','QUANTITÀ OFFERTA'],['production_qty_raw','QUANTITÀ BUZZONI'],
  ['comments','COMMENTI'],['change_notes','CHANGING LOG'],['drafter_name','DISEGNATORE'],['reported_approval_date','APPROVAZIONE']];
const LEGACY_CODES=['production','glass','lighting','finishes','marble','hardware'];
export default function DrawingLogGrid({items,workstreams,selectedId,onSelect,checkedIds,onToggle,onStatusUpdate}:Props){
  const {t}=useTranslation();
  const col=(i:Item,key:string)=>{
    if(key==='boq') return (i.boq_links||[]).map(l=>l.boq_ref_raw).join('\n');
    if(key==='notes')return i.notes;
    const found=i.checkpoints?.find(c=>workstreams.find(w=>w.id===c.workstream_id)?.code===key);
    if(found) return found.reported_value || (found.status!=='unknown'?found.status:'');
    return String((i as unknown as Record<string,unknown>)[key]??'');
  };
  const columns=[...BASE,...LEGACY_CODES.map(k=>[k,workstreams.find(w=>w.code===k)?.label??k]),['notes','NOTE'],
    ...['shipment_1','shipment_2'].map(k=>[k,workstreams.find(w=>w.code===k)?.label??k])];
  return <div className="overflow-x-auto rounded-xl border border-border" role="region" aria-label={t('productionRegister.title')} tabIndex={0}>
    <table className="min-w-max w-full text-left text-xs">
      <thead className="sticky top-0 bg-surface-secondary"><tr><th scope="col" className="border-b border-border p-3">#</th>{columns.map(([key,label])=><th key={key} scope="col" className="whitespace-nowrap border-b border-border px-3 py-3 font-semibold">{label}</th>)}</tr></thead>
      <tbody>{items.map(item=><tr key={item.id} tabIndex={0} onClick={()=>onSelect(item)} onKeyDown={e=>{if(e.key==='Enter')onSelect(item);}}
          aria-selected={selectedId===item.id} className={`cursor-pointer border-t border-border hover:bg-surface-secondary ${selectedId===item.id?'bg-surface-secondary':''}`}>
          <td className="p-3"><input type="checkbox" checked={checkedIds.has(item.id)} aria-label={`Select ${item.item_code}`}
            onClick={e=>e.stopPropagation()} onChange={e=>onToggle(item.id,e.target.checked)} /></td>
          {columns.map(([key])=>{
            const ws=workstreams.find(w=>w.code===key);
            const check=ws?item.checkpoints?.find(c=>c.workstream_id===ws.id):undefined;
            return <td key={key} className="max-w-64 whitespace-pre-line break-words px-3 py-3 align-top">
              {ws?<div className="space-y-1" onClick={e=>e.stopPropagation()}>
                <span className="block">{col(item,key)}</span>
                <select aria-label={`${item.item_code} - ${ws.label}`} className="w-full min-w-28 rounded border border-border bg-surface-primary p-1"
                  value={check?.status||'unknown'} onChange={e=>onStatusUpdate(item,ws,e.target.value as CheckpointStatus)}>
                  {(['unknown','not_started','in_progress','on_hold','completed','not_applicable'] as const).map(st=><option key={st}>{st}</option>)}
                </select>
              </div>:<>{col(item,key)}{key==='boq'&&item.boq_links?.some(l=>l.resolution!=='resolved')&&<span className="ml-1 text-amber-600" title={t('productionRegister.unresolved')}>!</span>}</>}
            </td>;
          })}
        </tr>)}
      </tbody>
    </table>
    {!items.length && <p className="p-6 text-sm text-content-secondary">{t('productionRegister.noItems')}</p>}
  </div>;
}
