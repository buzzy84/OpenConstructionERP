import { apiGet, apiPost, apiPatch, apiPut, apiDelete, fetchWithAuth, API_BASE } from '@/shared/lib/api';
import type { Register, Readiness, ItemsPage, Item, Workstream, ImportPreview, Summary } from './types';
const base = (projectId:string) => `/v1/production-register/projects/${encodeURIComponent(projectId)}`;
const path = (projectId:string) => `${base(projectId)}/drawing-log`;

async function fileResponse(res: Response) {
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `HTTP ${res.status}`);
  }
  return res;
}
export const registerApi = {
  readiness: (id:string) => apiGet<Readiness>(`${base(id)}/readiness`),
  register: (id:string) => apiGet<Register>(path(id)),
  create: (id:string, contract_id:string, boq_id:string, mode:'empty'|'from_boq'|'excel') =>
    apiPost<Register>(path(id), { contract_id, boq_id, mode }),
  summary: (id:string) => apiGet<Summary>(`${path(id)}/summary`),
  candidates: (id:string) => apiGet<{items:{id:string;ordinal:string;description:string}[]}>(`${path(id)}/boq-candidates`),
  items: (id:string, filters:Record<string,string|number|undefined>) => {
    const q = new URLSearchParams();
    Object.entries(filters).forEach(([key,value])=>{if(value!==undefined && value!=='')q.set(key,String(value));});
    return apiGet<ItemsPage>(`${path(id)}/items?${q}`);
  },
  item: (id:string,itemId:string) => apiGet<Item>(`${path(id)}/items/${itemId}`),
  addItem: (id:string, body:Record<string,unknown>) => apiPost<Item>(`${path(id)}/items`,body),
  editItem: (id:string,itemId:string, body:Record<string,unknown>) => apiPatch<Item>(`${path(id)}/items/${itemId}`,body),
  archiveItem: (id:string,itemId:string,version:number,reason:string) => apiPost<Item>(`${path(id)}/items/${itemId}/archive`,{expected_version:version,reason}),
  mapBoq: (id:string,itemId:string,version:number,links:{boq_ref_raw:string;boq_position_id?:string|null}[]) =>
    apiPut(`${path(id)}/items/${itemId}/boq-links`, {expected_version:version,links}),
  relations: (id:string,itemId:string,version:number,relations:{child_item_id:string;kind:string}[]) =>
    apiPut(`${path(id)}/items/${itemId}/relations`,{expected_version:version,relations}),
  checkpoint: (id:string,itemId:string,wsId:string,body:Record<string,unknown>) =>
    apiPut(`${path(id)}/items/${itemId}/checkpoints/${wsId}`,body),
  bulkCheckpoints: (id:string,updates:Record<string,unknown>[])=>
    apiPatch(`${path(id)}/checkpoints/bulk`,{updates}),
  workstreams: (id:string) => apiGet<{items:Workstream[]}>(`${path(id)}/workstreams`),
  addWorkstream: (id:string,body:Record<string,unknown>)=> apiPost<Workstream>(`${path(id)}/workstreams`,body),
  editWorkstream: (id:string,wsId:string,body:Record<string,unknown>)=>apiPatch<Workstream>(`${path(id)}/workstreams/${wsId}`,body),
  references: (id:string,itemId:string)=>apiGet<{items:unknown[]}>(`${path(id)}/items/${itemId}/references`),
  addReference: (id:string,itemId:string,body:Record<string,unknown>)=>apiPost(`${path(id)}/items/${itemId}/references`,body),
  deleteReference: (id:string,itemId:string,refId:string)=>apiDelete(`${path(id)}/items/${itemId}/references/${refId}`),
  audit: (id:string,itemId:string)=>apiGet<{items:{id:string;action:string;occurred_at:string;reason?:string}[]}>(`${path(id)}/items/${itemId}/audit`),
  preview: async (id:string, file:File) => {
    const data=new FormData();data.set('file',file);
    const res=await fileResponse(await fetchWithAuth(`${API_BASE}${path(id)}/import/preview`,{method:'POST',body:data}));
    return res.json() as Promise<ImportPreview>;
  },
  commit: async (id:string,file:File,preview:ImportPreview,resolutions:Record<string,unknown>={})=>{
    const data=new FormData();data.set('file',file);data.set('preview_sha256',preview.preview_sha256);
    data.set('expected_register_version',String(preview.register_version));data.set('resolutions',JSON.stringify(resolutions));
    return (await fileResponse(await fetchWithAuth(`${API_BASE}${path(id)}/import/commit`,{method:'POST',body:data}))).json();
  },
  export: async (id:string,format:'legacy'|'extended') => {
    const res=await fileResponse(await fetchWithAuth(`${API_BASE}${path(id)}/export?format=${format}`));
    const blob=await res.blob();const uri=URL.createObjectURL(blob);
    try { const anchor=document.createElement('a');anchor.href=uri;anchor.download=`drawing-log-${format}.xlsx`;anchor.click(); }
    finally {setTimeout(()=>URL.revokeObjectURL(uri),2000);}
  },
};
