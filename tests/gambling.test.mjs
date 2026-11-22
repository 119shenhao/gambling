import test from 'node:test';
import {spawnSync} from 'node:child_process';
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

test('identity center clients remain separate and only dev login is enabled',()=>{
 const cfg=JSON.parse(read('wrangler.jsonc'));
 assert.equal(cfg.vars.IDENTITY_ISSUER,'https://idcenter.nbn369.com');
 assert.equal(cfg.vars.IDENTITY_CLIENT_ID,'gambling-community-prod');
 assert.equal(cfg.previews.vars.IDENTITY_ISSUER,'https://dev-identity-center.119shenhao.workers.dev');
 assert.equal(cfg.previews.vars.IDENTITY_CLIENT_ID,'gambling-community-dev');
 assert.equal(cfg.vars.IDENTITY_LOGIN_ENABLED,'false');
 assert.equal(cfg.previews.vars.IDENTITY_LOGIN_ENABLED,'true');
 for(const vars of [cfg.vars,cfg.previews.vars]){
  assert.equal(vars.IDENTITY_CLIENT_SECRET,undefined);
  assert.match(vars.IDENTITY_REDIRECT_URI,/^https:\/\//);
 }
});

test('confirmed development and production hosts map to unique exact SSO callbacks',()=>{
 const c=JSON.parse(read('wrangler.jsonc'));
 assert.equal(c.previews.vars.IDENTITY_REDIRECT_URI,'https://dev-gambling-community.119shenhao.workers.dev/api/auth/identity/callback');
 assert.equal(c.vars.IDENTITY_REDIRECT_URI,'https://gambling.nbn369.com/api/auth/identity/callback');
 assert.equal(c.previews.vars.PUBLIC_CONTENT_ORIGIN,'https://dev-gambling-community.119shenhao.workers.dev');
 assert.equal(c.previews.vars.IDENTITY_LOGIN_ENABLED,'true');
 assert.equal(c.vars.IDENTITY_LOGIN_ENABLED,'false');
 assert.equal(c.previews.vars.IDENTITY_CLIENT_SECRET,undefined);
 assert.equal(c.vars.IDENTITY_CLIENT_SECRET,undefined);
});

test('Cloudflare public Worker fetch compatibility is configured before OAuth tests',()=>{
 const c=JSON.parse(read('wrangler.jsonc'));
 assert.ok(c.compatibility_flags.includes('global_fetch_strictly_public'));
 assert.equal(c.previews.vars.IDENTITY_LOGIN_ENABLED,'true');
});

test('one-time DEV OAuth bootstrap is correctly scoped to Gambling Worker and DEV-only databases',()=>{
 const result=spawnSync(process.execPath,['--check','scripts/provision-dev-identity.mjs'],{encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);
 const s=read('scripts/provision-dev-identity.mjs'),c=JSON.parse(read('wrangler.identity-dev-provision.jsonc'));
 assert.match(s,/WORKERS_CI_BRANCH!=="dev"/);
 assert.match(s,/\["preview","secret","put",SECRET_NAME/);
 assert.match(s,/gambling-community-dev/);
 assert.match(s,/status!=="disabled"/);
 assert.equal(c.d1_databases.length,1);
 assert.equal(c.d1_databases[0].database_id,'66c36ee9-2cab-4e85-bc02-645819344297');
 assert.equal(c.d1_databases[0].database_name,'identity-center-dev');
});

test('one-time provisioning is no longer invoked from ordinary Cloudflare builds',()=>{
 assert.equal(read('scripts/prepare-build.mjs').includes("['scripts/provision-dev-identity.mjs']"),false);
});

test('Google login always requests account chooser through Identity Center, never bypasses center',()=>{
  const auth=read('src/auth.ts');
  assert.match(auth,/params\.set\('provider_hint','google'\)/);
  assert.match(auth,/prompt:'select_account'/);
  assert.match(auth,/return redirect\(config\.issuer\+'\/oauth\/authorize\?'\+params,flowCookie\(state\)\)/);
  assert.equal(JSON.parse(read('wrangler.jsonc')).vars.IDENTITY_LOGIN_ENABLED,'false');
});

test('Azure DEV/PROD shared-key budget is protected by a 25k/month environment cap',()=>{
 const c=JSON.parse(read('wrangler.jsonc'));
 assert.equal(c.vars.TRANSLATION_ENABLED,'false');
 assert.equal(c.previews.vars.TRANSLATION_ENABLED,'true');
 assert.equal(c.previews.vars.TRANSLATOR_REGION,'eastus');
 assert.equal(c.previews.vars.TRANSLATOR_F0_VERIFIED_AT,'2026-11-09T06:14:50Z');
 assert.equal(c.previews.vars.TRANSLATOR_KEY,undefined);
 assert.equal(c.vars.TRANSLATOR_KEY,undefined);
 assert.equal(c.previews.vars.TRANSLATION_DAILY_LIMIT,'5000');
 assert.equal(c.previews.vars.TRANSLATION_MONTHLY_LIMIT,'10000');
 const tr=read('src/translation.ts');
 assert.match(tr,/AZURE_SITE_MAX_MONTHLY=25000/);
 assert.match(tr,/AZURE_DEFAULT_DAILY=5000/);
 assert.match(tr,/AZURE_DEFAULT_MONTHLY=25000/);
 assert.match(tr,/Math\.min\(Number\(raw\),max\)/);
 const admin=read('src/admin.ts');
 assert.match(admin,/monthly>AZURE_SITE_MAX_MONTHLY/);
 assert.match(admin,/translation_credentials_not_ready/);
 assert.match(admin,/env\.APP_ENV!=='preview'/);
 assert.match(read('public/translation-admin.js'),/data-action="toggle-translation"/);
 assert.match(read('public/app.js'),/if\(action==='toggle-translation'\)/);
});

test('translation provider status exposes database activation state to admin UI',()=>{
 const source=read('src/translation.ts');
 assert.match(source,/translationEnabled:budget\.translationEnabled/);
 const ui=read('public/translation-admin.js');
 assert.match(ui,/azure\.translationEnabled/);
 assert.match(read('src/admin.ts'),/translation_requires_development_verification/);
});

test('Worker deployment never overwrites Cloudflare-managed secrets or isolates wrong resources',()=>{
 const cfg=JSON.parse(read('wrangler.jsonc'));
 assert.equal(cfg.keep_vars,true);
 assert.equal(cfg.name,'gambling-community');
 assert.equal(cfg.previews.vars.APP_ENV,'preview');
 assert.equal(cfg.vars.APP_ENV,'production');
 assert.equal(cfg.previews.vars.TRANSLATOR_KEY,undefined);
 assert.equal(cfg.vars.TRANSLATOR_KEY,undefined);
 assert.equal(cfg.previews.d1_databases[0].database_id,'a92cf620-2a0b-46e1-a0ff-2e0c94218f37');
 assert.equal(cfg.d1_databases[0].database_id,'7bba9ada-589f-493b-8fcf-60265fc0efac');
 const build=read('scripts/prepare-build.mjs');
 assert.doesNotMatch(build,/wrangler[^\n]*secret\s+(?:put|delete|bulk)/);
 assert.doesNotMatch(build,/secrets-file/);
 assert.match(read('.github/workflows/dev-secret-persistence.yml'),/Workers Builds: gambling-community/);
 assert.match(read('.github/workflows/dev-secret-persistence.yml'),/keyConfigured/);
});

test('One-shot Azure validation endpoint is removed from running forum code after successful verification',()=>{
 const source=read('src/translation.ts');
 assert.doesNotMatch(source,/api\/dev\/azure-smoke/);
 assert.doesNotMatch(source,/function devAzureSmoke/);
 assert.doesNotMatch(source,/azure_dev_smoke_20261121/);
});

test('verified DEV and future PROD Identity Center Owners have separate hashed role selectors',()=>{
 const c=JSON.parse(read('wrangler.jsonc'));
 assert.equal(c.previews.vars.ADMIN_CENTER_OWNER_SHA256,'7df1b395981a31a651015a158eb1086264ecbea53b5dd41a34d62444ff29fa26');
 assert.equal(c.vars.ADMIN_CENTER_OWNER_SHA256,'eb367b5a659205efbacd7dfa4964e0c2a9852c072237b668d3d885e334105ba4');
 assert.notEqual(c.previews.vars.ADMIN_CENTER_OWNER_SHA256,c.vars.ADMIN_CENTER_OWNER_SHA256);
 assert.equal(c.previews.vars.IDENTITY_LOGIN_ENABLED,'true');
 assert.equal(c.vars.IDENTITY_LOGIN_ENABLED,'false','do not turn on PROD login prematurely');
 assert.equal(c.keep_vars,true);
 for(const v of [c.previews.vars,c.vars]){
   assert.equal(v.ADMIN_GOOGLE_SUB,undefined);
   assert.match(v.ADMIN_CENTER_OWNER_SHA256,/^[a-f0-9]{64}$/);
 }
 const src=read('src/core.ts');
 assert.match(src,/await hash\(centerUserId\)!==ownerHash/);
 assert.match(src,/ai\.provider='identity_center'/);
 assert.match(src,/identity_center_verified_owner/);
 assert.match(src,/env\.APP_ENV==='production'/);
 assert.match(src,/env\.APP_ENV==='preview'/);
 assert.match(src,/if\(!isAdmin&&env\.ADMIN_CENTER_OWNER_SHA256\)/);
 assert.match(read('src/auth.ts'),/await ensureVerifiedCenterOwnerAdmin\(env,uid,claims\.sub\)/);
});

test('collector HTTP surfaces remain isolated to Gambling Preview and preserve production deny',()=>{
 const c=JSON.parse(read('wrangler.jsonc'));
 assert.equal(c.vars.IMPORT_ENABLED,'false');
 assert.equal(c.vars.COLLECT_ENABLED,'false');
 assert.equal(c.previews.vars.IMPORT_ENABLED,'true');
 assert.equal(c.previews.vars.COLLECT_ENABLED,'true');
 const isolated=c.previews.d1_databases.find(d=>d.binding==='IMPORT_DB');
 assert.equal(isolated.database_id,'a92cf620-2a0b-46e1-a0ff-2e0c94218f37');
 assert.equal(c.d1_databases.some(d=>d.binding==='IMPORT_DB'),false);
 const imp=read('src/import.ts'),col=read('src/collect.ts'),index=read('src/index.ts');
 assert.match(imp,/APP_ENV==='preview'/);
 assert.match(imp,/dev-gambling-community[.]119shenhao[.]workers[.]dev/);
 assert.match(imp,/env[.]IMPORT_DB/);
 assert.match(col,/collectEnabled/);
 assert.match(col,/claim_not_owned_or_expired/);
 assert.match(index,/await importRoute\(req,env,path\)/);
 assert.match(index,/await collectRoute\(req,env,path\)/);
 assert.match(read('scripts/preview-migrate.mjs'),/migrations\/preview-only\/0001_collector_queue[.]sql/);
 assert.match(read('scripts/preview-migrate.mjs'),/migrations\/preview-only\/0002_collector_long[.]sql/);
 assert.match(read('migrations/preview-only/0002_collector_long.sql'),/ordinal BETWEEN 0 AND 499/);
 assert.match(read('src/collect-long.ts'),/MAX_REPLIES=500/);
 assert.match(read('src/collect.ts'),/collectLongRoute/);
 assert.match(read('src/index.ts'),/collect\/long\/finish/);
 assert.match(read('migrations/preview-only/0001_collector_queue.sql'),/CREATE TABLE IF NOT EXISTS collector_candidates/);
});

test('safe production sync is offline by default and uses only gambling D1',()=>{
 const prod=JSON.parse(read('wrangler.production-sync.jsonc'));
 assert.equal(prod.d1_databases[0].database_id,'7bba9ada-589f-493b-8fcf-60265fc0efac');
 const src=read('scripts/sync-preview-to-production.mjs');
 assert.match(src,/GAMBLING_SYNC_PRODUCTION_CONFIRM/);
 assert.match(src,/gambling-topic-v1/);
 assert.match(src,/topic_sync_receipts/);
 assert.match(src,/verifyComments/);
 assert.match(src,/verifyWrittenLanguageEvidence/);
 assert.doesNotMatch(src,/spine-topic-v1|SPINE_SYNC_PRODUCTION_CONFIRM/);
 const collectorSources=JSON.parse(read('scripts/gambling_sources.json')).sources;
 assert.ok(collectorSources.length>=1);
 const gamcare=collectorSources.find(s=>s.id==='gamcare');
 assert.ok(gamcare && gamcare.approved===true && gamcare.reuse_allowed===true &&
   gamcare.parser_verified===true && typeof gamcare.permission_evidence==='string' &&
   gamcare.permission_evidence.length>30);
 // A newly authorized data source is allowed only when its evidence is
 // recorded and the independent full parser verification gate is also true.
 assert.ok(collectorSources.every(s=>
   !(s.approved===true && s.reuse_allowed===true && s.parser_verified===true) ||
   (typeof s.permission_evidence==='string' && s.permission_evidence.length>30)));
 assert.ok(collectorSources.filter(s=>s.id==='gamblingtherapy').every(s=>
   s.approved===false && s.reuse_allowed===false && s.parser_verified===false));
 assert.ok(collectorSources.every(s=>s.adapter==='gambling_forums'));
 assert.ok(!collectorSources.some(s=>s.id==='spine'));
  assert.ok(['inspect','collect'].includes(JSON.parse(read('.github/gambling-collector-request.json')).mode));
 const py=spawnSync('python3',['-m','py_compile','scripts/gambling_collect.py'],{encoding:'utf8'});
 assert.equal(py.status,0,py.stderr);
});

test('sync candidate rows preserve language proof and idempotent Anonymous author mapping',async()=>{
 const {fingerprint,resolveSyncLanguage,sortComments,buildInserts}=await import('../scripts/sync-preview-to-production.mjs');
 const fp=fingerprint('  A  ',' B ');
 assert.match(fp,/^[a-f0-9]{64}$/);
 assert.deepEqual(resolveSyncLanguage({status:'published',source_lang:'en',source_lang_mode:'manual',content_version:1}),
   {label:'en',mode:'manual',method:null,score:null});
 assert.equal(resolveSyncLanguage({status:'published',source_lang:'en',source_lang_mode:'auto',
   content_version:2,verified_version:1,verified_method:'tinyld-heavy',verified_language:'en'}).label,'und');
 const nested=sortComments([
   {id:'child',parent_comment_id:'parent',status:'published',kind:'regular'},
   {id:'parent',parent_comment_id:null,status:'published',kind:'regular'},
   {id:'hidden',parent_comment_id:null,status:'hidden',kind:'regular'}
 ]);
 assert.deepEqual(nested.map(x=>x.id),['parent','child']);
 const topic={id:'00000000-0000-4000-8000-000000000001',title:'A',body:'B',
   status:'published',source_lang:'und',source_lang_mode:'legacy',content_version:1,
   symptom_duration_days:null,created_at:1};
 const sql=buildInserts(topic,[],[],fingerprint('A','B'));
 assert.match(sql,/system-unknown-import/);
 assert.match(sql,/INSERT OR IGNORE INTO topics/);
 assert.doesNotMatch(sql,/spine-topic-v1|spine-community/);
});


test('approved mobile casino-felt theme keeps reading preferences and four primary actions',()=>{
 const css=read('public/styles.css');
 const html=read('public/index.html');
 const app=read('public/app.js');
 assert.match(css,/Mobile visual baseline approved 2026-11-22/);
 assert.match(css,/--paper:\s*#173b26/);
 assert.match(css,/--bg:\s*#460a17/);
 assert.match(css,/--frame:\s*#c7a765/);
 assert.match(css,/grid-template-columns:repeat\(4,minmax\(0,1fr\)\)/);
 assert.match(css,/\[data-reading-theme="warm"\] \.topic-card/);
 assert.match(html,/<img src="\/dynamic-dice-option3-complete\.svg" alt="" width="31" height="31"/);
 const dice=read('public/dynamic-dice-option3-complete.svg');
 assert.match(dice,/viewBox="0 0 128 128"/);
 assert.match(dice,/transparent safety margin and a continuous gold rim/);
 const embedded=dice.match(/data:image\/png;base64,([^"]+)/)?.[1];
 assert.ok(embedded,'approved original artwork must be embedded');
 const png=Buffer.from(embedded,'base64');
 assert.equal(png.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
 assert.equal(png.readUInt32BE(16),128);
 assert.equal(png.readUInt32BE(20),128);
 // A byte-for-byte checksum guards against reintroducing the earlier cropped rim.
 const crypto=await import('node:crypto');
 assert.equal(crypto.createHash('sha256').update(png).digest('hex'),'1984f8b12032bd157c5e48f420130afbaada50511614ca4cf81f32515d5574c3');
 assert.doesNotMatch(html,/M16 3C12 9 5 12/);
 assert.match(app,/class="primary-nav"/);
 assert.match(app,/class="nav-link nav-compose"/);
 assert.match(app,/class="admin-nav"/);
 assert.match(app,/<a href="\/admin">/);
 assert.match(css,/\.sidebar \.admin-nav \{display:none;\}/);
 assert.match(css,/\.preview-badge:not\(\[hidden\]\)/);
 assert.match(css,/\.feed-heading::after/);
 assert.match(app,/function readingSettingsCard\(/);
});

test('compose action is visually distinct without affecting the other mobile tabs',()=>{
 const css=read('public/styles.css'),js=read('public/app.js');
 assert.match(css,/Final approved 2026-11-22: understated compose button only/);
 assert.match(css,/\.sidebar \.primary-nav \.nav-compose \{/);
 assert.match(css,/background:linear-gradient\(160deg,#12392b 0%,#082b20 100%\)/);
 assert.match(css,/border:2px solid #d3b06b/);
 assert.match(css,/font-weight:750/);
 assert.match(css,/\.sidebar \.primary-nav \.nav-compose::before \{display:none;\}/);
 assert.match(js,/data-action="compose"/);
});

test('approved dynamic die logo preserves a compact brand frame and all navigation',()=>{
 const css=read('public/styles.css'),html=read('public/index.html');
 const svg=read('public/dynamic-dice-option3-complete.svg');
 assert.match(css,/\.brand-icon \{border:0; background:transparent; box-shadow:none;\}/);
 assert.match(css,/:root:not\(\[data-reading-theme="warm"\]\) \.brand-icon,/);
 assert.match(css,/:root\[data-reading-theme="warm"\] \.brand-icon \{border:0;/);
 assert.match(css,/\.brand-icon img \{display:block; width:100%; height:100%; object-fit:contain;/);
 assert.match(html,/<span class="brand-icon" aria-hidden="true"><img src="\/dynamic-dice-option3-complete\.svg"/);
 assert.match(svg,/data:image\/png;base64,/);
 assert.doesNotMatch(svg,/<ellipse|<animate|<script/);
});
