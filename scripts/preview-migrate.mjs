// Only in Cloudflare's dev Preview build; never runs for GitHub CI, local builds or production.
import {existsSync,readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
const previewBuild=process.env.WORKERS_CI==='1'&&process.env.WORKERS_CI_BRANCH==='dev';
if(!previewBuild){
 console.log('Remote migrations skipped: not Cloudflare dev Preview.');
}else if(!existsSync('wrangler.preview-migrations.jsonc')){
 console.log('Remote migrations pending: gambling-community-dev UUID has not yet been verified.');
}else{
 const conf=JSON.parse(readFileSync('wrangler.jsonc','utf8'));
 const mig=JSON.parse(readFileSync('wrangler.preview-migrations.jsonc','utf8'));
 const preview=conf.previews?.d1_databases||[];
 const production=conf.d1_databases||[];
 const p=preview.filter(x=>x.binding==='DB');
 const x=(mig.d1_databases||[]).filter(x=>x.binding==='PREVIEW_DB');
 const uuid=/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
 const sourceDBs=new Set(['5919ff78-b8fc-46ab-85f0-01fe5e6a41b0','4362537a-5748-4a05-b0c4-219c3db36996','66c36ee9-2cab-4e85-bc02-645819344297']);
 if(conf.name!=='gambling-community'||conf.vars?.APP_ENV!=='production'||conf.previews?.vars?.APP_ENV!=='preview'||
    p.length!==1||x.length!==1||!uuid.test(p[0].database_id)||
    p[0].database_name!=='gambling-community-dev'||x[0].database_name!=='gambling-community-dev'||
    p[0].database_id!==x[0].database_id||p[0].database_id!=='a92cf620-2a0b-46e1-a0ff-2e0c94218f37'||production.length!==1||production[0].database_name!=='gambling-community-prod'||production[0].database_id!=='7bba9ada-589f-493b-8fcf-60265fc0efac'||p[0].migrations_dir!=='migrations/v1'||x[0].migrations_dir!=='migrations/v1'||
    production.some(d=>d.database_id===p[0].database_id)||
    sourceDBs.has(p[0].database_id)||sourceDBs.has(production[0].database_id)||
    (conf.previews?.r2_buckets||[]).filter(b=>b.binding==='PUBLIC_CONTENT_R2'&&b.bucket_name==='gambling-community-public-dev').length!==1||
    (conf.r2_buckets||[]).filter(b=>b.binding==='PUBLIC_CONTENT_R2'&&b.bucket_name==='gambling-community-public-prod').length!==1||
    conf.previews?.vars?.IMPORT_ENABLED!=='false'||conf.previews?.vars?.COLLECT_ENABLED!=='false')
   throw Error('Preview binding does not match the isolated gambling-community-dev resource; no migration attempted.');
 const cli='node_modules/wrangler/bin/wrangler.js';
 function remote(args){
  const r=spawnSync(process.execPath,[cli,'d1',...args],{encoding:'utf8',stdio:'pipe',env:process.env,maxBuffer:2*1024*1024});
  if(r.status!==0)throw Error('Cloudflare dev D1 command failed. Check Preview build permissions and the verified DB UUID.');
  return r.stdout;
 }
 const opts=['PREVIEW_DB','--remote','--config','wrangler.preview-migrations.jsonc'];
 let before;
 try{before=JSON.parse(remote(['execute',...opts,'--command',"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users','topics','settings')",'--json']));}
 catch(e){throw Error('Could not read isolated Preview D1 schema; migration stopped.');}
 const found=new Set(before.flatMap(o=>o.results||[]).map(o=>o.name));
 if(found.size>0&&!['users','topics','settings'].every(t=>found.has(t)))
  throw Error('Unrecognized partial Preview schema; refusing to modify D1.');
 remote(['migrations','apply',...opts]);
 const after=JSON.parse(remote(['execute',...opts,'--command',"SELECT value FROM settings WHERE key='schema_version'",'--json']));
 if(!after.some(r=>(r.results||[]).some(x=>x.value==='1')))throw Error('Preview schema version check failed after migration.');
 console.log('Verified migrations on gambling-community-dev only. Production D1 not accessed.');
}
