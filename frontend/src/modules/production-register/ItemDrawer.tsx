import React,{useEffect,useState} from 'react';
import {useQuery,useMutation,useQueryClient} from '@tanstack/react-query';
import {useTranslation} from 'react-i18next';
import {registerApi} from './api';
import type {Item,Register,CheckpointStatus} from './types';

interface Props{ projectId:string;item:Item;register:Register;onClose:()=>void; }
const STATUSES:CheckpointStatus[]=['unknown','not_started','in_progress','on_hold','completed','not_applicable'];
const KINDS=['cde_container','design_deliverable','submittal','change_order','variation_request','schedule_activity','external'];
const caption='block text-xs font-medium text-content-secondary mb-1';
const field='w-full rounded-md border border-border bg-surface-primary p-2 text-sm';

export default function ItemDrawer({projectId,item,register,onClose}:Props){
  const {t}=useTranslation();const queryClient=useQueryClient();
  const [section,setSection]=useState('general');
  const [form,setForm]=useState<Record<string,string>>({});
  const [boqText,setBoqText]=useState('');
  const [relationId,setRelationId]=useState('');
  const [relationKind,setRelationKind]=useState('contains');
  const [referenceKind,setReferenceKind]=useState('external');
  const [ownerId,setOwnerId]=useState('');
  const [namespace,setNamespace]=useState('');
  const [externalKey,setExternalKey]=useState('');
  const [referenceLabel,setReferenceLabel]=useState('');
  const [error,setError]=useState('');
  const {data:detail,isLoading}=useQuery({queryKey:['production-register',projectId,'item',item.id],queryFn:()=>registerApi.item(projectId,item.id)});
  const {data:audit}=useQuery({queryKey:['production-register',projectId,'audit',item.id],queryFn:()=>registerApi.audit(projectId,item.id),enabled:section==='history'});
  const {data:candidates}=useQuery({queryKey:['production-register',projectId,'candidates'],queryFn:()=>registerApi.candidates(projectId),enabled:section==='boq'});
  const {data:allItems}=useQuery({queryKey:['production-register',projectId,'relation-choices'],queryFn:()=>registerApi.items(projectId,{page:1,page_size:200}),enabled:section==='relations'});
  useEffect(()=>{
    if(detail){
      const current=detail as Item;
      const keys=['floor','room','category','item_code','description','specification','quoted_qty_raw','production_qty_raw','comments','change_notes','notes','drafter_name','reported_approval_date','scope'];
      setForm(Object.fromEntries(keys.map(k=>[k,String((current as unknown as Record<string,unknown>)[k]??'')])));
      setBoqText((detail.boq_links||[]).map(l=>l.boq_ref_raw).join('\n'));
    }
  },[detail]);
  const refresh=async()=>{await queryClient.invalidateQueries({queryKey:['production-register',projectId]});};
  const action=useMutation({mutationFn:async(fn:()=>Promise<unknown>)=>fn(),onSuccess:()=>{setError('');void refresh();},onError:e=>setError(String(e))});
  const saveGeneral=()=>detail&&action.mutate(()=>registerApi.editItem(projectId,detail.id,
    {expected_version:detail.version,...Object.fromEntries(Object.entries(form).map(([k,v])=>[k,(!v && ['quoted_qty_raw','production_qty_raw','reported_approval_date','drafter_name'].includes(k)) ? null : v]))}));
  const saveBoq=()=>detail&&action.mutate(()=>registerApi.mapBoq(projectId,detail.id,detail.version,
    boqText.split(/[\n;]+/).map(x=>x.trim()).filter(Boolean).map(boq_ref_raw=>({boq_ref_raw}))));
  const addRelation=()=>detail&&relationId&&action.mutate(()=>registerApi.relations(projectId,detail.id,detail.version,
      [...(detail.relations||[]).map(x=>({child_item_id:x.child_item_id,kind:x.kind})),{child_item_id:relationId,kind:relationKind}]));
  const addReference=()=>detail&&action.mutate(()=>registerApi.addReference(projectId,detail.id,
    referenceKind==='external'?{kind:'external',namespace,external_key:externalKey,label:referenceLabel}:
       {kind:referenceKind,owner_id:ownerId,label:referenceLabel}));
  const tabs=[['general',t('productionRegister.general')],['boq',t('productionRegister.boq')],
              ['workstreams',t('productionRegister.workstreams')],['relations',t('productionRegister.relations')],
              ['documents',t('productionRegister.documents')],['history',t('productionRegister.history')]];
  const input=(name:string,label:string,multi=false)=> <label key={name} className="block text-sm"><span className={caption}>{label}</span>
    {multi?<textarea className={field} rows={3} value={form[name]||''} onChange={e=>setForm(f=>({...f,[name]:e.target.value}))}/>:
    <input className={field} value={form[name]||''} onChange={e=>setForm(f=>({...f,[name]:e.target.value}))}/>}
  </label>;
  return <aside role="dialog" aria-modal="true" aria-label={t('productionRegister.details')}
    className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col overflow-hidden border-l border-border bg-surface-primary shadow-2xl">
    <div className="flex items-center justify-between border-b border-border p-4"><div>
      <h2 className="text-lg font-semibold">{detail?.item_code||item.item_code} — {t('productionRegister.details')}</h2>
      <p className="text-xs text-content-secondary">UUID: {item.id}</p></div>
      <button onClick={onClose} className="rounded border border-border px-3 py-2" aria-label={t('productionRegister.cancel')}>×</button></div>
    <div className="flex gap-2 overflow-x-auto border-b border-border p-2" role="tablist">
      {tabs.map(([key,label])=><button key={key} role="tab" aria-selected={section===key} onClick={()=>setSection(key)}
        className={`whitespace-nowrap rounded px-3 py-2 text-xs ${section===key?'bg-oe-blue text-white':'border border-border'}`}>{label}</button>)}
    </div>
    <div className="flex-1 space-y-4 overflow-y-auto p-5">
      {isLoading&&<p>Loading…</p>}
      {error&&<p role="alert" className="text-red-600">{error}</p>}
      {detail&&section==='general'&&<div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">{input('item_code',t('productionRegister.code'))}{input('floor',t('productionRegister.floor'))}
          {input('room',t('productionRegister.room'))}{input('category','Category')}{input('quoted_qty_raw','Quoted quantity')}
          {input('production_qty_raw',t('productionRegister.quantity'))}{input('drafter_name','Drafter')}
          {input('reported_approval_date',t('productionRegister.approval'))}
        </div>{input('description',t('productionRegister.description'),true)}{input('specification','Specification',true)}
        {input('comments','Comments',true)}{input('change_notes','Change log',true)}{input('notes','Notes',true)}
        <label className="block text-sm">Scope<select value={form.scope||'ours'} className={field} onChange={e=>setForm(f=>({...f,scope:e.target.value}))}>
          {['ours','subcontracted','by_others','unknown'].map(v=><option key={v}>{v}</option>)}
        </select></label>
        <button disabled={action.isPending} onClick={saveGeneral} className="rounded bg-oe-blue px-4 py-2 text-white">{t('productionRegister.save')}</button>
      </div>}
      {detail&&section==='boq'&&<div className="space-y-3"><p className="text-sm">{t('productionRegister.boqHelp')}</p>
        <textarea className={field} rows={7} value={boqText} onChange={e=>setBoqText(e.target.value)} aria-label={t('productionRegister.boq')}/>
        <p className="text-xs text-content-secondary">Baseline: {register.baseline_snapshot_id}</p>
        <div className="max-h-40 overflow-y-auto rounded border border-border p-2 text-xs">
          {(candidates?.items||[]).slice(0,200).map(c=><button key={c.id} className="mr-2 mb-2 rounded border border-border px-2 py-1"
            onClick={()=>setBoqText(v=>v?`${v}\n${c.ordinal}`:c.ordinal)} title={c.description}>{c.ordinal}</button>)}
        </div>
        {(detail.boq_links||[]).map(link=><p key={link.id} className="text-xs">{link.boq_ref_raw} — {link.resolution}</p>)}
        <button disabled={action.isPending} onClick={saveBoq} className="rounded bg-oe-blue px-4 py-2 text-white">{t('productionRegister.save')}</button>
      </div>}
      {detail&&section==='workstreams'&&<div className="space-y-3">
        {register.workstreams.filter(x=>x.enabled).map(ws=>{
          const check=detail.checkpoints?.find(c=>c.workstream_id===ws.id);
          return <CheckpointEditor key={ws.id} label={ws.label} status={check?.status||'unknown'}
            data={check||null} onSave={body=>action.mutate(()=>registerApi.checkpoint(projectId,detail.id,ws.id,body))}/>;
        })}
      </div>}
      {detail&&section==='relations'&&<div className="space-y-3">
        {(detail.relations||[]).map((r,i)=><p key={i} className="text-sm">{r.kind} → {r.child_item_id}</p>)}
        <label className="block text-sm">Child item<select className={field} value={relationId} onChange={e=>setRelationId(e.target.value)}>
          <option value="">—</option>{(allItems?.items||[]).filter(x=>x.id!==detail.id).map(x=><option key={x.id} value={x.id}>{x.item_code}: {x.description}</option>)}
        </select></label>
        <select className={field} value={relationKind} onChange={e=>setRelationKind(e.target.value)}>
          {['contains','depends_on','replaces'].map(v=><option key={v}>{v}</option>)}
        </select><button onClick={addRelation} className="rounded border border-border px-3 py-2">Add relation</button>
      </div>}
      {detail&&section==='documents'&&<div className="space-y-3">
        {(detail.references||[]).map(r=><div key={r.id} className="flex items-center justify-between gap-2 border-b border-border py-2 text-sm">
          <span>{r.kind}: {r.label||r.external_key||r.owner_id}</span>
          <button className="rounded border border-border px-2 py-1" onClick={()=>action.mutate(()=>registerApi.deleteReference(projectId,detail.id,r.id))}>Remove</button>
        </div>)}
        <select className={field} value={referenceKind} onChange={e=>setReferenceKind(e.target.value)}>
          {KINDS.map(k=><option key={k}>{k}</option>)}
        </select>
        {referenceKind==='external'?<><label className="block text-sm">Namespace<input className={field} value={namespace} onChange={e=>setNamespace(e.target.value)}/></label>
          <label className="block text-sm">Reference<input className={field} value={externalKey} onChange={e=>setExternalKey(e.target.value)}/></label></>:
          <label className="block text-sm">OCERP ID<input className={field} value={ownerId} onChange={e=>setOwnerId(e.target.value)}/></label>}
        <label className="block text-sm">Label<input className={field} value={referenceLabel} onChange={e=>setReferenceLabel(e.target.value)}/></label>
        <button onClick={addReference} className="rounded border border-border px-3 py-2">Add reference</button>
      </div>}
      {section==='history'&&<div className="space-y-3">{(audit?.items||[]).map(a=><div key={a.id} className="border-b border-border pb-2 text-xs">
        <strong>{a.action}</strong> · {new Date(a.occurred_at).toLocaleString()} {a.reason||''}
      </div>)}</div>}
    </div>
  </aside>;
}

