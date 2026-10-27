import {describe,it,expect} from 'vitest';
import {manifest} from './manifest';

describe('optional production register plugin',()=>{
  it('is project-contextual and disabled by default',()=>{
    expect(manifest.id).toBe('production-register');
    expect(manifest.defaultEnabled).toBe(false);
    expect(manifest.routes.map(r=>r.path)).toContain('/projects/:projectId/drawing-log');
    expect(manifest.navItems).toEqual([]);
  });
  it('bundles English and Italian keys for every message',()=>{
    const en=manifest.translations?.en, it=manifest.translations?.it;
    expect(en).toBeTruthy();expect(it).toBeTruthy();
    expect(Object.keys(en||{}).sort()).toEqual(Object.keys(it||{}).sort());
  });
});
