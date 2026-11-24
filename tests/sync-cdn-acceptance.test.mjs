import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {parseWranglerResults,assertProdConfig,assertReadiness,verifyEnvelope,parseManifest} from '../scripts/sync-production-cdn-acceptance.mjs';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
const database='7bba9ada-589f-493b-8fcf-60265fc0efac';
const account='289976272520a38732bef34108585e11';
const prodConfig=JSON.parse(read('wrangler.production-sync.jsonc'));
const env={CLOUDFLARE_ACCOUNT_ID:account,CLOUDFLARE_API_TOKEN:'mock-not-a-real-token',
  GAMBLING_SYNC_PRODUCTION_CONFIRM:database};
const health={environment:'production',databaseReady:true,
  publicContent:{ready:true,enabled:true,purgeConfigured:true,onDemand:true,fallback:true,baseUrl:'https://gambling-data.nbn369.com'}};
const topicRecord={version:5,published_version:5,content_version:1,reply_count:2,comment_count:2};
const topic={schemaVersion:1,contentVersion:5,topicId:'fake-topic',data:{translationLayout:'separate-v1',
  topic:{id:'fake-topic',content_version:1,reply_count:2},comments:[{id:'c1'},{id:'c2'}],progress:[]}};
test('production sync uses only the reviewed D1 binding, never arbitrary credentials',()=>{
 assert.doesNotThrow(()=>assertProdConfig(prodConfig,env));
 assert.throws(()=>assertProdConfig(prodConfig,{...env,CLOUDFLARE_API_TOKEN:''}),/credentials/);
 assert.throws(()=>assertProdConfig(prodConfig,{...env,GAMBLING_SYNC_PRODUCTION_CONFIRM:'different'}),/credentials/);
 assert.throws(()=>assertProdConfig({d1_databases:[{binding:'PRODUCTION_DB',database_id:'other'}]},env),/binding/);
});
test('no production CDN means fail before any content sync write',()=>{
 assertReadiness(health);
 for(const change of [
  {publicContent:{...health.publicContent,enabled:false}},
  {publicContent:{...health.publicContent,purgeConfigured:false}},
  {publicContent:{...health.publicContent,baseUrl:'https://gambling-data-dev.nbn369.com'}},
  {environment:'preview'},
  {publicContent:{...health.publicContent,onDemand:false}},
 ]){
  assert.throws(()=>assertReadiness({...health,...change}),/STOP BEFORE D1 WRITES/);
 }
});
test('production D1 query failures never yield an empty queue false success',()=>{
 assert.deepEqual(parseWranglerResults(JSON.stringify([{success:true,results:[{id:'a'}]}])),[{id:'a'}]);
 assert.throws(()=>parseWranglerResults(JSON.stringify([{success:false,results:[]}])),/Unsuccessful/);
 assert.throws(()=>parseWranglerResults(JSON.stringify([{success:true}])),/Unsuccessful/);
 assert.throws(()=>parseWranglerResults(JSON.stringify({success:true,results:[]})),/Unsuccessful/);
});
test('CDN acceptance requires exact current content version, reply count and long edge TTL',()=>{
 verifyEnvelope('topic','fake-topic',topicRecord,topic,'public, max-age=0, s-maxage=604800, must-revalidate');
 assert.throws(()=>verifyEnvelope('topic','fake-topic',{...topicRecord,version:6},topic,
   'public, max-age=0, s-maxage=604800, must-revalidate'),/version/);
 assert.throws(()=>verifyEnvelope('topic','fake-topic',topicRecord,{...topic,invalidated:true},
   'public, max-age=0, s-maxage=604800, must-revalidate'),/version/);
 assert.throws(()=>verifyEnvelope('topic','fake-topic',topicRecord,{...topic,data:{...topic.data,comments:[]}},
   'public, max-age=0, s-maxage=604800, must-revalidate'),/replies/);
 assert.throws(()=>verifyEnvelope('topic','fake-topic',topicRecord,topic,
   'public, max-age=0, s-maxage=60, must-revalidate'),/TTL/);
 assert.throws(()=>verifyEnvelope('topic','fake-topic',topicRecord,{...topic,topicId:'another'},
   'public, max-age=0, s-maxage=604800, must-revalidate'),/replies/);
});
test('latest feed verifies exact outbox version and one-day TTL',()=>{
 const data={schemaVersion:1,contentVersion:8,data:{translationLayout:'separate-v1',topics:[]}};
 verifyEnvelope('feed','latest',{version:8},data,'public, max-age=0, s-maxage=86400, must-revalidate');
 assert.throws(()=>verifyEnvelope('feed','latest',{version:9},data,
   'public, max-age=0, s-maxage=86400, must-revalidate'),/version/);
});
test('only valid and deduplicated source-receipted topic identifiers enter CDN acceptance manifest',()=>{
 const input='{"id":"fake-topic","comments":2}\n{"id":"fake-topic","comments":2}\n{"id":"another-topic","comments":0}\n';
 assert.deepEqual(parseManifest(input),['fake-topic','another-topic']);
 assert.throws(()=>parseManifest('{"id":"../admin"}'),/Untrusted/);
 assert.throws(()=>parseManifest('{"id":"abc","url":"https://untrusted.invalid"}'),/Untrusted/);
});
test('sync contract: manifest after source receipt, post-sync R2 wake, Cloudflare purge and fail-closed',()=>{
 const sync=read('scripts/sync-preview-to-production.mjs');
 const wake=read('src/projection-demand.ts');
 const worker=read('src/index.ts');
 const cdn=read('scripts/sync-production-cdn-acceptance.mjs');
 assert.match(sync,/markPreview\(topic,topic\.id,hash,comments\.length\);counts\.marked\+\+;[\s\S]*GAMBLING_SYNC_CDN_MANIFEST_PATH/);
 assert.match(wake,/current\?\.state==='done'&&current\.version===current\.published_version/);
 assert.match(wake,/Number\(existing\.customMetadata\?\.projectionVersion\)===current\.version/);
 assert.match(worker,/ctx\.waitUntil\(requestProjection\(env,req,path\)/);
 assert.match(cdn,/x-gambling-projection-miss/);
 assert.match(cdn,/if\(row\.state==='dead'\)throw/);
 assert.match(cdn,/if\(row\.state==='done'&&row\.published_version===row\.version&&r\.status===200\)/);
 assert.match(cdn,/const after=pending\(\)/);
 assert.doesNotMatch(cdn,/\/purge_cache|env\.DB\.prepare/);
});

test('DEV receipt trigger persists unverified CDN obligations across reruns',()=>{
 const migration=read('migrations/preview-only/0003_sync_cdn_acceptance.sql');
 const py=[
  "import sqlite3,sys",
  "db=sqlite3.connect(':memory:')",
  "db.execute('PRAGMA foreign_keys=ON')",
  "db.executescript('CREATE TABLE topics(id TEXT PRIMARY KEY); CREATE TABLE topic_sync_receipts(source_topic_id TEXT PRIMARY KEY REFERENCES topics(id),production_topic_id TEXT NOT NULL); INSERT INTO topics(id) VALUES(\\'old\\'),(\\'new\\'); INSERT INTO topic_sync_receipts VALUES(\\'old\\',\\'existing-prod\\');')",
  "sql=sys.stdin.read()",
  "db.executescript(sql)",
  "assert db.execute('SELECT source_topic_id,production_topic_id,verified_at FROM topic_cdn_sync_acceptance').fetchall()==[('old','existing-prod',None)]",
  "db.execute(\"INSERT INTO topic_sync_receipts VALUES('new','new-prod')\")",
  "assert db.execute('SELECT count(*) FROM topic_cdn_sync_acceptance WHERE verified_at IS NULL').fetchone()[0]==2",
  "db.execute(\"UPDATE topic_cdn_sync_acceptance SET verified_at=unixepoch(),verified_version=9 WHERE source_topic_id='old'\")",
  "db.executescript(sql)",
  "rows=db.execute('SELECT source_topic_id,production_topic_id,verified_version,verified_at IS NOT NULL FROM topic_cdn_sync_acceptance ORDER BY source_topic_id').fetchall()",
  "assert rows==[('new','new-prod',None,0),('old','existing-prod',9,1)],rows",
  "print('PASS 2 durable acceptance records; no duplicate and no lost checkpoint')"
 ].join('\n');
 const result=spawnSync('python3',['-c',py],{input:migration,encoding:'utf8'});
 assert.equal(result.status,0,result.stderr||result.stdout);
 const preview=read('scripts/preview-migrate.mjs');
 assert.match(preview,/0003_sync_cdn_acceptance\.sql/);
 assert.match(preview,/topic_cdn_sync_receipt_insert/);
});
test('CDN checkpoints cannot mutate original sync receipt or disappear across Actions runs',()=>{
 const s=read('scripts/sync-production-cdn-acceptance.mjs');
 assert.match(s,/function unacceptedReceipts\(\)/);
 assert.match(s,/WHERE verified_at IS NULL ORDER BY/);
 assert.match(s,/ackAcceptedReceipts\(receipts,versions\)/);
 assert.match(s,/verified_at=unixepoch\(\),verified_version=CASE source_topic_id/);
 assert.match(s,/const left=unacceptedReceipts\(\)/);
 assert.match(s,/if\(left\.some/);
 assert.doesNotMatch(s,/UPDATE topic_sync_receipts|DELETE FROM topic_sync_receipts/);
});
