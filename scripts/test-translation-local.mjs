// LOCAL-ONLY API acceptance using a migrated, seeded local Wrangler D1.
// Never accesses remote Cloudflare D1, Azure or real user content.
import assert from 'node:assert/strict';
import {spawn,spawnSync} from 'node:child_process';
import {setTimeout as sleep} from 'node:timers/promises';

const wrangler='node_modules/wrangler/bin/wrangler.js';
function cli(args){
 const out=spawnSync(process.execPath,[wrangler,...args],{encoding:'utf8',timeout:120000});
 if(out.status!==0)throw Error('Local Wrangler setup failed: '+(out.stderr||out.stdout||'').slice(-1800));
}
cli(['d1','migrations','apply','DB','--local','--config','wrangler.local.jsonc']);
cli(['d1','execute','DB','--local','--config','wrangler.local.jsonc','--file','tests/fixtures/translation-local.sql']);
const port=8788;
const origin='http://127.0.0.1:'+port;
const child=spawn(process.execPath,[wrangler,'dev','--local','--config','wrangler.local.jsonc','--ip','127.0.0.1','--port',String(port)],{stdio:['ignore','pipe','pipe']});
let tail='';
for(const stream of [child.stdout,child.stderr])stream.on('data',chunk=>{tail=(tail+String(chunk)).slice(-2000)});
try{
 let ready=false;
 for(let i=0;i<80;i++){
  if(child.exitCode!==null)throw Error('Local Worker exited: '+tail);
  try{
   const r=await fetch(origin+'/api/health',{signal:AbortSignal.timeout(1200)});
   if(r.ok&&(await r.json()).databaseReady===true){ready=true;break;}
  }catch{}
  await sleep(400);
 }
 if(!ready)throw Error('Local Worker health not ready: '+tail);
 const post=async(locale,items,generate=false)=>{
  const r=await fetch(origin+'/api/translate',{method:'POST',headers:{'content-type':'application/json','origin':origin},
   body:JSON.stringify({locale,items,generate}),signal:AbortSignal.timeout(10000)});
  const result=await r.json();
  return {status:r.status,result};
 };
 const topic={id:'local-trans-topic',type:'topic',scope:'full',version:1};
 const summary={...topic,scope:'summary'};
 const comment={id:'local-trans-comment',type:'comment',scope:'full',version:1};
 let batch=await post('zh-CN',[topic,summary,comment],false);
 assert.equal(batch.status,200,JSON.stringify(batch.result));
 assert.equal(batch.result.items.length,3);
 assert.deepEqual(batch.result.items.map(x=>x.translated),[true,true,true]);
 assert.equal(batch.result.items[0].title,'新的开始');
 assert.equal(batch.result.items[0].body,'我正在寻求支持，一步一步向前。');
 assert.equal(batch.result.items[1].title,'新的开始');
 assert.equal(batch.result.items[2].body,'你可以一天一天慢慢来。');
 console.log('PASS: anonymous cached topic full/summary and comment display correct localized text.');
 const repeated=await post('zh-CN',[topic,summary,comment],false);
 assert.deepEqual(repeated.result,batch.result);
 console.log('PASS: repeated translation uses same D1 cached text, no Azure token required.');
 const source=await post('en',[topic,comment],false);
 assert.deepEqual(source.result.items.map(x=>x.reason),['same_language','same_language']);
 console.log('PASS: original language is not overwritten by a translation.');
 const invalid=await post('xx',[topic],false);
 assert.equal(invalid.status,400);
 const wrongVersion=await post('zh-CN',[{...topic,version:2}],false);
 assert.equal(wrongVersion.result.items[0].reason,'content_changed');
 console.log('PASS: invalid locale and content-version mismatch are safely rejected.');
 cli(['d1','execute','DB','--local','--config','wrangler.local.jsonc','--command',
   "UPDATE topics SET body='I am asking for help today, not yesterday.',content_version=content_version+1 WHERE id='local-trans-topic'"]);
 const after=await post('zh-CN',[{...topic,version:2}],false);
 assert.equal(after.result.items[0].reason,'translation_cache_miss');
 console.log('PASS: editing original invalidates cached Azure translation; no stale translated content exposed.');
}finally{
 child.kill('SIGTERM');
 await sleep(250);
 if(child.exitCode===null)child.kill('SIGKILL');
}
