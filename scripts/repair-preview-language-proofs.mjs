// DEV ONLY: audit and repair missing original-language proofs for historical imported
// content. Does not write to production, re-import posts or alter language labels.
// Newly imported content must write language + proof in the SAME D1 batch.
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {randomUUID} from 'node:crypto';

const DEV_ID='a92cf620-2a0b-46e1-a0ff-2e0c94218f37';
const PROD_ID='7bba9ada-589f-493b-8fcf-60265fc0efac';
const CONFIG='wrangler.preview-migrations.jsonc';
const argv=process.argv.slice(2);
const apply=argv.includes('--apply');
const arg=argv.find(a=>a.startsWith('--limit='));
const limit=arg?Number(arg.slice(8)):100;
if(argv.some(a=>a!=='--apply'&&!a.startsWith('--limit='))||
   !Number.isInteger(limit)||limit<1||limit>500)
 throw Error('Usage: node scripts/repair-preview-language-proofs.mjs [--limit=100] [--apply]');
const config=JSON.parse(readFileSync(CONFIG,'utf8'));
if(config.d1_databases?.length!==1||config.d1_databases[0].binding!=='PREVIEW_DB'||
   config.d1_databases[0].database_id!==DEV_ID||
   config.d1_databases[0].database_id===PROD_ID)
 throw Error('Unsafe: only the Gambling preview D1 database is allowed');
if(apply&&process.env.GAMBLING_PREVIEW_LANGUAGE_REPAIR_CONFIRM!==DEV_ID)
 throw Error('DEV-only repair requires GAMBLING_PREVIEW_LANGUAGE_REPAIR_CONFIRM');
const sqlValue=x=>x===null||x===undefined?'NULL':
 typeof x==='number'&&Number.isFinite(x)?String(x):
 "'"+String(x).replaceAll("'","''")+"'";
