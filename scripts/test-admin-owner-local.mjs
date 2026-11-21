// LOCAL ONLY: no remote Cloudflare D1, real Google accounts or secrets.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawnSync,spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
const wrangler='node_modules/wrangler/bin/wrangler.js';
const ownerCenterId='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const memberCenterId='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const ownerId='local-owner-user',memberId='local-member-user';
const tokenOwner='local-owner-test-token',tokenMember='local-member-test-token';
const sha=s=>createHash('sha256').update(s).digest('hex');
const exec=args=>{
 const r=spawnSync(process.execPath,[wrangler,...args],{encoding:'utf8',timeout:120000});
 if(r.status!==0)throw Error('LOCAL D1 command failed: '+(r.stderr||r.stdout||'').slice(-1600));
 return r.stdout;
};
const localDb=['d1','execute','DB','--local','--config','wrangler.local.jsonc'];
exec(['d1','migrations','apply','DB','--local','--config','wrangler.local.jsonc']);
const sql=[
 `INSERT OR IGNORE INTO users(id,nickname) VALUES('${ownerId}','Local Owner Test')`,
 `INSERT OR IGNORE INTO users(id,nickname) VALUES('${memberId}','Local Member Test')`,
 `INSERT OR IGNORE INTO auth_identities(id,user_id,provider,provider_subject) VALUES('owner-identity-1','${ownerId}','identity_center','${ownerCenterId}')`,
 `INSERT OR IGNORE INTO auth_identities(id,user_id,provider,provider_subject) VALUES('member-identity-1','${memberId}','identity_center','${memberCenterId}')`,
 `INSERT OR IGNORE INTO user_sessions(id,user_id,token_hash,expires_at) VALUES('owner-session-1','${ownerId}','${sha(tokenOwner)}',unixepoch()+86400)`,
 `INSERT OR IGNORE INTO user_sessions(id,user_id,token_hash,expires_at) VALUES('member-session-1','${memberId}','${sha(tokenMember)}',unixepoch()+86400)`
];
for(const query of sql)exec([...localDb,'--command',query]);
const port=8791,origin='http://127.0.0.1:'+port;
const child=spawn(process.execPath,[wrangler,'dev','--local','--config','wrangler.local.jsonc','--ip','127.0.0.1','--port',String(port),
 '--var','APP_ENV:preview','--var','IDENTITY_LOGIN_ENABLED:true',
 '--var','IDENTITY_CLIENT_ID:gambling-community-dev',
 '--var','IDENTITY_ISSUER:https://dev-identity-center.119shenhao.workers.dev',
 '--var','ADMIN_CENTER_OWNER_SHA256:'+sha(ownerCenterId)],
 {stdio:['ignore','pipe','pipe']});
let output='';
for(const stream of [child.stdout,child.stderr])stream.on('data',part=>{output=(output+String(part)).slice(-2400)});
const load=async(path,token)=>{
 const r=await fetch(origin+path,{headers:{cookie:'gc_session='+token},signal:AbortSignal.timeout(8000)});
 return {status:r.status,body:await r.json()};
};
try{
 let alive=false;
 for(let i=0;i<90;i++){
  if(child.exitCode!==null)throw Error('Worker stopped: '+output);
  try{const r=await fetch(origin+'/api/health',{signal:AbortSignal.timeout(1200)});if(r.ok){alive=true;break}}catch{}
  await delay(350);
 }
 if(!alive)throw Error('Local Worker did not start: '+output);
 const anonymous=await load('/api/me','not-a-session');
 assert.equal(anonymous.status,200);assert.equal(anonymous.body.user,null);
 const member=await load('/api/me',tokenMember);
 assert.equal(member.status,200);assert.equal(member.body.user.role,'member');
 const memberDenied=await load('/api/admin/overview',tokenMember);
 assert.equal(memberDenied.status,403,'regular member must not access admin');
 const owner=await load('/api/me',tokenOwner);
 assert.equal(owner.status,200);assert.equal(owner.body.user.role,'admin');
 const ownerAdmin=await load('/api/admin/overview',tokenOwner);
 assert.equal(ownerAdmin.status,200,'verified center owner should access admin');
 const twice=await load('/api/me',tokenOwner);
 assert.equal(twice.body.user.role,'admin');
 const audit=exec([...localDb,'--command',"SELECT COUNT(*) AS n FROM moderation_actions WHERE action='grant_admin' AND reason='identity_center_verified_owner'"]);
 assert.match(audit,/"n":\s*1\b/,'owner role must be granted and audited exactly once');
 const identities=exec([...localDb,'--command',"SELECT count(*) AS n FROM user_roles WHERE role='admin'"]);
 assert.match(identities,/"n":\s*1\b/,'never grant admin to ordinary account');
 console.log('PASS: existing Center-linked OWNER session obtains admin without new login.');
 console.log('PASS: wrong Google/Center account remains member and cannot access admin.');
 console.log('PASS: role grant is idempotent and audited once; no production database touched.');
}finally{
 child.kill('SIGTERM');await delay(250);
 if(child.exitCode===null)child.kill('SIGKILL');
}
