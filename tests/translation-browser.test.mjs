import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {translationView,unpackTranslation} from '../public/translation-ui.js';

test('cached encrypted projection is decrypted only with matching AES-GCM key',async()=>{
 const crypto=globalThis.crypto||webcrypto;
 const key=crypto.getRandomValues(new Uint8Array(32));
 const iv=crypto.getRandomValues(new Uint8Array(12));
 const payload={title:'新开始',body:'今天我迈出了第一步。'};
 const aes=await crypto.subtle.importKey('raw',key,'AES-GCM',false,['encrypt']);
 const ciphertext=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},aes,
   new TextEncoder().encode(JSON.stringify(payload))));
 const combined=new Uint8Array(iv.length+ciphertext.length);combined.set(iv);combined.set(ciphertext,iv.length);
 const base64url=v=>Buffer.from(v).toString('base64url');
 const result=await unpackTranslation({translated:true,key:base64url(key)},{ciphertext:base64url(combined)});
 assert.deepEqual(result,payload);
 await assert.rejects(unpackTranslation({translated:true,key:base64url(crypto.getRandomValues(new Uint8Array(32)))},
   {ciphertext:base64url(combined)}));
});

test('viewer loads translated visible topics, toggles original, skips source language',async()=>{
 let observer,requests=0,renders=[];
 const oldIO=globalThis.IntersectionObserver,oldWidth=globalThis.innerWidth,oldHeight=globalThis.innerHeight;
 globalThis.innerWidth=1600;globalThis.innerHeight=1000;
 globalThis.IntersectionObserver=class {
  constructor(cb){this.cb=cb;observer=this;}
  observe(target){this.cb([{target,isIntersecting:true}]);}
  disconnect(){}
 };
 try{
  const view=translationView('zh-CN',{
   configured:true,hasCache:false,direct:false,
   request:async({locale,items,generate})=>{
    requests++;assert.equal(locale,'zh-CN');assert.equal(generate,true);
    return {items:items.map(x=>({translated:true,title:'翻译后的标题',body:'翻译后的正文',provider:'azure'}))};
   },
   render:(node,state)=>renders.push({original:state.original,body:state.result.body}),
   onStale:()=>{throw Error('unexpected stale state')}
  });
  const source={id:'cn',body:'中文原文',source_lang:'zh-CN',source_lang_mode:'manual',content_version:1,status:'published'};
  assert.equal(view.item('topic',source,'full'),null,'same language must not request translation');
  const english={id:'en',body:'The original English text',source_lang:'en',source_lang_mode:'manual',content_version:1,status:'published'};
  const state=view.item('topic',english,'full');
  assert.ok(state);
  const parent={getBoundingClientRect:()=>({top:10,bottom:100,left:0,right:500})};
  const node={dataset:{translation:state.key},parentElement:parent,isConnected:true};
  view.observe([node]);
  for(let i=0;i<40&&renders.length<1;i++)await new Promise(r=>setTimeout(r,20));
  assert.equal(requests,1);
  assert.equal(renders[0].original,false);
  assert.equal(renders[0].body,'翻译后的正文');
  view.toggle(node);
  assert.equal(renders.at(-1).original,true);
  view.toggle(node);
  assert.equal(renders.at(-1).original,false);
  view.close();
  console.log('PASS: visible translation overlay and original/translation toggle.');
 }finally{
  globalThis.IntersectionObserver=oldIO;globalThis.innerWidth=oldWidth;globalThis.innerHeight=oldHeight;
 }
});
