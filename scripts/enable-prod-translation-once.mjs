#!/usr/bin/env node
// ONE-TIME guarded PROD D1 Azure translation enablement.
// No Secret mutation, no preview/Spine writes. D1 receipt prevents later
// builds from reenabling translation when the administrator pauses it.
import {readFileSync,writeFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
if(process.env.WORKERS_CI!=='1'||process.env.WORKERS_CI_BRANCH!=='main'){
 console.log('Production translation bootstrap skipped outside Cloudflare main build.');
 process.exit(0);
}
const PROD_ID='7bba9ada-589f-493b-8fcf-60265fc0efac';
const DEV_ID='a92cf620-2a0b-46e1-a0ff-2e0c94218f37';
const RECEIPT='gambling_prod_translation_20261122';
const cfg=JSON.parse(readFileSync('wrangler.jsonc','utf8'));
const prod=cfg.d1_databases||[],dev=cfg.previews?.d1_databases||[];
const v=cfg.vars||{},preview=cfg.previews?.vars||{};
if(cfg.name!=='gambling-community'||cfg.keep_vars!==true||
 v.APP_ENV!=='production'||v.TRANSLATION_ENABLED!=='true'||
 v.TRANSLATION_DAILY_LIMIT!=='200000'||v.TRANSLATION_MONTHLY_LIMIT!=='1800000'||
 v.TRANSLATOR_REGION!=='eastus'||v.TRANSLATOR_KEY!==undefined||
 v.IDENTITY_ISSUER!=='https://idcenter.nbn369.com'||
 v.IDENTITY_CLIENT_ID!=='gambling-community-prod'||
 v.IDENTITY_LOGIN_ENABLED!=='true'||
 prod.length!==1||prod[0].binding!=='DB'||
 prod[0].database_name!=='gambling-community-prod'||prod[0].database_id!==PROD_ID||
 dev.length!==1||dev[0].database_name!=='gambling-community-dev'||dev[0].database_id!==DEV_ID||
 preview.APP_ENV!=='preview'||preview.TRANSLATION_MONTHLY_LIMIT!=='10000'||
 preview.TRANSLATION_DAILY_LIMIT!=='5000'||preview.TRANSLATION_ENABLED!=='true'||
 preview.TRANSLATOR_KEY!==undefined)
 throw Error('Production translation environment or D1 isolation mismatch.');
const verified=Date.parse(v.TRANSLATOR_F0_VERIFIED_AT||'');
if(!Number.isFinite(verified)||verified>Date.now()||
 Date.now()-verified>31*86400*1000)
 throw Error('Azure F0 verification marker stale; refusing production enablement.');
const runner='node_modules/wrangler/bin/wrangler.js';
function invoke(args){
 const r=spawnSync(process.execPath,[runner,...args],{
  env:process.env,encoding:'utf8',stdio:['ignore','pipe','pipe'],
  timeout:120000,maxBuffer:1024*1024
 });
 if(r.status!==0)throw Error('Production Wrangler '+args[0]+' failed; output suppressed.');
 return r.stdout;
}
const keys=JSON.parse(invoke(['secret','list','--name','gambling-community','--format','json']));
if(!Array.isArray(keys)||!keys.some(x=>x?.name==='TRANSLATOR_KEY'))
 throw Error('Production Azure Secret not present, leaving translation disabled.');
writeFileSync('wrangler.prod-translation-once.jsonc',JSON.stringify({
 name:'gambling-prod-translation-once',compatibility_date:'2026-11-06',
 d1_databases:[{binding:'PROD_TRANSLATION_DB',
  database_name:'gambling-community-prod',database_id:PROD_ID}]
}));
function sql(command){
 const data=JSON.parse(invoke(['d1','execute','PROD_TRANSLATION_DB','--remote','--config',
  'wrangler.prod-translation-once.jsonc','--command',command,'--json']));
 if(!Array.isArray(data)||data.length!==1||data[0]?.success!==true||
  !Array.isArray(data[0]?.results))
  throw Error('Production D1 statement failed; refusing deployment.');
 return data[0].results;
}
if(sql("SELECT name FROM d1_migrations WHERE name='0012_automatic_translation.sql'").length!==1||
 sql('SELECT id FROM translation_budget WHERE id=1').length!==1)
 throw Error('Production D1 schema or budget row missing.');
const receipt=sql("SELECT value FROM settings WHERE key='"+RECEIPT+"'");
if(receipt.length>1||receipt[0]&&receipt[0].value!=='applied')
 throw Error('Unexpected production translation bootstrap receipt.');
if(receipt.length===1){
 console.log('PASS: production translation receipt exists; administrative settings preserved.');
 process.exit(0);
}
const expected=[
 ['translation_active_provider','azure'],
 ['translation_azure_daily_limit','200000'],
 ['translation_azure_monthly_limit','1800000'],
 ['translation_enabled','true'],
 [RECEIPT,'applied']
];
// This one SQLite UPSERT is atomic and retains the existing usage counters.
const tuples=expected.map(([key,value])=>"('"+key+"','"+value+"')").join(',');
sql('INSERT INTO settings(key,value) VALUES'+tuples+
 ' ON CONFLICT(key) DO UPDATE SET value=excluded.value');
const states=sql("SELECT key,value FROM settings WHERE key IN ("+
 expected.map(([key])=>"'"+key+"'").join(',')+")");
if(states.length!==expected.length||
 expected.some(([key,value])=>states.find(s=>s.key===key)?.value!==value))
 throw Error('Production D1 translation settings readback mismatch.');
console.log('PASS: production Azure enabled; daily 200000, monthly 1800000; receipt verified.');
console.log('PASS: previously recorded usage counters and existing Secrets preserved.');
