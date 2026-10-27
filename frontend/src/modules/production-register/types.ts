export type UUID = string;
export type CheckpointStatus = 'unknown'|'not_started'|'in_progress'|'on_hold'|'completed'|'not_applicable';
export interface BoqLink { id:UUID; boq_ref_raw:string; boq_position_id:UUID|null; resolution:'resolved'|'unresolved'|'ambiguous'; }
export interface Checkpoint { id:UUID; item_id:UUID; workstream_id:UUID; status:CheckpointStatus; reported_value:string|null; planned_date:string|null; actual_date:string|null; assignee_name:string|null; notes:string; version:number; }
export interface Workstream { id:UUID; code:string; label:string; category:string; enabled:boolean; sort_order:number; legacy_column:string|null; }
export interface Reference { id:UUID; kind:string; owner_id:UUID|null; namespace:string|null; external_key:string|null; label:string; }
export interface Item {
  id:UUID; register_id:UUID; project_id:UUID; item_code:string; floor:string; room:string; category:string;
  description:string; specification:string; quoted_qty_raw:string|null; production_qty_raw:string|null;
  comments:string; change_notes:string; notes:string; drafter_name:string|null;
  reported_approval_date:string|null; scope:string; lifecycle:string; display_order:number; version:number;
  boq_links:BoqLink[]; checkpoints:Checkpoint[]; references?:Reference[]; relations?:{child_item_id:UUID;kind:string}[];
}
export interface Register { id:UUID; project_id:UUID; contract_id:UUID; boq_id:UUID; baseline_snapshot_id:UUID; legacy_code_header:string; version:number; created_mode:string; state:string; workstreams:Workstream[]; }
export interface Readiness { can_create:boolean; reasons:string[]; eligible_contracts:{id:UUID;code:string}[]; eligible_boqs:{id:UUID;name:string;snapshot_id:UUID}[]; register_id:UUID|null; }
export interface ItemsPage { items:Item[]; total:number; page:number; page_size:number; }
export interface Summary { item_count:number; unresolved_boq_links:number; distinct_boq_positions:number; by_floor:Record<string,number>; by_category:Record<string,number>; checkpoint_status:Record<string,number>; }
export interface ImportRow { row:number; item_id:string|null; item_version:number|null; action:'create'|'update'|'unchanged'|'conflict'; issue:string|null; values:Record<string,string|null>; boq_refs:string[]; }
export interface ImportPreview { preview_sha256:string; register_version:number; legacy_code_header:string; warnings:{row:number;code:string;message?:string}[]; counts:Record<string,number>; items:ImportRow[]; }
