import React,{useState} from 'react';
import {useTranslation} from 'react-i18next';
import {registerApi} from './api';
import type {ImportPreview} from './types';
interface Props{projectId:string;onDone:()=>void;onClose:()=>void;}
export default function ImportWizard({projectId,onDone,onClose}:Props){
  const {t}=useTranslation();
  const [file,setFile]=useState<File|null>(null);
  const [preview,setPreview]=useState<ImportPreview|null>(null);
  const [busy,setBusy]=useState(false);
  const [resolutions,setResolutions]=useState<Record<string,{action:'create'|'match';item_id?:string}>>({});
  const [choices,setChoices]=useState<{id:string;item_code:string;room:string}[]>([]);
  const [error,setError]=useState<string|null>(null);
  const unresolved=preview?.items.some(r=>r.action==='conflict' && !resolutions[String(r.row)]);
  const run=async (act:'preview'|'commit')=>{
    if(!file) return;
    setBusy(true);setError(null);
    try{
      if(act==='preview'){
        const found=await registerApi.preview(projectId,file);
        setPreview(found);setResolutions({});
        if(found.items.some(x=>x.action==='conflict')){
          const existing=await registerApi.items(projectId,{page:1,page_size:200});
          setChoices(existing.items.map(x=>({id:x.id,item_code:x.item_code,room:x.room})));
        }
      } else if(preview){await registerApi.commit(projectId,file,preview,resolutions);onDone();}
    }catch(e){setError(String(e));}finally{setBusy(false);}
  };
  return <div role="dialog" aria-modal="true" aria-label={t('productionRegister.import')} className="fixed inset-0 z-50 overflow-y-auto bg-black/40 p-6">
    <div className="mx-auto max-w-4xl rounded-xl bg-surface-primary p-6 shadow-xl">
      <h2 className="mb-4 text-lg font-semibold">{t('productionRegister.import')}</h2>
      <input type="file" accept=".xlsx" aria-label={t('productionRegister.import')}
        onChange={e=>{setFile(e.target.files?.[0]||null);setPreview(null);}} />
      <button onClick={()=>void run('preview')} disabled={!file||busy} className="ml-3 rounded border border-border px-3 py-2">{t('productionRegister.preview')}</button>
      {error&&<p role="alert" className="my-3 text-red-600">{error}</p>}
      {preview&&<div className="my-5 space-y-3">
        <p className="text-sm">{JSON.stringify(preview.counts)} · {preview.legacy_code_header}</p>
        {!!preview.warnings.length&&<p className="text-sm text-amber-700">Warnings: {preview.warnings.length}</p>}
        <div className="max-h-96 overflow-auto rounded border border-border"><table className="w-full text-left text-sm"><thead><tr>
          {['Row','Action','Code','BOQ','Issue'].map(x=><th key={x} className="p-2">{x}</th>)}</tr></thead><tbody>
          {preview.items.map(row=><tr key={row.row} className="border-t border-border">
            <td className="p-2">{row.row}</td><td className="p-2">{row.action}</td><td className="p-2">{row.values.item_code}</td>
            <td className="p-2">{row.boq_refs.join(', ')}</td><td className="p-2">{row.issue}</td></tr>)}
        </tbody></table></div>
        {preview.items.filter(r=>r.action==='conflict').map(row=><label key={row.row} className="block text-sm">
          Row {row.row}: {row.issue} — choose target
          <select className="mt-1 w-full rounded border border-border bg-surface-primary p-2" value={
            resolutions[String(row.row)]?.action==='create'?'create':resolutions[String(row.row)]?.item_id||''}
            onChange={e=>setResolutions(v=>({...v,[row.row]:e.target.value==='create'?{action:'create'}:{action:'match',item_id:e.target.value}}))}>
            <option value="">— Select resolution —</option><option value="create">Create a new independent item</option>
            {choices.map(x=><option value={x.id} key={x.id}>{x.item_code} / {x.room} ({x.id.slice(0,8)})</option>)}
          </select>
        </label>)}
        {unresolved&&<p role="alert" className="text-amber-700">Select a resolution for each conflict to enable import.</p>}
        <button disabled={busy||unresolved} className="rounded bg-oe-blue px-4 py-2 text-white disabled:opacity-40" onClick={()=>void run('commit')}>{t('productionRegister.commit')}</button>
      </div>}
      <button className="ml-3 rounded border border-border px-4 py-2" onClick={onClose}>{t('productionRegister.cancel')}</button>
    </div>
  </div>;
}
