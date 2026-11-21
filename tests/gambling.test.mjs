import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('separate deployment and disabled integrations',()=>{const c=JSON.parse(read('wrangler.jsonc'));assert.equal(c.name,'gambling-community');assert.ok(!c.d1_databases&&!c.r2_buckets);assert.equal(c.vars.IDENTITY_LOGIN_ENABLED,'false');assert.equal(c.vars.COLLECT_ENABLED,'false');});
test('no inherited spine production bindings',()=>{for(const p of ['wrangler.jsonc','wrangler.local.jsonc','src/seo.ts','public/_headers'])assert.doesNotMatch(read(p),/spine\.nbn369\.com|spine-community-db|5919ff78-b8fc-46ab-85f0-01fe5e6a41b0/);});
test('localized product values',()=>{const s=read('public/i18n.js');assert.match(s,/戒赌社区/);assert.match(s,/戒賭社區/);assert.match(s,/Real Stories\. Real Impacts\. Open Discussion\./);});
test('new SSO maps center user ID without old Google identity',()=>{const s=read('src/auth.ts');assert.match(s,/direct_google_login_disabled/);assert.doesNotMatch(s,/claims\.spine_google_sub/);assert.match(s,/findOrCreateUser\(env\.DB,'identity_center',claims\.sub\)/);});
