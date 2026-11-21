#!/usr/bin/env node
// ONE-TIME production-only OAuth Secret bootstrap. DO NOT execute manually.
// No credentials, user IDs, secret digests or Cloudflare token contents are logged.
import {randomBytes,createHash} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
if(process.env.WORKERS_CI!=='1'||process.env.WORKERS_CI_BRANCH!=='main'){
 console.log('PROD OAuth bootstrap skipped: only the exact Cloudflare production build can run it.');
 process.exit(0);
}
const prodId='7bba9ada-589f-493b-8fcf-60265fc0efac';
const devId='a92cf620-2a0b-46e1-a0ff-2e0c94218f37';
const worker='gambling-community';
const secretName='IDENTITY_CLIENT_SECRET';
const receipt='gambling_identity_prod_secret_digest';
const verified='gambling_identity_prod_secret_verified';
const cfg=JSON.parse(readFileSync('wrangler.jsonc','utf8'));
const pd=cfg.d1_databases||[],dv=cfg.previews?.d1_databases||[];
if(cfg.name!==worker||cfg.keep_vars!==true||cfg.vars?.APP_ENV!=='production'||
 cfg.vars?.IDENTITY_LOGIN_ENABLED!=='false'||
 cfg.vars?.IDENTITY_ISSUER!=='https://idcenter.nbn369.com'||
 cfg.vars?.IDENTITY_CLIENT_ID!=='gambling-community-prod'||
 cfg.vars?.IDENTITY_REDIRECT_URI!=='https://gambling.nbn369.com/api/auth/identity/callback'||
 pd.length!==1||pd[0].binding!=='DB'||pd[0].database_id!==prodId||
 pd[0].database_name!=='gambling-community-prod'||
 dv[0]?.database_id!==devId||pd[0].database_id===dv[0]?.database_id||
 cfg.vars?.TRANSLATION_ENABLED!=='false'||
 cfg.vars?.TRANSLATOR_KEY!==undefined||cfg.previews?.vars?.IDENTITY_CLIENT_SECRET!==undefined)
 throw Error('Refusing OAuth secret provisioning: production environment and Secret isolation do not match.');
const wrangler='node_modules/wrangler/bin/wrangler.js';
const invoke=(args,input)=>{
 const r=spawnSync(process.execPath,[wrangler,...args],{
  input,encoding:'utf8',timeout:120000,stdio:['pipe','pipe','pipe'],
  env:process.env,maxBuffer:1024*1024
 });
 if(r.status!==0){
  const reason=/403|unauthorized|forbidden|permission/i.test((r.stderr||'')+(r.stdout||''))?'permission_denied':'operation_failed';
  throw Error('PROD Wrangler '+args[0]+' failed ('+reason+'). Output suppressed.');
 }
 return r.stdout;
};
function meta(){
 const rows=JSON.parse(invoke(['secret','list','--name',worker,'--json']));
 if(!Array.isArray(rows))throw Error('Production Worker Secret metadata malformed.');
 return new Set(rows.map(x=>x?.name).filter(x=>typeof x==='string'));
}
function sql(command){
 const output=invoke(['d1','execute','PROD_DB','--remote','--config',
    'wrangler.prod-identity-setup.jsonc','--command',command,'--json']);
 const records=JSON.parse(output);
 if(!Array.isArray(records)||records.length!==1||records[0]?.success!==true||
    !Array.isArray(records[0].results))throw Error('Production D1 query unsuccessful.');
 return records[0].results;
}
writeFileSync('wrangler.prod-identity-setup.jsonc',JSON.stringify({
 name:'gambling-prod-identity-setup',compatibility_date:'2026-11-06',
 d1_databases:[{binding:'PROD_DB',database_name:'gambling-community-prod',database_id:prodId}]
}));
const applied=sql("SELECT name FROM d1_migrations WHERE name='0100_identity_center.sql'");
if(applied.length!==1)throw Error('Production D1 missing unified identity schema.');
const count=sql("SELECT count(*) AS n FROM user_roles WHERE role='admin'");
if(count.length!==1||count[0].n!==1)throw Error('Production Owner role not uniquely present; no Secret change.');
const readKey=key=>{
 const rows=sql("SELECT value FROM settings WHERE key='"+key+"'");
 if(rows.length>1)throw Error('Duplicate production receipt.');
 return rows[0]?.value||'';
};
const digestPattern=/^[A-Za-z0-9_-]{43}$/;
const names=meta();
if(!names.has('TRANSLATOR_KEY'))
 throw Error('Existing PRODUCTION Azure Translator Secret missing; refuse any credential changes.');
let digest=readKey(receipt);
let confirmed=readKey(verified);
if(names.has(secretName)){
 if(!digestPattern.test(digest)||!confirmed||confirmed!==digest)
  throw Error('Production OAuth Secret already present but verified receipt missing. Refuse rotation.');
 console.log('PASS: previously provisioned PROD identity credential and verified receipt retained.');
 process.exit(0);
}
if(digest||confirmed)throw Error('Existing receipt without production OAuth Secret; manual investigation required.');
const secret=randomBytes(48).toString('base64url');
digest=createHash('sha256').update(secret).digest('base64url');
if(!digestPattern.test(digest))throw Error('Unexpected verifier format.');
sql("INSERT INTO settings(key,value) VALUES('"+receipt+"','"+digest+
 "') ON CONFLICT(key) DO UPDATE SET value=excluded.value");
invoke(['secret','put',secretName,'--name',worker],secret+'\n');
const updated=meta();
if(!updated.has(secretName)||!updated.has('TRANSLATOR_KEY'))
 throw Error('Production Secret post-write metadata check failed; no login enabled.');
sql("INSERT INTO settings(key,value) VALUES('"+verified+"','"+digest+
 "') ON CONFLICT(key) DO UPDATE SET value=excluded.value");
if(readKey(verified)!==digest||readKey(receipt)!==digest)
 throw Error('Production credential digest readback failed.');
console.log('PASS: independent Gambling PROD OAuth Worker Secret configured with verified D1 receipt.');
console.log('PASS: preexisting production Azure Translator Secret remained present.');
console.log('Identity Center PROD client remains disabled until separate authorized activation.');
