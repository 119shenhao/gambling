/* DEV-only staged long-thread import. No content is published before finish.
   The existing collect claim/lease still owns all chunks. */
import {Env,Row,body,fail,hash,id,json,now,one,all,stmt,risk,textField,topicFingerprint} from './core';
import {UNKNOWN_USER_ID} from './import';
import {importedSourceLanguage} from './source-language';

const MAX_REPLIES=500;
function obj(v:any,keys:string[]):Row {
 if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).some(k=>!keys.includes(k)))fail(400,'invalid_long_payload');
 return v as Row;
}
function siteId(v:unknown,kind:string):string {
 if(typeof v!=='string'||!new RegExp(kind==='site'?'^[a-z0-9][a-z0-9_-]{1,31}$':'^[A-Za-z0-9_-]{1,128}$').test(v))fail(400,'invalid_long_id');
 return v;
}
function positive(v:unknown,min:number,max:number):number {
 if(typeof v!=='number'||!Number.isInteger(v)||v<min||v>max)fail(400,'invalid_long_count');
 return v;
}
function tokenValue(v:unknown):string {
 if(typeof v!=='string'||v.length<32||v.length>128)fail(400,'invalid_long_token');
 return v;
}
async function lease(db:D1Database,site:string,sourceId:string,tokenHash:string){
 const r=await one(db,'SELECT state,lease_token_hash,lease_expires_at,topic_id,completion_token_hash FROM collect_sources WHERE site=? AND source_id=?',site,sourceId);
 if(!r||r.state!=='claimed'||r.lease_token_hash!==tokenHash||r.lease_expires_at<=now())fail(409,'claim_not_owned_or_expired');
 return r;
}
const guard=(db:D1Database,site:string,sourceId:string,tokenHash:string)=>
 stmt(db,'INSERT INTO collect_finalize_guard(site,source_id,lease_token_hash) VALUES(?,?,?)',site,sourceId,tokenHash);
const unguard=(db:D1Database,site:string,sourceId:string)=>
 stmt(db,'DELETE FROM collect_finalize_guard WHERE site=? AND source_id=?',site,sourceId);

