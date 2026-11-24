import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';

// These tests bundle the actual production TypeScript module. They intentionally
// use in-memory R2 and a mocked Cloudflare purge endpoint, never real D1/R2.
const built=await build({
  entryPoints:['src/public-projection.ts'],bundle:true,platform:'node',
  format:'esm',write:false,logLevel:'silent'
});
const moduleUrl='data:text/javascript;base64,'+Buffer.from(built.outputFiles[0].contents).toString('base64');
const {writeProjection,purgeProjection}=await import(moduleUrl);
const base='https://gambling-data-dev.nbn369.com';
const origin='https://dev-gambling-community.119shenhao.workers.dev';

function bucket(){
  const entries=new Map();
  let writes=0;
  return {
    entries,
    get writeCount(){return writes;},
    async head(key){return entries.get(key)||null;},
    async put(key,body,opts){
      const old=entries.get(key);
      if(opts.onlyIf?.etagMatches!==undefined&&old?.etag!==opts.onlyIf.etagMatches)return null;
      if(opts.onlyIf?.etagDoesNotMatch==='*'&&old)return null;
      const etag='etag-'+(++writes);
      entries.set(key,{etag,body:JSON.parse(body),httpMetadata:opts.httpMetadata,customMetadata:opts.customMetadata});
      return {etag};
    }
  };
}
function config(b){
  return {base,origin,bucket:b,separateTranslations:true,directTranslations:true};
}
function oneTopic(version,withTranslation=false){
  const topic={id:'test-topic',status:'published',content_version:version,title:'Test',
    body:'Public text',source_lang:'en',reply_count:0};
  if(withTranslation)topic.translations={'zh-CN':{sourceVersion:version,title:'测试',body:'公开文字'}};
  return {topic,comments:[],progress:[]};
}
test('feed JSON uses one day and does not re-write unchanged same-version R2 objects',async()=>{
  const b=bucket(),c=config(b);
  const data={topics:[{id:'test-topic',status:'published',content_version:1,title:'Test'}]};
  const key='feeds/latest/page-1.json';
  await writeProjection(c,key,'feed','latest',1,data,false,1);
  const obj=b.entries.get(key);
  assert.ok(obj);
  assert.equal(obj.httpMetadata.cacheControl,'public, max-age=0, s-maxage=86400, must-revalidate');
  assert.equal(obj.customMetadata.cachePolicy,'edge-86400');
  assert.equal(obj.body.data.translationLayout,'separate-v1');
  assert.equal(b.writeCount,1);
  await writeProjection(c,key,'feed','latest',1,data,false,1);
  assert.equal(b.writeCount,1);
});
test('topic original is 7 days; independently versioned translations are 30 days',async()=>{
  const b=bucket(),c=config(b);
  const key='topics/test-topic/detail.json';
  const locales=await writeProjection(c,key,'topic','test-topic',1,oneTopic(1,true),false,1);
  assert.deepEqual(locales,['i18n/zh-CN/'+key]);
  const original=b.entries.get(key),translated=b.entries.get(locales[0]);
  assert.equal(original.httpMetadata.cacheControl,'public, max-age=0, s-maxage=604800, must-revalidate');
  assert.equal(original.customMetadata.cachePolicy,'edge-604800');
  assert.equal(translated.httpMetadata.cacheControl,'public, max-age=0, s-maxage=2592000, must-revalidate');
  assert.equal(translated.customMetadata.cachePolicy,'edge-2592000');
  assert.equal(original.body.data.translationLayout,'separate-v1');
  assert.deepEqual(original.body.data.translationLocales,['zh-CN']);
  assert.equal(translated.body.locale,'zh-CN');
  assert.equal(translated.body.contentVersion,1);
  assert.equal(translated.body.translationLayout,'separate-v1');
  const count=b.writeCount;
  await writeProjection(c,key,'topic','test-topic',1,oneTopic(1,true),false,1);
  assert.equal(b.writeCount,count);
});
test('editing content invalidates all prior translated copies and avoids caching tombstones',async()=>{
  const b=bucket(),c=config(b),key='topics/test-topic/detail.json';
  await writeProjection(c,key,'topic','test-topic',1,oneTopic(1,true),false,1);
  await writeProjection(c,key,'topic','test-topic',2,oneTopic(2,false),false,2);
  const oldLocale=b.entries.get('i18n/zh-CN/'+key);
  const updated=b.entries.get(key);
  assert.equal(oldLocale.body.invalidated,true);
  assert.equal(oldLocale.httpMetadata.cacheControl,'no-store');
  assert.equal(oldLocale.customMetadata.cachePolicy,'edge-no-store');
  assert.equal(updated.body.contentVersion,2);
  assert.deepEqual(updated.body.data.translationLocales,[]);
  assert.equal(updated.httpMetadata.cacheControl,'public, max-age=0, s-maxage=604800, must-revalidate');
});
test('removal or hiding writes an uncached original tombstone and locale tombstones',async()=>{
  const b=bucket(),c=config(b),key='topics/test-topic/detail.json';
  await writeProjection(c,key,'topic','test-topic',1,oneTopic(1,true),false,1);
  const touched=await writeProjection(c,key,'topic','test-topic',2,{},true,2);
  const original=b.entries.get(key);
  assert.equal(original.body.invalidated,true);
  assert.equal(original.httpMetadata.cacheControl,'no-store');
  assert.equal(original.customMetadata.cachePolicy,'edge-no-store');
  assert.deepEqual(touched,['i18n/zh-CN/'+key]);
  assert.equal(b.entries.get(touched[0]).httpMetadata.cacheControl,'no-store');
});
test('same-version source and translation are republished when cache-policy metadata changes',async()=>{
  const b=bucket(),c=config(b),key='topics/test-topic/detail.json';
  const data=oneTopic(1,true);
  await writeProjection(c,key,'topic','test-topic',1,data,false,1);
  // Emulate a previously published 60-second object and translation. Preserve hashes.
  for(const row of b.entries.values()){
    row.customMetadata.cachePolicy='edge-60';
    row.httpMetadata.cacheControl='public, max-age=0, s-maxage=60, must-revalidate';
  }
  const before=b.writeCount;
  await writeProjection(c,key,'topic','test-topic',1,data,false,1);
  assert.equal(b.writeCount,before+2);
  assert.equal(b.entries.get(key).customMetadata.cachePolicy,'edge-604800');
  assert.equal(b.entries.get('i18n/zh-CN/'+key).customMetadata.cachePolicy,'edge-2592000');
});
test('Cloudflare purge uses exact URL plus Origin variant and locale keys',async()=>{
  const originalFetch=globalThis.fetch;
  const calls=[];
  globalThis.fetch=async(url,opts)=>{
    calls.push({url,opts});
    return new Response(JSON.stringify({success:true}),{status:200});
  };
  try{
    const env={CDN_ZONE_ID:'a'.repeat(32),CDN_PURGE_API_TOKEN:'in-memory-test-token'};
    const key='topics/test-topic/detail.json';
    await purgeProjection(env,config(bucket()),key,false,['i18n/zh-CN/'+key]);
    assert.equal(calls.length,1);
    assert.equal(calls[0].url,'https://api.cloudflare.com/client/v4/zones/'+env.CDN_ZONE_ID+'/purge_cache');
    assert.equal(calls[0].opts.headers.authorization,'Bearer in-memory-test-token');
    const files=JSON.parse(calls[0].opts.body).files;
    assert.deepEqual(files,[
      base+'/'+key,{url:base+'/'+key,headers:{Origin:origin}},
      base+'/i18n/zh-CN/'+key,{url:base+'/i18n/zh-CN/'+key,headers:{Origin:origin}}
    ]);
  }finally{globalThis.fetch=originalFetch;}
});
test('privacy priority uses prefix purge and failed purge is never treated as success',async()=>{
  const originalFetch=globalThis.fetch;
  const calls=[];
  const env={CDN_ZONE_ID:'b'.repeat(32),CDN_PURGE_API_TOKEN:'in-memory-test-token'};
  const key='topics/test-topic/detail.json';
  try{
    globalThis.fetch=async(_url,opts)=>{
      calls.push(JSON.parse(opts.body));
      return new Response(JSON.stringify({success:true}),{status:200});
    };
    await purgeProjection(env,config(bucket()),key,true,['i18n/zh-CN/'+key]);
    assert.deepEqual(calls[0].prefixes,[
      'gambling-data-dev.nbn369.com/topics/test-topic/detail.json',
      'gambling-data-dev.nbn369.com/i18n/zh-CN/topics/test-topic/detail.json'
    ]);
    globalThis.fetch=async()=>new Response(JSON.stringify({success:false}),{status:429});
    await assert.rejects(purgeProjection(env,config(bucket()),key),/purge_http_429/);
    globalThis.fetch=async()=>new Response(JSON.stringify({success:false}),{status:200});
    await assert.rejects(purgeProjection(env,config(bucket()),key),/purge_rejected/);
    globalThis.fetch=async()=>{throw new Error('temporary network outage');};
    await assert.rejects(purgeProjection(env,config(bucket()),key),/purge_unavailable/);
  }finally{globalThis.fetch=originalFetch;}
});
