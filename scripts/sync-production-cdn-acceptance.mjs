// Production D1 -> R2 -> Cloudflare CDN acceptance gate for the protected sync executor.
// Never directly writes PROD D1/R2 or invokes the CDN purge API from GitHub.
// CDN acknowledgements persist only in the isolated DEV D1 companion ledger.
// The production Worker owns the queue, R2 publishing and zone-purge secret.
import {readFileSync,existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';

const PROD_DB='7bba9ada-589f-493b-8fcf-60265fc0efac';
const PREVIEW_DB='a92cf620-2a0b-46e1-a0ff-2e0c94218f37';
const ACCOUNT='289976272520a38732bef34108585e11';
const WORKER='https://gambling.nbn369.com';
const CDN='https://gambling-data.nbn369.com';
const IDENT=/^[A-Za-z0-9_-]{1,128}$/;
const MAX_QUEUE=300;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const signal=()=>AbortSignal.timeout(12500);

export function parseWranglerResults(text){
 const items=JSON.parse(text);
 if(!Array.isArray(items)||items.some(x=>x?.success!==true||!Array.isArray(x.results)))
  throw Error('Unsuccessful or malformed production D1 result');
 return items.flatMap(x=>x.results);
}
export function assertProdConfig(config,env){
 if(env.CLOUDFLARE_ACCOUNT_ID!==ACCOUNT||!env.CLOUDFLARE_API_TOKEN||
    env.GAMBLING_SYNC_PRODUCTION_CONFIRM!==PROD_DB)
  throw Error('Protected production D1 executor credentials or target mismatch');
 if(config?.d1_databases?.length!==1||
    config.d1_databases[0].database_id!==PROD_DB||
    config.d1_databases[0].binding!=='PRODUCTION_DB')
  throw Error('Production D1 binding does not match reviewed target');
}
export function assertReadiness(health){
 if(health?.environment!=='production'||health?.databaseReady!==true||
   health?.publicContent?.ready!==true||
   health?.publicContent?.enabled!==true||
   health?.publicContent?.purgeConfigured!==true||
   health?.publicContent?.onDemand!==true||
   health?.publicContent?.fallback!==true||
   health?.publicContent?.baseUrl!==CDN)
  throw Error('PROD R2/CDN is not activated and purge-ready: STOP BEFORE D1 WRITES');
}
export function verifyEnvelope(scope,target,record,response,cacheControl,pageSize=50){
 const version=Number(record.version);
 if(!response||response.schemaVersion!==1||response.contentVersion!==version||
   response.invalidated===true||response.data?.translationLayout!=='separate-v1')
  throw Error('CDN version/content mismatch: '+scope+'/'+target);
 if(scope==='topic'){
  if(response.topicId!==target||response.data.topic?.id!==target||
     !Array.isArray(response.data.comments)||
     !Array.isArray(response.data.progress)||
     response.data.topic.content_version!==Number(record.content_version)||
     response.data.topic.reply_count!==Number(record.reply_count)||
     response.data.comments.length!==Math.min(pageSize,Number(record.comment_count)))
   throw Error('CDN topic/replies mismatch: '+target);
 }else if(!Array.isArray(response.data.topics))
  throw Error('CDN latest feed schema mismatch');
 // A touched object MUST have the long-cache policy, not a legacy 60s object.
 const ttl=scope==='feed'?86400:604800;
 if(!new RegExp('(?:^|,\\s*)s-maxage='+ttl+'(?:,|$)').test(cacheControl||''))
  throw Error('CDN still has legacy/invalid TTL on '+scope+'/'+target);
}
export function parseManifest(raw){
 if(!raw.trim())return [];
 const ids=new Set();
 for(const line of raw.trim().split(/\r?\n/)){
  const data=JSON.parse(line);
  if(!IDENT.test(data.id)||Object.keys(data).some(k=>!['id','comments'].includes(k)))
   throw Error('Untrusted CDN manifest entry');
  ids.add(data.id);
 }
 return [...ids];
}
const query=(sql,preview=false)=>{
 const args=['node_modules/wrangler/bin/wrangler.js','d1','execute',preview?'PREVIEW_DB':'PRODUCTION_DB',
   '--remote','--config',preview?'wrangler.preview-migrations.jsonc':'wrangler.production-sync.jsonc',
   '--command',sql,'--json','--yes'];
 const p=spawnSync(process.execPath,args,{encoding:'utf8',maxBuffer:5*1024*1024,timeout:60000});
 if(p.error||p.status!==0)throw Error((preview?'DEV':'PROD')+' D1 query failed: '+String(p.stderr||p.error||'').slice(0,250));
 return parseWranglerResults(p.stdout);
};
function previewLedger(){
 const rows=query("SELECT name FROM sqlite_master WHERE type='table' AND name='topic_cdn_sync_acceptance'",true);
 if(rows.length!==1)throw Error('DEV durable CDN acceptance ledger missing: STOP BEFORE D1 WRITES');
}
function unacceptedReceipts(){
 return query('SELECT source_topic_id,production_topic_id FROM topic_cdn_sync_acceptance '+
   'WHERE verified_at IS NULL ORDER BY created_at,source_topic_id LIMIT '+(MAX_QUEUE+1),true);
}
function ackAcceptedReceipts(receipts,versions){
 for(let i=0;i<receipts.length;i+=40){
  const batch=receipts.slice(i,i+40);
  const quote=id=>"'"+id.replaceAll("'","''")+"'";
  const cases=batch.map(row=>{
   const version=versions.get(row.production_topic_id);
   if(!Number.isSafeInteger(version)||version<1)throw Error('Missing accepted R2 projection version');
   return 'WHEN '+quote(row.source_topic_id)+' THEN '+version;
  });
  const sql='UPDATE topic_cdn_sync_acceptance SET verified_at=unixepoch(),verified_version=CASE source_topic_id '+
   cases.join(' ')+' ELSE verified_version END WHERE verified_at IS NULL AND source_topic_id IN ('+
   batch.map(row=>quote(row.source_topic_id)).join(',')+') RETURNING source_topic_id';
  const changed=query(sql,true);
  if(changed.length!==batch.length)throw Error('DEV CDN acceptance acknowledgements are incomplete');
 }
}
async function health(){
 const r=await fetch(WORKER+'/api/health',{redirect:'error',signal:signal()});
 if(!r.ok)throw Error('PROD health HTTP '+r.status);
 const data=await r.json();
 assertReadiness(data);
 return data;
}
async function wake(key){
 const page=key==='feeds/latest/page-1.json';
 const path=page?'/api/topics?sort=latest&offset=0':'/api/topics/'+encodeURIComponent(key.split('/')[1]);
 const response=await fetch(WORKER+path,{headers:{'x-gambling-projection-miss':key},
   redirect:'error',signal:signal()});
 if(!response.ok)throw Error('Production Worker projection wake failed: HTTP '+response.status+' '+key);
 // No source content or private user data is logged.
}
async function cdn(key){
 const response=await fetch(CDN+'/'+key,{headers:{Origin:WORKER},signal:signal(),redirect:'error'});
 if(!response.ok)return {status:response.status,cache:response.headers.get('cf-cache-status')};
 return {status:200,cache:response.headers.get('cf-cache-status'),
   control:response.headers.get('cache-control'),body:await response.json()};
}
function rowFor(scope,target){
 const id=target.replaceAll("'","''");
 return query(scope==='feed'
  ?"SELECT scope,target,version,published_version,state,last_error,0 content_version,0 reply_count,0 comment_count FROM public_projection WHERE scope='feed' AND target='latest'"
  : "SELECT p.scope,p.target,p.version,p.published_version,p.state,p.last_error,t.content_version,t.reply_count,"+
    "(SELECT count(*) FROM comments c WHERE c.topic_id=t.id AND c.status IN ('published','deleted')) comment_count "+
    "FROM public_projection p JOIN topics t ON t.id=p.target WHERE p.scope='topic' AND p.target='"+id+"' AND t.status='published'");
}
function pending(){
 return query("SELECT p.scope,p.target FROM public_projection p LEFT JOIN topics t ON p.scope='topic' AND t.id=p.target "+
   "WHERE (p.scope='feed' OR (p.scope='topic' AND t.author_id='system-unknown-import')) "+
   "AND (p.state<>'done' OR p.published_version<>p.version) "+
   "ORDER BY CASE WHEN p.scope='feed' THEN 0 ELSE 1 END,p.updated_at,p.target LIMIT "+(MAX_QUEUE+1));
}
async function accept(scope,target,deadline){
 const key=scope==='feed'?'feeds/latest/page-1.json':'topics/'+target+'/detail.json';
 let last='not_checked',tries=0;
 while(Date.now()<deadline){
  const rows=rowFor(scope,target);
  if(rows.length!==1)throw Error('Production D1 projection absent or content not published for '+scope+'/'+target);
  const row=rows[0];
  if(row.state==='dead')throw Error('Production CDN refresh dead-letter; manual intervention required for '+scope+'/'+target+' reason '+row.last_error);
  tries++;
  const r=await cdn(key);
  if(row.state==='done'&&row.published_version===row.version&&r.status===200){
   try{
    verifyEnvelope(scope,target,row,r.body,r.control);
    return {key,version:row.version,tries,cache:r.cache||null};
   }catch(e){last=e.message;}
  }else last='D1 projection='+row.state+' published='+row.published_version+' expected='+row.version+' CDN='+r.status;
  if(tries%2===1)await wake(key);
  await sleep(3000);
 }
 throw Error('Production CDN acceptance timed out for '+scope+'/'+target+': '+last);
}
async function main(){
 const [mode]=process.argv.slice(2);
 if(!['preflight','verify'].includes(mode))throw Error('Usage: node scripts/sync-production-cdn-acceptance.mjs preflight|verify');
 const env=process.env;
 assertProdConfig(JSON.parse(readFileSync('wrangler.production-sync.jsonc','utf8')),env);
 const previewCfg=JSON.parse(readFileSync('wrangler.preview-migrations.jsonc','utf8'));
 if(previewCfg?.d1_databases?.length!==1||previewCfg.d1_databases[0].binding!=='PREVIEW_DB'||
   previewCfg.d1_databases[0].database_id!==PREVIEW_DB)
  throw Error('Untrusted DEV D1 receipt binding: STOP BEFORE D1 WRITES');
 previewLedger();
 await health();
 console.log('PASS: production CDN fail-closed preflight (Worker R2 and purge readiness confirmed)');
 if(mode==='preflight')return;
 const path=env.GAMBLING_SYNC_CDN_MANIFEST_PATH;
 const runnerTemp=resolve(env.RUNNER_TEMP||'/tmp');
 if(!path||!resolve(path).startsWith(runnerTemp+'/'))throw Error('Protected runner manifest path missing');
 const ids=parseManifest(existsSync(path)?readFileSync(path,'utf8'):'');
 // Unlike the ephemeral GitHub manifest, these source receipts survive failed jobs.
 const receipts=unacceptedReceipts();
 if(receipts.length>MAX_QUEUE)throw Error('Unbounded DEV CDN acceptance backlog');
 if(receipts.some(row=>!IDENT.test(row.source_topic_id)||!IDENT.test(row.production_topic_id)))
  throw Error('Invalid durable CDN acceptance receipt');
 // Also recover unfinished PROD R2 purge attempts even when a source is already synced.
 const queue=pending();
 if(queue.length>MAX_QUEUE)throw Error('Unbounded production CDN queue; investigation required');
 const topics=new Set([...ids,...receipts.map(row=>row.production_topic_id),
   ...queue.filter(x=>x.scope==='topic').map(x=>x.target)]);
 const targets=[{scope:'feed',target:'latest'},...[...topics].sort().map(target=>({scope:'topic',target}))];
 if(targets.length>MAX_QUEUE+1)throw Error('Excessive CDN verification targets');
 const deadline=Date.now()+25*60*1000;
 const results=[],versions=new Map();
 for(const {scope,target} of targets){
  if(scope==='topic'&&!IDENT.test(target))throw Error('Untrusted production topic ID');
  const verified=await accept(scope,target,deadline);
  results.push(verified);
  if(scope==='topic')versions.set(target,verified.version);
  console.log('PASS: production CDN R2 version and purge acknowledged',JSON.stringify(verified));
 }
 const after=pending();
 if(after.some(x=>x.scope==='feed'||topics.has(x.target)))
  throw Error('Production CDN invalidation outbox still pending after per-topic verification');
 // The original source receipt always stays immutable; the separate DEV ledger is
 // acknowledged only after actual CDN content and PROD outbox versions agree.
 ackAcceptedReceipts(receipts,versions);
 const left=unacceptedReceipts();
 if(left.some(row=>receipts.some(old=>old.source_topic_id===row.source_topic_id)))
  throw Error('DEV CDN acceptance ledger still has unacknowledged source receipts');
 console.log(JSON.stringify({cdnAccepted:true,topics:topics.size,acknowledged:receipts.length,latestFeedVerified:true,verifiedObjects:results.length}));
}
if(process.argv[1]&&resolve(process.argv[1])===resolve(new URL(import.meta.url).pathname))
  main().catch(e=>{console.error('PRODUCTION CDN ACCEPTANCE FAILED:',e.message);process.exitCode=1;});