function CheckpointEditor({label,status,data,onSave}:{label:string;status:CheckpointStatus;data:{version:number;reported_value:string|null;planned_date:string|null;actual_date:string|null;assignee_name:string|null;notes:string}|null;onSave:(body:Record<string,unknown>)=>void}){
  const {t}=useTranslation();
  const [form,setForm]=useState({status,reported_value:data?.reported_value||'',planned_date:data?.planned_date||'',
    actual_date:data?.actual_date||'',assignee_name:data?.assignee_name||'',notes:data?.notes||''});
  useEffect(()=>setForm({status,reported_value:data?.reported_value||'',planned_date:data?.planned_date||'',
    actual_date:data?.actual_date||'',assignee_name:data?.assignee_name||'',notes:data?.notes||''}),[data,status]);
  const set=(k:string,v:string)=>setForm(f=>({...f,[k]:v}));
  return <fieldset className="space-y-2 rounded-lg border border-border p-3"><legend className="px-2 font-medium">{label}</legend>
    <select className={field} value={form.status} onChange={e=>set('status',e.target.value)}>
      {STATUSES.map(st=><option key={st} value={st}>{st==='unknown'?t('productionRegister.unknown'):st}</option>)}
    </select>
    <input className={field} aria-label={`${label}: reported`} placeholder="Reported value" value={form.reported_value} onChange={e=>set('reported_value',e.target.value)}/>
    <div className="grid grid-cols-2 gap-2"><label className="text-xs">Planned date<input type="date" className={field} value={form.planned_date} onChange={e=>set('planned_date',e.target.value)}/></label>
      <label className="text-xs">Actual date<input type="date" className={field} value={form.actual_date} onChange={e=>set('actual_date',e.target.value)}/></label></div>
    <input className={field} placeholder="Responsible" aria-label={`${label}: responsible`} value={form.assignee_name} onChange={e=>set('assignee_name',e.target.value)}/>
    <input className={field} placeholder="Notes" aria-label={`${label}: notes`} value={form.notes} onChange={e=>set('notes',e.target.value)}/>
    <button className="rounded border border-border px-3 py-1 text-sm" onClick={()=>onSave({expected_version:data?.version||0,
      status:form.status,reported_value:form.reported_value||null,planned_date:form.planned_date||null,actual_date:form.actual_date||null,
      assignee_name:form.assignee_name||null,notes:form.notes})}>{t('productionRegister.save')}</button>
  </fieldset>;
}
