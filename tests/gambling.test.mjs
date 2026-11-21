import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('separate deployment and disabled integrations',()=>{const c=JSON.parse(read('wrangler.jsonc'));assert.equal(c.name,'gambling-community');assert.equal(c.d1_databases[0].database_name,'gambling-community-prod');assert.equal(c.d1_databases[0].database_id,'7bba9ada-589f-493b-8fcf-60265fc0efac');assert.equal(c.previews.d1_databases[0].database_name,'gambling-community-dev');assert.equal(c.previews.d1_databases[0].database_id,'a92cf620-2a0b-46e1-a0ff-2e0c94218f37');assert.notEqual(c.d1_databases[0].database_id,c.previews.d1_databases[0].database_id);assert.equal(c.vars.APP_ENV,'production');assert.equal(c.previews.vars.APP_ENV,'preview');assert.equal(c.r2_buckets[0].bucket_name,'gambling-community-public-prod');assert.equal(c.previews.r2_buckets[0].bucket_name,'gambling-community-public-dev');assert.equal(c.vars.IDENTITY_LOGIN_ENABLED,'false');assert.equal(c.vars.COLLECT_ENABLED,'false');});
test('no inherited spine production bindings',()=>{for(const p of ['wrangler.jsonc','wrangler.local.jsonc','src/seo.ts','public/_headers'])assert.doesNotMatch(read(p),/spine\.nbn369\.com|spine-community-db|5919ff78-b8fc-46ab-85f0-01fe5e6a41b0/);});
test('localized product values',()=>{const s=read('public/i18n.js');assert.match(s,/戒赌社区/);assert.match(s,/戒賭社區/);assert.match(s,/Real Stories\. Real Impacts\. Open Discussion\./);});
test('new SSO maps center user ID without old Google identity',()=>{const s=read('src/auth.ts');assert.match(s,/direct_google_login_disabled/);assert.doesNotMatch(s,/claims\.spine_google_sub/);assert.match(s,/findOrCreateUser\(env\.DB,'identity_center',claims\.sub\)/);});

test('remote migration cannot run without exact dev Preview gating and verified D1 mapping',()=>{const s=read('scripts/preview-migrate.mjs');assert.match(s,/WORKERS_CI_BRANCH==='dev'/);assert.match(s,/gambling-community-dev/);assert.match(s,/preview-migrations.jsonc/);assert.match(s,/production.some/);});

test('repository rename links use canonical GitHub path',()=>{
 for(const p of ['README.md','AGENTS.md','docs/START_HERE.md','docs/PROJECT_STATUS.md','docs/CLOUDFLARE_SETUP.md']){
  const contents=read(p);
  assert.doesNotMatch(contents,/119shenhao\/gambing(?![a-z-])/,'outdated repository link in '+p);
 }
 assert.match(read('README.md'),/119shenhao\/gambling/);
});

// Check every runtime URL, admin confirmation, and browser storage key after the repo rename.
test('no references to previous medical forum infrastructure in active runtime',()=>{
 for(const p of ['src/admin.ts','src/community.ts','src/public-projection.ts','src/projection-demand.ts','public/app.js','public/public-content.js','public/share-ui.js']){
  assert.doesNotMatch(read(p),/spine-community|spine\.nbn369\.com|spine-data|x-spine-projection-miss|my-spine|spine-traffic-v1|SPINE COMMUNITY/,'stale medical forum reference in '+p);
 }
 const app=read('public/app.js'),admin=read('src/admin.ts');
 assert.match(app,/preview_confirm:'gambling-community-dev'/);
 assert.match(admin,/b\.preview_confirm!=='gambling-community-dev'/);
 assert.match(read('src/projection-demand.ts'),/x-gambling-projection-miss/);
 for(const p of ['public/app.js','public/locale.js'])assert.doesNotMatch(read(p),/sc_locale/);
 assert.match(read('public/locale.js'),/gc_locale/);
 assert.doesNotMatch(read('src/community.ts'),/sc_visitor/);
 assert.doesNotMatch(read('public/reading-preferences.js'),/sc_reading_preferences/);
});

test('identity center client names are independent, while login is disabled until registered',()=>{
 const cfg=JSON.parse(read('wrangler.jsonc'));
 assert.equal(cfg.vars.IDENTITY_ISSUER,'https://idcenter.nbn369.com');
 assert.equal(cfg.vars.IDENTITY_CLIENT_ID,'gambling-community-prod');
 assert.equal(cfg.previews.vars.IDENTITY_ISSUER,'https://dev-identity-center.119shenhao.workers.dev');
 assert.equal(cfg.previews.vars.IDENTITY_CLIENT_ID,'gambling-community-dev');
 for(const vars of [cfg.vars,cfg.previews.vars]){
  assert.equal(vars.IDENTITY_LOGIN_ENABLED,'false');
  assert.equal(vars.IDENTITY_CLIENT_SECRET,undefined);
  assert.match(vars.IDENTITY_REDIRECT_URI,/^https:\/\//);
 }
});

test('confirmed development and production hosts map to unique exact SSO callbacks',()=>{
 const c=JSON.parse(read('wrangler.jsonc'));
 assert.equal(c.previews.vars.IDENTITY_REDIRECT_URI,'https://dev-gambling-community.119shenhao.workers.dev/api/auth/identity/callback');
 assert.equal(c.vars.IDENTITY_REDIRECT_URI,'https://gambling.nbn369.com/api/auth/identity/callback');
 assert.equal(c.previews.vars.PUBLIC_CONTENT_ORIGIN,'https://dev-gambling-community.119shenhao.workers.dev');
 assert.equal(c.previews.vars.IDENTITY_LOGIN_ENABLED,'false');
 assert.equal(c.vars.IDENTITY_LOGIN_ENABLED,'false');
 assert.equal(c.previews.vars.IDENTITY_CLIENT_SECRET,undefined);
 assert.equal(c.vars.IDENTITY_CLIENT_SECRET,undefined);
});

test('Cloudflare public Worker fetch compatibility is configured before OAuth tests',()=>{
 const c=JSON.parse(read('wrangler.jsonc'));
 assert.ok(c.compatibility_flags.includes('global_fetch_strictly_public'));
 assert.equal(c.previews.vars.IDENTITY_LOGIN_ENABLED,'false');
});
