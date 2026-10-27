import React,{useState} from 'react';
import {useParams,useNavigate} from 'react-router-dom';
import {useTranslation} from 'react-i18next';
import {useQuery,useMutation,useQueryClient} from '@tanstack/react-query';
import {registerApi} from './api';
import type {Item,Readiness,CheckpointStatus,Workstream} from './types';
import DrawingLogToolbar from './DrawingLogToolbar';
import DrawingLogGrid from './DrawingLogGrid';
import CreateRegisterDialog from './CreateRegisterDialog';
import ImportWizard from './ImportWizard';
import ItemDrawer from './ItemDrawer';
import BoqCandidatePanel from './BoqCandidatePanel';
import WorkstreamConfigRow from './WorkstreamConfigRow';

const input='w-full rounded border border-border bg-surface-primary px-3 py-2 text-sm';
export default function DrawingLogPage(){
  const {projectId=''}=useParams<{projectId:string}>();const navigate=useNavigate();const {t}=useTranslation();
  const qc=useQueryClient();
  const [search,setSearch]=useState('');const [floor,setFloor]=useState('');const [page,setPage]=useState(1);
  const [selected,setSelected]=useState<Item|null>(null);const [addOpen,setAddOpen]=useState(false);
  const [importOpen,setImportOpen]=useState(false);const [error,setError]=useState('');
  const [checkedIds,setCheckedIds]=useState<Set<string>>(new Set());
  const [bulkWorkstream,setBulkWorkstream]=useState('production');
  const [bulkStatus,setBulkStatus]=useState<CheckpointStatus>('in_progress');
  const [manageOpen,setManageOpen]=useState(false);
  const [showBoqCandidates,setShowBoqCandidates]=useState(false);
  const [newWsCode,setNewWsCode]=useState('');const [newWsLabel,setNewWsLabel]=useState('');
  const [itemDraft,setItemDraft]=useState({item_code:'',description:'',floor:'',room:'',category:'',production_qty_raw:'',quoted_qty_raw:'',boq_refs:''});
  const readiness=useQuery({queryKey:['production-register',projectId,'readiness'],queryFn:()=>registerApi.readiness(projectId),enabled:!!projectId});
  const hasRegister=!!readiness.data?.register_id;
  const register=useQuery({queryKey:['production-register',projectId,'header'],queryFn:()=>registerApi.register(projectId),enabled:hasRegister});
  const summary=useQuery({queryKey:['production-register',projectId,'summary'],queryFn:()=>registerApi.summary(projectId),enabled:hasRegister});
  const list=useQuery({queryKey:['production-register',projectId,'items',page,search,floor],queryFn:()=>registerApi.items(projectId,{page,page_size:50,search,floor}),enabled:hasRegister});
  const refresh=async()=>{await qc.invalidateQueries({queryKey:['production-register',projectId]});};
  const create=useMutation({mutationFn:({contractId,boqId,mode}:{contractId:string;boqId:string;mode:'empty'|'from_boq'|'excel'})=>
     registerApi.create(projectId,contractId,boqId,mode),onSuccess:(data)=>{void refresh();if(data.created_mode==='excel')setImportOpen(true);if(data.created_mode==='from_boq')setShowBoqCandidates(true);},onError:e=>setError(String(e))});
  const checkpointUpdate=useMutation({mutationFn:({item,ws,status}:{item:Item;ws:Workstream;status:CheckpointStatus})=>{
    const current=item.checkpoints?.find(c=>c.workstream_id===ws.id);
    return registerApi.checkpoint(projectId,item.id,ws.id,{expected_version:current?.version||0,status,
      reported_value:current?.reported_value||null,planned_date:current?.planned_date||null,
      actual_date:current?.actual_date||null,assignee_name:current?.assignee_name||null,notes:current?.notes||''});
  },onSuccess:()=>{void refresh();},onError:e=>setError(String(e))});
  const bulk=useMutation({mutationFn:async()=>{
    const ws=register.data?.workstreams.find(w=>w.code===bulkWorkstream);
    if(!ws)throw new Error('Workstream not found');
    const selected=(list.data?.items||[]).filter(item=>checkedIds.has(item.id));
    return registerApi.bulkCheckpoints(projectId,selected.map(item=>{
      const existing=item.checkpoints?.find(c=>c.workstream_id===ws.id);
      return {item_id:item.id,workstream_id:ws.id,expected_version:existing?.version||0,
        status:bulkStatus,reported_value:existing?.reported_value||null,
        planned_date:existing?.planned_date||null,actual_date:existing?.actual_date||null,
        assignee_name:existing?.assignee_name||null,notes:existing?.notes||''};
    }));
  },onSuccess:()=>{setCheckedIds(new Set());void refresh();},onError:e=>setError(String(e))});
  const add=useMutation({mutationFn:()=>registerApi.addItem(projectId,{
      item_code:itemDraft.item_code,description:itemDraft.description,floor:itemDraft.floor,room:itemDraft.room,
      category:itemDraft.category,quoted_qty_raw:itemDraft.quoted_qty_raw||null,production_qty_raw:itemDraft.production_qty_raw||null,
      boq_links:itemDraft.boq_refs.split(/[\n;]+/).map(x=>x.trim()).filter(Boolean).map(boq_ref_raw=>({boq_ref_raw}))
  }),onSuccess:()=>{setAddOpen(false);setItemDraft({item_code:'',description:'',floor:'',room:'',category:'',production_qty_raw:'',quoted_qty_raw:'',boq_refs:''});void refresh();},onError:e=>setError(String(e))});
  if(!projectId)return <p role="alert">Project ID missing</p>;
  if(readiness.isLoading)return <div className="p-6" role="status">Loading drawing log…</div>;
  if(readiness.error)return <div role="alert" className="p-6 text-red-600">{String(readiness.error)}</div>;
  const floors=Object.keys(summary.data?.by_floor||{}).filter(Boolean);
  return <div className="space-y-5 p-5">
    <div className="flex items-start justify-between"><div>
      <h1 className="text-2xl font-semibold text-content-primary">{t('productionRegister.title')}</h1>
      <p className="text-sm text-content-secondary">{t('productionRegister.subtitle')}</p>
      {register.data&&<p className="mt-2 text-xs text-content-secondary">BOQ: {register.data.boq_id} · Baseline: {register.data.baseline_snapshot_id}</p>}
    </div><button className="rounded border border-border px-3 py-2 text-sm" onClick={()=>navigate(`/projects/${projectId}`)}>← Project</button></div>
    {error&&<p role="alert" className="rounded border border-red-200 p-3 text-red-600">{error}<button className="ml-4" onClick={()=>setError('')}>×</button></p>}
    {!hasRegister&&readiness.data&&<CreateRegisterDialog readiness={readiness.data as Readiness} disabled={create.isPending}
      onCreate={async (contractId,boqId,mode)=>{await create.mutateAsync({contractId,boqId,mode});}}/>}
    {hasRegister&&register.data&&<>
      <div className="flex flex-wrap gap-3 text-sm">
        <span className="rounded-lg border border-border px-3 py-2">Items: <b>{summary.data?.item_count??'…'}</b></span>
        <span className="rounded-lg border border-border px-3 py-2">{t('productionRegister.unresolved')}: <b>{summary.data?.unresolved_boq_links??'…'}</b></span>
        <span className="rounded-lg border border-border px-3 py-2">Distinct BOQ: <b>{summary.data?.distinct_boq_positions??'…'}</b></span>
      </div>
      <button className="rounded border border-border px-3 py-2 text-sm" onClick={()=>setShowBoqCandidates(v=>!v)}>{t('productionRegister.boqCandidates')}</button>
      {showBoqCandidates&&<BoqCandidatePanel projectId={projectId} onClose={()=>setShowBoqCandidates(false)}
        onUse={positions=>{setItemDraft(previous=>({...previous,
          description:positions.length===1?positions[0]!.description:previous.description,
          boq_refs:[...new Set([...previous.boq_refs.split(/[\n;]+/).map(x=>x.trim()).filter(Boolean),...positions.map(p=>p.ordinal)])].join('\n')}));
          setShowBoqCandidates(false);setAddOpen(true);}}/>}
      <DrawingLogToolbar search={search} onSearch={v=>{setSearch(v);setPage(1);}} floor={floor} onFloor={v=>{setFloor(v);setPage(1);}}
        floors={floors} onAdd={()=>setAddOpen(true)} onImport={()=>setImportOpen(true)} onExport={mode=>{void registerApi.export(projectId,mode).catch(e=>setError(String(e)));}} reload={()=>{void refresh();}}/>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <button className="rounded border border-border px-3 py-1" onClick={()=>setManageOpen(!manageOpen)}>Manage workstreams</button>
        <span>{checkedIds.size} selected</span>
        <select className="rounded border border-border p-2" aria-label="Bulk workstream" value={bulkWorkstream} onChange={e=>setBulkWorkstream(e.target.value)}>
          {register.data.workstreams.filter(w=>w.enabled).map(w=><option key={w.id} value={w.code}>{w.label}</option>)}
        </select>
        <select className="rounded border border-border p-2" aria-label="Bulk status" value={bulkStatus} onChange={e=>setBulkStatus(e.target.value)}>
          {(['unknown','not_started','in_progress','on_hold','completed','not_applicable'] as const).map(st=><option key={st}>{st}</option>)}
        </select><button disabled={!checkedIds.size||bulk.isPending} className="rounded bg-oe-blue px-3 py-2 text-white disabled:opacity-40"
          onClick={()=>bulk.mutate()}>Update selected</button>
      </div>
      {manageOpen&&<div className="rounded border border-border p-4"><h2 className="mb-3 font-semibold">Workstream configuration</h2>
        {register.data.workstreams.map(w=><WorkstreamConfigRow key={w.id} workstream={w} disabled={false}
          onSave={changes=>registerApi.editWorkstream(projectId,w.id,changes).then(refresh).catch(err=>{setError(String(err));return undefined;})}/>)}
        <div className="flex gap-2"><input className={input} placeholder="Code" value={newWsCode} onChange={e=>setNewWsCode(e.target.value)}/>
          <input className={input} placeholder="Label" value={newWsLabel} onChange={e=>setNewWsLabel(e.target.value)}/>
          <button className="rounded border border-border px-3 py-2" disabled={!newWsCode||!newWsLabel}
            onClick={()=>{void registerApi.addWorkstream(projectId,{code:newWsCode,label:newWsLabel,category:'other',sort_order:99})
              .then(()=>{setNewWsCode('');setNewWsLabel('');return refresh();}).catch(err=>setError(String(err)));}}>Add</button>
        </div>
      </div>}
      {list.isLoading?<div role="status">Loading items…</div>:
       list.error?<p role="alert" className="text-red-600">{String(list.error)}</p>:
       <DrawingLogGrid items={list.data?.items||[]} workstreams={register.data.workstreams} selectedId={selected?.id} onSelect={setSelected}
         checkedIds={checkedIds} onToggle={(id,checked)=>setCheckedIds(prev=>{const next=new Set(prev);checked?next.add(id):next.delete(id);return next;})}
         onStatusUpdate={(item,ws,status)=>checkpointUpdate.mutate({item,ws,status})}/>}
      <div className="flex items-center gap-3 text-sm">
        <button disabled={page===1} className="rounded border border-border px-3 py-1 disabled:opacity-40" onClick={()=>setPage(p=>Math.max(1,p-1))}>Previous</button>
        <span>{page} / {Math.max(1,Math.ceil((list.data?.total||0)/50))}</span>
        <button disabled={page*50>=(list.data?.total||0)} className="rounded border border-border px-3 py-1 disabled:opacity-40" onClick={()=>setPage(p=>p+1)}>Next</button>
      </div>
    </>}
    {hasRegister&&register.data&&selected&&<ItemDrawer key={selected.id} projectId={projectId} item={selected} register={register.data} onClose={()=>{setSelected(null);void refresh();}}/>}
    {hasRegister&&importOpen&&<ImportWizard projectId={projectId} onClose={()=>setImportOpen(false)} onDone={()=>{setImportOpen(false);void refresh();}}/>}
    {hasRegister&&addOpen&&<div role="dialog" aria-modal="true" aria-label={t('productionRegister.add')} className="fixed inset-0 z-50 bg-black/40 p-6">
      <form className="mx-auto max-w-xl space-y-3 rounded-xl bg-surface-primary p-6" onSubmit={e=>{e.preventDefault();add.mutate();}}>
        <h2 className="text-lg font-semibold">{t('productionRegister.add')}</h2>
        {(['item_code','description','floor','room','category','quoted_qty_raw','production_qty_raw','boq_refs']as const).map(key=><label className="block text-sm" key={key}>
          {key==='boq_refs'?t('productionRegister.boq'):key}
          {key==='boq_refs'?<textarea className={input} rows={3} value={itemDraft[key]} onChange={e=>setItemDraft(v=>({...v,[key]:e.target.value}))}/>:
            <input className={input} value={itemDraft[key]} onChange={e=>setItemDraft(v=>({...v,[key]:e.target.value}))}/>}</label>)}
        <button type="submit" disabled={add.isPending} className="rounded bg-oe-blue px-4 py-2 text-white">{t('productionRegister.save')}</button>
        <button type="button" className="ml-3 rounded border border-border px-4 py-2" onClick={()=>setAddOpen(false)}>{t('productionRegister.cancel')}</button>
      </form>
    </div>}
  </div>;
}
