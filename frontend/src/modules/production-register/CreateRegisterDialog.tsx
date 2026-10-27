import React,{useState} from 'react';
import { useTranslation } from 'react-i18next';
import type {Readiness} from './types';
interface Props { readiness:Readiness; onCreate:(contractId:string,boqId:string,mode:'empty'|'from_boq'|'excel')=>Promise<void>; disabled:boolean; }
export default function CreateRegisterDialog({readiness,onCreate,disabled}:Props){
  const {t}=useTranslation();
  const [contractId,setContract]=useState(readiness.eligible_contracts[0]?.id||'');
  const [boqId,setBoq]=useState(readiness.eligible_boqs[0]?.id||'');
  const [mode,setMode]=useState<'empty'|'from_boq'|'excel'>('empty');
  return <section className="max-w-2xl rounded-xl border border-border bg-surface-primary p-6" aria-label={t('productionRegister.create')}>
    <h2 className="text-lg font-semibold">{t('productionRegister.create')}</h2>
    {!readiness.can_create&&<div role="alert" className="my-3 text-amber-700">{t('productionRegister.notReady')} {readiness.reasons.join(', ')}</div>}
    <div className="mt-3 grid gap-3 sm:grid-cols-2">
      <label className="text-sm">Contract
        <select className="mt-1 block w-full rounded border border-border p-2" value={contractId} onChange={e=>setContract(e.target.value)}>
          {readiness.eligible_contracts.map(c=><option key={c.id} value={c.id}>{c.code}</option>)}
        </select>
      </label>
      <label className="text-sm">BOQ baseline
        <select className="mt-1 block w-full rounded border border-border p-2" value={boqId} onChange={e=>setBoq(e.target.value)}>
          {readiness.eligible_boqs.map(b=><option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      </label>
    </div>
    <fieldset className="my-4"><legend className="text-sm font-medium">Mode</legend>
      {(['empty','from_boq','excel']as const).map(m=><label key={m} className="mr-4 inline-flex items-center gap-1 text-sm">
        <input type="radio" checked={mode===m} onChange={()=>setMode(m)} />{m==='empty'?'Empty':m==='from_boq'?'From approved BOQ':'Import Excel'}
      </label>)}
    </fieldset>
    <button disabled={!readiness.can_create||disabled||!contractId||!boqId} className="rounded bg-oe-blue px-4 py-2 text-white disabled:opacity-50"
      onClick={()=>void onCreate(contractId,boqId,mode)}>{t('productionRegister.create')}</button>
  </section>;
}