export async function collectLongRoute(req:Request,env:Env,path:string):Promise<Response>{
 if(req.method!=='POST')fail(405,'method_not_allowed');
 const action=path.substring('/api/collect/long/'.length);
 if(!['start','append','finish','abort'].includes(action))fail(404,'not_found');
 const input=await body(req);
 const common=['site','source_id','lease_token'];
 const allowed=action==='start'?[...common,'title','body','source_lang','source_total','target_count']:
  action==='append'?[...common,'offset','comments']:common;
 const v=obj(input,allowed);
 const site=siteId(v.site,'site'),sourceId=siteId(v.source_id,'source');
 const token=tokenValue(v.lease_token),tokenHash=await hash(token);
 const db=env.IMPORT_DB!;
 // The legacy collectRoute calls its preview-only host/origin gate before us.
 const existing=await one(db,'SELECT * FROM collector_long_stages WHERE site=? AND source_id=?',site,sourceId);
 if(action==='finish'&&existing?.status==='completed'){
  const receipt=await one(db,'SELECT state,completion_token_hash,topic_id FROM collect_sources WHERE site=? AND source_id=?',site,sourceId);
  if(receipt?.state==='completed'&&receipt.completion_token_hash===tokenHash)
   return json({status:'completed',already_completed:true,topic_id:receipt.topic_id,
    imported:{topics:0,comments:0},stored_comments:existing.target_count,
    source_total:existing.source_total,capped:Boolean(existing.capped)});
 }
 await lease(db,site,sourceId,tokenHash);
 const account=await one(db,'SELECT id FROM users WHERE id=? AND is_system=1 AND status=?',UNKNOWN_USER_ID,'active');
 if(!account)fail(503,'import_account_unavailable');
 if(action==='start'){
  const title=textField(v.title,1,200,'title'),content=textField(v.body,1,30000);
  const sourceTotal=positive(v.source_total,1,1000000);
  const target=positive(v.target_count,1,MAX_REPLIES);
  if(target!==Math.min(MAX_REPLIES,sourceTotal))fail(400,'target_must_be_first_500');
  const language=importedSourceLanguage(v.source_lang,title,content);
  const fp=await topicFingerprint(title,content);
  if(existing&&existing.status==='staging'&&existing.lease_hash===tokenHash){
   if(existing.content_hash!==fp||existing.target_count!==target)fail(409,'long_session_payload_changed');
   return json({status:'staging',topic_id:existing.topic_id,received:existing.received,
    target_count:target,source_total:sourceTotal,capped:sourceTotal>MAX_REPLIES});
  }
  const duplicate=await one(db,'SELECT id FROM topics WHERE content_hash=? OR (title=? AND body=?) LIMIT 1',fp,title,content);
  if(duplicate){
   // Duplicates retain their original complete source identity, and are never appended.
   await db.batch([
    guard(db,site,sourceId,tokenHash),
    stmt(db,'UPDATE collect_sources SET state=?,lease_token_hash=NULL,lease_expires_at=NULL,completion_token_hash=?,topic_id=?,content_hash=?,completed_duplicate=1,completed_at=?,updated_at=? WHERE site=? AND source_id=? AND state=? AND lease_token_hash=?',
     'completed',tokenHash,duplicate.id,fp,now(),now(),site,sourceId,'claimed',tokenHash),
    unguard(db,site,sourceId)
   ]);
   return json({status:'completed',duplicate:true,topic_id:duplicate.id,imported:{topics:0,comments:0}});
  }
  const topicId=id();
  const writes:D1PreparedStatement[]=[guard(db,site,sourceId,tokenHash)];
  if(existing){
   if(existing.status!=='staging')fail(409,'long_stage_already_complete');
   writes.push(stmt(db,'DELETE FROM collector_long_replies WHERE site=? AND source_id=?',site,sourceId));
   writes.push(stmt(db,'DELETE FROM collector_long_stages WHERE site=? AND source_id=?',site,sourceId));
  }
  writes.push(stmt(db,'INSERT INTO collector_long_stages(site,source_id,topic_id,lease_hash,title,body,source_lang,source_lang_mode,topic_status,content_hash,source_total,target_count,capped) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
   site,sourceId,topicId,tokenHash,title,content,language.label,language.mode,risk(title,content),fp,sourceTotal,target,sourceTotal>MAX_REPLIES?1:0));
  writes.push(unguard(db,site,sourceId));
  await db.batch(writes);
  return json({status:'staging',topic_id:topicId,received:0,target_count:target,
   source_total:sourceTotal,capped:sourceTotal>MAX_REPLIES},201);
 }
 if(!existing||existing.status!=='staging'||existing.lease_hash!==tokenHash)fail(409,'long_stage_not_owned');
 if(action==='abort'){
  await db.batch([
   guard(db,site,sourceId,tokenHash),
   stmt(db,'DELETE FROM collector_long_replies WHERE site=? AND source_id=?',site,sourceId),
   stmt(db,'DELETE FROM collector_long_stages WHERE site=? AND source_id=?',site,sourceId),
   stmt(db,'UPDATE collect_sources SET state=?,collector_id=NULL,lease_token_hash=NULL,lease_expires_at=NULL,updated_at=? WHERE site=? AND source_id=? AND state=? AND lease_token_hash=?',
    'released',now(),site,sourceId,'claimed',tokenHash),
   unguard(db,site,sourceId)
  ]);
  return json({status:'aborted'});
 }
 if(action==='append'){
  const offset=positive(v.offset,0,MAX_REPLIES);
  if(!Array.isArray(v.comments)||v.comments.length<1||v.comments.length>20)fail(400,'long_batch_size_invalid');
  if(offset+v.comments.length>existing.target_count)fail(400,'long_batch_exceeds_cap');
  if(offset<existing.received){
   if(offset+v.comments.length>existing.received)fail(409,'long_partial_replay');
   const saved=await all(db,'SELECT ordinal,body,parent_ordinal FROM collector_long_replies WHERE site=? AND source_id=? AND ordinal>=? AND ordinal<? ORDER BY ordinal',site,sourceId,offset,offset+v.comments.length);
   if(saved.length!==v.comments.length||saved.some((s:Row,i:number)=>s.body!==v.comments[i]?.body||s.parent_ordinal!==(v.comments[i]?.parent_index??null)))fail(409,'long_replay_changed');
   return json({status:'staging',received:existing.received,replayed:true});
  }
  if(offset!==existing.received)fail(409,'long_batch_out_of_order');
  const writes:D1PreparedStatement[]=[guard(db,site,sourceId,tokenHash)];
  for(let i=0;i<v.comments.length;i++){
   const row=obj(v.comments[i],['body','source_lang','parent_index']);
   const message=textField(row.body,1,12000);
   const ordinal=offset+i, parent=row.parent_index??null;
   if(parent!==null)positive(parent,0,ordinal-1);
   const language=importedSourceLanguage(row.source_lang,message);
   writes.push(stmt(db,'INSERT INTO collector_long_replies(site,source_id,ordinal,id,parent_ordinal,body,source_lang,source_lang_mode,reply_status) VALUES(?,?,?,?,?,?,?,?,?)',
    site,sourceId,ordinal,id(),parent,message,language.label,language.mode,risk('',message)));
  }
  writes.push(stmt(db,'UPDATE collector_long_stages SET received=received+? WHERE site=? AND source_id=? AND received=? AND status=? AND lease_hash=?',
   v.comments.length,site,sourceId,offset,'staging',tokenHash));
  writes.push(unguard(db,site,sourceId));
  await db.batch(writes);
  return json({status:'staging',received:offset+v.comments.length,target_count:existing.target_count});
 }
 if(existing.received!==existing.target_count)fail(409,'long_incomplete_batch');
 const stat=await one(db,'SELECT COUNT(*) count, MIN(ordinal) first,MAX(ordinal) last FROM collector_long_replies WHERE site=? AND source_id=?',site,sourceId);
 if(!stat||stat.count!==existing.target_count||stat.first!==0||stat.last!==existing.target_count-1)fail(409,'long_stage_gap');
 // Each insert into public tables below is a single atomic D1 batch, including
 // its source completion receipt; an error rolls everything back.
 await db.batch([
  guard(db,site,sourceId,tokenHash),
  stmt(db,'INSERT INTO topics(id,author_id,title,body,source_lang,source_lang_mode,status,content_hash) VALUES(?,?,?,?,?,?,?,?)',
   existing.topic_id,UNKNOWN_USER_ID,existing.title,existing.body,existing.source_lang,existing.source_lang_mode,existing.topic_status,existing.content_hash),
  stmt(db,'INSERT INTO comments(id,topic_id,author_id,parent_comment_id,kind,body,source_lang,source_lang_mode,status) SELECT c.id,?, ?,p.id,?,c.body,c.source_lang,c.source_lang_mode,c.reply_status FROM collector_long_replies c LEFT JOIN collector_long_replies p ON p.site=c.site AND p.source_id=c.source_id AND p.ordinal=c.parent_ordinal WHERE c.site=? AND c.source_id=? ORDER BY c.ordinal',
   existing.topic_id,UNKNOWN_USER_ID,'regular',site,sourceId),
  // Record the same independent language evidence used by the short-topic
  // import path. Without these current-version rows, the protected DEV-to-PROD
  // sync deliberately downgrades otherwise recognized original languages to
  // "und" (especially visible on V2EX long threads).
  stmt(db,`INSERT OR IGNORE INTO content_language_verifications
   (content_type,content_id,content_version,language,method,score)
   SELECT 'topic',id,content_version,source_lang,'tinyld-heavy',NULL FROM topics
   WHERE id=? AND status<>'deleted' AND source_lang_mode='auto' AND source_lang<>'und'`,existing.topic_id),
  stmt(db,`INSERT OR IGNORE INTO content_language_verifications
   (content_type,content_id,content_version,language,method,score)
   SELECT 'comment',id,content_version,source_lang,'tinyld-heavy',NULL FROM comments
   WHERE topic_id=? AND status<>'deleted' AND source_lang_mode='auto' AND source_lang<>'und'`,existing.topic_id),
  stmt(db,'UPDATE collect_sources SET state=?,lease_token_hash=NULL,lease_expires_at=NULL,completion_token_hash=?,topic_id=?,content_hash=?,completed_duplicate=0,completed_at=?,updated_at=? WHERE site=? AND source_id=? AND state=? AND lease_token_hash=?',
   'completed',tokenHash,existing.topic_id,existing.content_hash,now(),now(),site,sourceId,'claimed',tokenHash),
  stmt(db,'UPDATE collector_long_stages SET status=? WHERE site=? AND source_id=? AND lease_hash=?','completed',site,sourceId,tokenHash),
  stmt(db,'DELETE FROM collector_long_replies WHERE site=? AND source_id=?',site,sourceId),
  stmt(db,'INSERT INTO daily_community_metrics(day_utc,new_topics,new_comments) VALUES(date(?),1,?) ON CONFLICT(day_utc) DO UPDATE SET new_topics=new_topics+1,new_comments=new_comments+excluded.new_comments',
   'now',existing.target_count),
  unguard(db,site,sourceId)
 ]);
 return json({status:'completed',duplicate:false,topic_id:existing.topic_id,
  imported:{topics:1,comments:existing.target_count},stored_comments:existing.target_count,
  source_total:existing.source_total,capped:Boolean(existing.capped)},201);
}
