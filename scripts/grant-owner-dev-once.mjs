// ONE-TIME DEV ONLY administrative grant; remove from Cloudflare builds after receipt.
// No Google sub, account ID or email is committed or logged. We look up existing
// Center-verified auth_identities, compare its SHA-256, and grant exactly one.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';

if(process.env.WORKERS_CI!=='1'||process.env.WORKERS_CI_BRANCH!=='dev'){
 console.log('One-time DEV owner grant skipped outside the exact dev Preview build.');
 process.exit(0);
}
const cfg=JSON.parse(readFileSync('wrangler.jsonc','utf8'));
const db=cfg.previews?.d1_databases?.[0];
const realProd=cfg.d1_databases?.[0];
const expectedHash='7df1b395981a31a651015a158eb1086264ecbea53b5dd41a34d62444ff29fa26';
if(!cfg.keep_vars||cfg.name!=='gambling-community'||
   cfg.previews?.vars?.APP_ENV!=='preview'||cfg.previews?.vars?.IDENTITY_LOGIN_ENABLED!=='true'||
   cfg.previews?.vars?.ADMIN_CENTER_OWNER_SHA256!==expectedHash||
   cfg.previews?.vars?.IDENTITY_CLIENT_ID!=='gambling-community-dev'||
   cfg.previews?.vars?.IDENTITY_ISSUER!=='https://dev-identity-center.119shenhao.workers.dev'||
   cfg.vars?.APP_ENV!=='production'||cfg.vars?.IDENTITY_LOGIN_ENABLED!=='false'||
   !db||db.binding!=='DB'||db.database_name!=='gambling-community-dev'||
   db.database_id!=='a92cf620-2a0b-46e1-a0ff-2e0c94218f37'||
   !realProd||realProd.database_id!=='7bba9ada-589f-493b-8fcf-60265fc0efac'||
   db.database_id===realProd.database_id)throw Error('Unsafe DEV/PROD D1 or Owner binding. No role grant.');
const cli='node_modules/wrangler/bin/wrangler.js';
const args=['PREVIEW_DB','--remote','--config','wrangler.preview-migrations.jsonc'];
const command=sql=>{
 const p=spawnSync(process.execPath,[cli,'d1','execute',...args,'--command',sql,'--json'],
   {encoding:'utf8',stdio:'pipe',env:process.env,maxBuffer:2*1024*1024});
 if(p.status!==0)throw Error('DEV D1 role grant verification failed (no identifiers disclosed).');
 const rows=JSON.parse(p.stdout);
 if(!Array.isArray(rows)||rows.length!==1||rows[0]?.success!==true)
  throw Error('DEV D1 returned an invalid result; refusing to proceed.');
 return rows[0].results||[];
};
const qualified=command(`SELECT u.id,ai.provider_subject FROM auth_identities ai
 JOIN users u ON u.id=ai.user_id
 WHERE ai.provider='identity_center' AND u.status='active' AND u.is_system=0 LIMIT 300`);
const hash=x=>createHash('sha256').update(x).digest('hex');
const selected=qualified.filter(row=>typeof row.provider_subject==='string'&&hash(row.provider_subject)===expectedHash);
if(selected.length===0)
 throw Error('No matching verified Center Owner account in Gambling DEV D1; refusing to claim completed admin grant.');
if(selected.length!==1)throw Error('Ambiguous Center Owner identity in DEV D1; no grant.');
const owner=selected[0];
const uuid=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
if(!uuid.test(owner.id)||!uuid.test(owner.provider_subject))
 throw Error('Malformed DEV account identity; no grant.');
const existing=command(`SELECT role FROM user_roles WHERE user_id='${owner.id}' AND role='admin'`);
if(existing.length===0){
 const granted=command(`INSERT OR IGNORE INTO user_roles(user_id,role)
  SELECT u.id,'admin' FROM users u
  JOIN auth_identities ai ON ai.user_id=u.id
  WHERE u.id='${owner.id}' AND ai.provider='identity_center'
   AND ai.provider_subject='${owner.provider_subject}'
   AND u.status='active' AND u.is_system=0 RETURNING role`);
 if(granted.length!==1||granted[0].role!=='admin')throw Error('DEV Owner grant was not confirmed.');
 command(`INSERT INTO moderation_actions(id,actor_id,target_type,target_id,action,reason)
  VALUES(lower(hex(randomblob(16))),'${owner.id}','role','${owner.id}',
    'grant_admin','identity_center_verified_owner')`);
}
const verified=command(`SELECT role FROM user_roles WHERE user_id='${owner.id}' AND role='admin'`);
if(verified.length!==1)throw Error('Owner DEV D1 role grant readback failed.');
console.log('PASS: Exactly the verified Identity Center DEV Owner has Gambling forum admin role in DEV D1.');
console.log('Production D1, all other users, Cloudflare Secrets and Worker bindings were not modified.');
