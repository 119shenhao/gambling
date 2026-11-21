#!/usr/bin/env node
// ONE-TIME production-only OAuth registration. Runs in the exact Cloudflare
// Workers Build for main while sign-in is still disabled. Remove after receipt.
import {createHash,randomBytes} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';

if(process.env.WORKERS_CI!=='1'||process.env.WORKERS_CI_BRANCH!=='main'){
  console.log('PROD identity provision skipped outside Cloudflare main build.');
  process.exit(0);
}
const cfg=JSON.parse(readFileSync('wrangler.jsonc','utf8'));
const d=cfg.d1_databases||[],p=cfg.previews?.d1_databases||[];
const prodId='7bba9ada-589f-493b-8fcf-60265fc0efac';
const devId='a92cf620-2a0b-46e1-a0ff-2e0c94218f37';
if(cfg.name!=='gambling-community'||cfg.keep_vars!==true||
   cfg.vars?.APP_ENV!=='production'||cfg.vars?.IDENTITY_LOGIN_ENABLED!=='false'||
   cfg.vars?.TRANSLATION_ENABLED!=='false'||
   cfg.vars?.IDENTITY_CLIENT_ID!=='gambling-community-prod'||
   cfg.vars?.IDENTITY_ISSUER!=='https://idcenter.nbn369.com'||
   cfg.vars?.IDENTITY_REDIRECT_URI!=='https://gambling.nbn369.com/api/auth/identity/callback'||
   d.length!==1||d[0].binding!=='DB'||d[0].database_id!==prodId||
   d[0].database_name!=='gambling-community-prod'||p.length!==1||p[0].database_id!==devId)
 throw Error('Production OAuth provisioning: expected isolated disabled production configuration.');

function wrangler(args,stdin){
  const r=spawnSync(process.execPath,['node_modules/wrangler/bin/wrangler.js',...args],{
    encoding:'utf8',stdio:['pipe','pipe','pipe'],input:stdin,env:process.env,timeout:120000,maxBuffer:2*1024*1024});
  if(r.error||r.status!==0){
    const reason=/403|permission|forbidden|unauthorized/i.test((r.stdout||'')+(r.stderr||''))?'permission_denied':'operation_failed';
    // Never expose CLI output; could contain OAuth secret material.
    throw Error('PROD OAuth secret / D1 CLI failed ('+reason+'); no credentials printed.');
  }
  return r.stdout;
}
function query(sql){
 const raw=wrangler(['d1','execute','DB','--remote','--config','wrangler.jsonc','--json','--command',sql]);
 const j=JSON.parse(raw);
 if(!Array.isArray(j)||j.length!==1||j[0]?.success===false||!Array.isArray(j[0]?.results))
   throw Error('Unexpected PROD D1 result; stopping');
 return j[0].results;
}
const oldReceipts=['gambling_identity_prod_secret_digest','gambling_identity_prod_secret_verified'];
const read=k=>query("SELECT value FROM settings WHERE key='"+k+"'")[0]?.value||'';
const migration=query("SELECT name FROM d1_migrations WHERE name='0100_identity_center.sql'");
if(migration.length!==1)throw Error('PROD D1 identity migration missing');
const admin=query("SELECT user_id FROM user_roles WHERE role='admin'");
if(admin.length!==1)throw Error('PROD verified Owner role not present; refusing to bootstrap Secret');
// Non-sensitive milestone confirms the Cloudflare Build token could reach
// ONLY the authorized Gambling production D1 before Worker Secret metadata.
query("INSERT INTO settings(key,value) VALUES('gambling_prod_oauth_bootstrap_stage','d1_verified') ON CONFLICT(key) DO UPDATE SET value=excluded.value");
const hasSecret=()=>{
 const list=JSON.parse(wrangler(['secret','list','--name','gambling-community','--format','json']));
 if(!Array.isArray(list))throw Error('PROD Worker Secret metadata invalid');
 return list.some(x=>x.name==='IDENTITY_CLIENT_SECRET'&&x.type==='secret_text');
};
const digestPattern=/^[A-Za-z0-9_-]{43}$/;
let digest=read(oldReceipts[0]),verified=read(oldReceipts[1]);
if(hasSecret()){
 if(!digestPattern.test(digest)||digest!==verified)
   throw Error('Existing PROD Worker SSO Secret found without approved receipt; no rotation');
 console.log('Existing verified PROD SSO Secret preserved without rotation.');
}else{
 if(digest||verified)throw Error('PROD D1 receipt found but Worker Secret absent; manual recovery required');
 const secret=randomBytes(48).toString('base64url');
 digest=createHash('sha256').update(secret).digest('base64url');
 if(!digestPattern.test(digest))throw Error('Invalid Secret digest generated');
 query("INSERT INTO settings(key,value) VALUES('"+oldReceipts[0]+"','"+digest+
   "') ON CONFLICT(key) DO UPDATE SET value=excluded.value");
 wrangler(['secret','put','IDENTITY_CLIENT_SECRET','--name','gambling-community','--config','wrangler.jsonc'],secret+'\n');
 if(!hasSecret())throw Error('PROD Secret was not present after upload');
 query("INSERT INTO settings(key,value) VALUES('"+oldReceipts[1]+"','"+digest+
  "') ON CONFLICT(key) DO UPDATE SET value=excluded.value");
 console.log('Installed NEW independent production SSO Secret in Cloudflare Worker; no plaintext logged.');
}
if(read(oldReceipts[0])!==digest||read(oldReceipts[1])!==digest)
 throw Error('PROD Worker/D1 Secret receipt mismatched');
console.log('PASS: verified PROD Worker SSO Secret metadata and D1 hashed receipts. Identity Center client still disabled.');