const validLanguage=x=>typeof x==='string'&&x!=='und'&&/^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?$/.test(x);
function wrangler(...tail){
 const r=spawnSync(process.execPath,['node_modules/wrangler/bin/wrangler.js','d1','execute',
  'PREVIEW_DB','--remote','--config',CONFIG,...tail,'--yes'],{
  encoding:'utf8',env:process.env,maxBuffer:32*1024*1024});
 if(r.status!==0)throw Error('Preview D1 command failed; no production writes');
 return r.stdout;
}
function query(statement){
 const raw=wrangler('--command',statement,'--json');
 let parsed;try{parsed=JSON.parse(raw);}catch{throw Error('Unexpected DEV D1 JSON');}
 if(!Array.isArray(parsed)||parsed.some(r=>r.success===false))throw Error('Invalid DEV D1 result');
 return parsed.flatMap(r=>r.results||[]);
}
async function detector(){
 // Bundle the original TypeScript detector used by the Worker. No copied or
 // weaker JS language detection logic is allowed in this repair path.
 const {build}=await import('esbuild');
 const bundle=await build({entryPoints:['src/source-language.ts'],bundle:true,
  platform:'node',format:'esm',write:false,logLevel:'silent'});
 if(bundle.outputFiles?.length!==1)throw Error('Source detector bundle unavailable');
 const file=resolve('scripts','.preview-language-detector-'+randomUUID()+'.mjs');
 try{
  writeFileSync(file,bundle.outputFiles[0].text,{mode:0o600});
  const mod=await import(pathToFileURL(file).href);
  if(typeof mod.detectSourceLanguageEvidence!=='function')throw Error('Detector export unavailable');
  return mod.detectSourceLanguageEvidence;
 }finally{rmSync(file,{force:true});}
}
function candidates(table,type){
 const alias=table==='topics'?'t':'c';
 const title=table==='topics'?alias+'.title AS title':'NULL AS title';
 return query(`SELECT ${alias}.id,${title},${alias}.body,${alias}.source_lang,
   ${alias}.content_version,v.language AS proof_language,v.method AS proof_method,
   v.content_version AS proof_version
   FROM ${table} ${alias}
   LEFT JOIN content_language_verifications v
    ON v.content_type=${sqlValue(type)} AND v.content_id=${alias}.id
     AND v.content_version=${alias}.content_version
   WHERE ${alias}.status='published' AND ${alias}.source_lang_mode='auto'
    AND ${alias}.source_lang<>'und'
    AND (v.content_id IS NULL OR v.language IS NULL OR v.language<>${alias}.source_lang
     OR v.method IS NULL OR v.method NOT IN ('tinyld-heavy','azure-auto','admin-manual'))
   ORDER BY ${alias}.id LIMIT ${limit}`);
}
function plannedStatement(row){
 const table=row.type==='topic'?'topics':'comments';
 return `INSERT OR IGNORE INTO content_language_verifications
   (content_type,content_id,content_version,language,method,score)
   SELECT ${sqlValue(row.type)},id,content_version,${sqlValue(row.lang)},'tinyld-heavy',
    ${sqlValue(row.score)}
   FROM ${table} WHERE id=${sqlValue(row.id)} AND content_version=${row.version}
    AND source_lang_mode='auto' AND status='published'
    AND source_lang=${sqlValue(row.lang)}
    AND NOT EXISTS (SELECT 1 FROM content_language_verifications
     WHERE content_type=${sqlValue(row.type)} AND content_id=${sqlValue(row.id)}
      AND content_version=${row.version});`;
}
async function run(){
 const recognize=await detector();
 const ready=[],review=[];
 for(const [table,type] of [['topics','topic'],['comments','comment']]){
  for(const row of candidates(table,type)){
   if(!Number.isInteger(row.content_version)||row.content_version<1||!validLanguage(row.source_lang)){
    review.push({type,id:row.id,reason:'invalid_dev_language_or_version'});continue;
   }
   if(row.proof_version!==null){
    review.push({type,id:row.id,reason:'conflicting_current_language_proof'});continue;
   }
   const evidence=type==='topic'?recognize(row.title,row.body):recognize(row.body);
   if(evidence.language!==row.source_lang){
    review.push({type,id:row.id,reason:'dev_language_disagrees_with_independent_detector',
      stored_language:row.source_lang,rechecked_language:evidence.language});continue;
   }
   ready.push({type,id:row.id,version:row.content_version,
    lang:row.source_lang,score:evidence.score});
  }
 }
 let applied=0;
 if(apply&&ready.length){
  const dir=mkdtempSync(join(tmpdir(),'gambling-preview-language-proof-'));
  try{
   const file=join(dir,'dev-proof-only.sql');
   writeFileSync(file,ready.map(plannedStatement).join('\n'),{mode:0o600});
   // Never pass PROD binding or a user-defined SQL/DB selector.
   wrangler('--file',file);
  }finally{rmSync(dir,{recursive:true,force:true});}
  for(const [type,table] of [['topic','topics'],['comment','comments']]){
   const rows=ready.filter(r=>r.type===type);
   for(let i=0;i<rows.length;i+=75){
    const group=rows.slice(i,i+75);
    const saved=query('SELECT content_id,content_version,language,method FROM content_language_verifications WHERE content_type='+
      sqlValue(type)+' AND content_id IN ('+group.map(r=>sqlValue(r.id)).join(',')+')');
    for(const item of group){
     if(!saved.some(v=>v.content_id===item.id&&v.content_version===item.version&&
        v.language===item.lang&&v.method==='tinyld-heavy'))
      throw Error('DEV proof post-write verification failed for '+item.id);
     applied++;
    }
   }
  }
 }
 const report={mode:apply?'apply':'inspect',database:'gambling-community-dev',
  missing_proofs_verified:ready.length,proofs_written_and_readback:applied,
  conflicts_requiring_review:review.length,
  review,verified_candidate_ids:ready.map(r=>({type:r.type,id:r.id,language:r.lang}))};
 console.log(JSON.stringify(report,null,2));
}
run().catch(err=>{console.error('DEV language proof repair stopped:',err.message);process.exitCode=1;});
