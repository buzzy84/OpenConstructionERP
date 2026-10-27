import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import DrawingLogGrid from './DrawingLogGrid';
import type { Item, Workstream } from './types';

vi.mock('react-i18next', () => ({ useTranslation: () => ({t:(key:string)=>key}) }));

const ws:Workstream={id:'w1',code:'production',label:'Production',category:'production',sort_order:0,enabled:true,legacy_column:'PRODUZIONE'};
const item:Item={
 id:'item-1',register_id:'register-1',project_id:'project-1',item_code:'ITEM-A+B',floor:'F1',room:'01',category:'Fixtures',
 description:'Display unit',specification:'Spec',quoted_qty_raw:'a corpo',production_qty_raw:'4ml',comments:'',change_notes:'',notes:'',
 drafter_name:null,reported_approval_date:null,scope:'ours',lifecycle:'active',display_order:0,version:1,
 boq_links:[{id:'l1',boq_ref_raw:'REF-A',boq_position_id:null,resolution:'unresolved'},
            {id:'l2',boq_ref_raw:'REF-B',boq_position_id:'b1',resolution:'resolved'}],checkpoints:[],
};

describe('production register legacy grid',()=>{
 it('keeps repeated BOQ references visible without splitting item code on +',()=>{
   render(<DrawingLogGrid items={[item]} workstreams={[ws]} onSelect={()=>{}} checkedIds={new Set()}
     onToggle={()=>{}} onStatusUpdate={()=>{}} />);
   expect(screen.getByText('ITEM-A+B')).toBeTruthy();
   expect(screen.getByText(/REF-A/)).toBeTruthy();
   expect(screen.getByText(/REF-B/)).toBeTruthy();
   expect(screen.getByTitle('productionRegister.unresolved')).toBeTruthy();
 });
 it('allows an explicit checkpoint status edit, without inferring completion',()=>{
   const changed=vi.fn();
   render(<DrawingLogGrid items={[item]} workstreams={[ws]} onSelect={()=>{}} checkedIds={new Set()}
     onToggle={()=>{}} onStatusUpdate={changed} />);
   expect((screen.getByLabelText('ITEM-A+B - Production') as HTMLSelectElement).value).toBe('unknown');
   fireEvent.change(screen.getByLabelText('ITEM-A+B - Production'),{target:{value:'in_progress'}});
   expect(changed).toHaveBeenCalledWith(item,ws,'in_progress');
 });
 it('supports selecting rows for a bulk edit without opening their drawer',()=>{
   const onSelect=vi.fn(),onToggle=vi.fn();
   render(<DrawingLogGrid items={[item]} workstreams={[ws]} onSelect={onSelect}
     checkedIds={new Set()} onToggle={onToggle} onStatusUpdate={()=>{}} />);
   fireEvent.click(screen.getByLabelText('Select ITEM-A+B'));
   expect(onToggle).toHaveBeenCalledWith('item-1',true);
   expect(onSelect).not.toHaveBeenCalled();
 });
});
