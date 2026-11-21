#!/usr/bin/env node
// ONE-TIME, DEV-ONLY OAuth client bootstrap for Gambling Community.
// Runs only during the named Cloudflare dev Preview build, never in CI/local/production.
// Secret plaintext stays in process memory and the dev Preview Worker Secret; only
// SHA-256 base64url digest is persisted to two separate DEV D1 databases.
import {createHash,randomBytes} from "node:crypto";
import {readFileSync} from "node:fs";
import {spawnSync} from "node:child_process";

if(process.env.WORKERS_CI!=="1"||process.env.WORKERS_CI_BRANCH!=="dev"){
  console.log("Dev identity bootstrap skipped outside named Cloudflare dev Preview build.");
  process.exit(0);
}
const WORKER="gambling-community";
const PREVIEW="dev";
const FORUM_DEV_ID="a92cf620-2a0b-46e1-a0ff-2e0c94218f37";
const FORUM_PROD_ID="7bba9ada-589f-493b-8fcf-60265fc0efac";
const CENTER_DEV_ID="66c36ee9-2cab-4e85-bc02-645819344297";
const CENTER_PROD_ID="5cc8d9c2-6883-452f-94e5-f96fb94917c3";
const CLIENT_ID="gambling-community-dev";
const CALLBACK="https://dev-gambling-community.119shenhao.workers.dev/api/auth/identity/callback";
const SECRET_NAME="IDENTITY_CLIENT_SECRET";
const RECEIPT="gambling_identity_dev_secret_digest";
const VERIFIED="gambling_identity_dev_secret_verified";
const cfg=JSON.parse(readFileSync("wrangler.jsonc","utf8"));
const forumCfg=JSON.parse(readFileSync("wrangler.preview-migrations.jsonc","utf8"));
const centerCfg=JSON.parse(readFileSync("wrangler.identity-dev-provision.jsonc","utf8"));
const forum=forumCfg.d1_databases||[],center=centerCfg.d1_databases||[];
const preview=cfg.previews?.d1_databases||[],production=cfg.d1_databases||[];
if(cfg.name!==WORKER||cfg.keep_vars!==true||
   cfg.vars?.APP_ENV!=="production"||cfg.vars?.IDENTITY_LOGIN_ENABLED!=="false"||
   cfg.previews?.vars?.APP_ENV!=="preview"||cfg.previews?.vars?.IDENTITY_LOGIN_ENABLED!=="false"||
   cfg.previews?.vars?.IDENTITY_CLIENT_ID!==CLIENT_ID||
   cfg.previews?.vars?.IDENTITY_REDIRECT_URI!==CALLBACK||
   cfg.previews?.vars?.IDENTITY_ISSUER!=="https://dev-identity-center.119shenhao.workers.dev"||
   preview.length!==1||preview[0].binding!=="DB"||preview[0].database_id!==FORUM_DEV_ID||
   preview[0].database_name!=="gambling-community-dev"||
   production.length!==1||production[0].database_id!==FORUM_PROD_ID||
   production[0].database_name!=="gambling-community-prod"||
   forum.length!==1||forum[0].binding!=="PREVIEW_DB"||forum[0].database_id!==FORUM_DEV_ID||
   center.length!==1||center[0].binding!=="IDENTITY_DEV_DB"||
   center[0].database_id!==CENTER_DEV_ID||center[0].database_name!=="identity-center-dev"||
   [FORUM_PROD_ID,CENTER_PROD_ID].includes(FORUM_DEV_ID)||
   [FORUM_PROD_ID,CENTER_PROD_ID].includes(CENTER_DEV_ID)){
  throw Error("Refusing OAuth bootstrap: exact dev Preview/Client/D1 identities not matched.");
}
function wrangler(args,input){
  const r=spawnSync(process.execPath,["node_modules/wrangler/bin/wrangler.js",...args],
    {input,encoding:"utf8",stdio:["pipe","pipe","pipe"],timeout:120000,env:process.env});
  if(r.error||r.status!==0){
    const output=(r.stdout||"")+"\n"+(r.stderr||"");
    const reason=/403|permission|forbidden|unauthorized/i.test(output)?"permission_denied":
      /unknown argument|unknown option|unrecognized option/i.test(output)?"cli_option_unsupported":"operation_failed";
    // Never print CLI output; it may accidentally include private material.
    throw Error("Dev-only Wrangler "+args[0]+" failed ("+reason+"). No secret was logged.");
  }
  return r.stdout;
}
function rows(binding,config,sql){
  const raw=wrangler(["d1","execute",binding,"--remote","--config",config,"--json","--command",sql]);
  const data=JSON.parse(raw);
  if(!Array.isArray(data)||data.length!==1||data[0].success===false||!Array.isArray(data[0].results)){
    throw Error("Unexpected dev D1 SQL response; bootstrap stopped.");
  }
  return data[0].results;
}
const forumQuery=sql=>rows("PREVIEW_DB","wrangler.preview-migrations.jsonc",sql);
const centerQuery=sql=>rows("IDENTITY_DEV_DB","wrangler.identity-dev-provision.jsonc",sql);
function readKey(key){
  const r=forumQuery("SELECT value FROM settings WHERE key='"+key+"'");
  if(r.length>1)throw Error("Duplicate dev receipt key.");
  return r[0]?.value||"";
}
const migration=forumQuery("SELECT name FROM d1_migrations WHERE name='0100_identity_center.sql'");
if(migration.length!==1)throw Error("Gambling development D1 is missing identity migration.");
const client=centerQuery("SELECT client_id,client_kind,status FROM oauth_clients WHERE client_id='"+CLIENT_ID+"'");
if(client.length!==1||client[0].client_kind!=="web_confidential"||client[0].status!=="disabled"){
  throw Error("Identity Center development client is missing or not safely disabled.");
}
const redirects=centerQuery("SELECT redirect_uri FROM oauth_redirect_uris WHERE client_id='"+CLIENT_ID+"'");
if(redirects.length!==1||redirects[0].redirect_uri!==CALLBACK)throw Error("Identity Center dev callback mismatch.");
const targetArgs=["--worker-name",WORKER,"--name",PREVIEW];
const hasSecret=()=>{
  const data=JSON.parse(wrangler(["preview","secret","list",...targetArgs,"--json"]));
  if(!Array.isArray(data))throw Error("Preview Secret metadata response malformed.");
  return data.some(x=>x.name===SECRET_NAME&&x.type==="secret_text");
};
const digestPattern=/^[A-Za-z0-9_-]{43}$/;
let digest=readKey(RECEIPT);
const previouslyVerified=readKey(VERIFIED);
if(hasSecret()){
  if(!digestPattern.test(digest))throw Error("Existing Preview OAuth Secret has no verified digest receipt; refuse rotation.");
}else{
  if(digest||previouslyVerified)throw Error("Dev digest receipt exists without Preview Secret; manual review required.");
  const secret=randomBytes(48).toString("base64url");
  digest=createHash("sha256").update(secret).digest("base64url");
  if(!digestPattern.test(digest))throw Error("Invalid generated credential hash.");
  forumQuery("INSERT INTO settings(key,value) VALUES('"+RECEIPT+"','"+digest+
    "') ON CONFLICT(key) DO UPDATE SET value=excluded.value");
  wrangler(["preview","secret","put",SECRET_NAME,...targetArgs,
    "--message","Initialize Gambling Community development OAuth client"],secret+"\n");
  if(!hasSecret())throw Error("Preview secret upload was not confirmed. Keep login disabled.");
  console.log("Dedicated Gambling DEV Preview Worker Secret uploaded and read back.");
}
if(previouslyVerified&&previouslyVerified!==digest)throw Error("Existing verified DEV receipt mismatch.");
const active=centerQuery("SELECT secret_hash FROM oauth_client_secrets WHERE client_id='"+CLIENT_ID+
  "' AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at>unixepoch())");
if(active.some(item=>item.secret_hash!==digest))throw Error("Different active DEV Identity Center secret exists; refuse replacement.");
if(active.length>1)throw Error("Multiple Identity Center active DEV secret hashes; refusing.");
if(active.length===0){
  centerQuery("INSERT INTO oauth_client_secrets(secret_hash,client_id,created_at) VALUES('"+
    digest+"','"+CLIENT_ID+"',unixepoch())");
}
const hashes=centerQuery("SELECT secret_hash FROM oauth_client_secrets WHERE client_id='"+CLIENT_ID+
  "' AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at>unixepoch())");
if(hashes.length!==1||hashes[0].secret_hash!==digest)throw Error("Center DEV hash verification failed.");
forumQuery("INSERT INTO settings(key,value) VALUES('"+VERIFIED+"','"+digest+
  "') ON CONFLICT(key) DO UPDATE SET value=excluded.value");
if(readKey(RECEIPT)!==digest||readKey(VERIFIED)!==digest)throw Error("Forum dev receipt verification failed.");
console.log("PASS: independent DEV Worker Secret and Identity Center DEV hash agree. Client remains DISABLED; production untouched.");
