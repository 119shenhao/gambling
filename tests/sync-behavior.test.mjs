import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fingerprint,sortComments,buildInserts,resolveSyncLanguage} from '../scripts/sync-preview-to-production.mjs';

test('gambling one-time sync fingerprints canonical title and body',()=>{
 assert.equal(fingerprint(' Test ', 'Hello  world'),fingerprint('test','hello world'));
 assert.notEqual(fingerprint('test','first'),fingerprint('test','second'));
});
test('production language requires verified current version',()=>{
 const draft={status:'published',source_lang:'en',source_lang_mode:'auto',
  content_version:2,verified_version:1,verified_language:'en',
  verified_method:'tinyld-heavy',verified_score:0.9};
 assert.deepEqual(resolveSyncLanguage(draft),{label:'und',mode:'legacy',method:null,score:null});
 const current={...draft,verified_version:2};
 assert.deepEqual(resolveSyncLanguage(current),{label:'en',mode:'auto',method:'tinyld-heavy',score:0.9});
 assert.equal(resolveSyncLanguage({...draft,source_lang_mode:'manual'}).mode,'manual');
});
test('source comments preserve parent before nested children',()=>{
 const source=[
  {id:'c3',parent_comment_id:'c2',status:'published'},
  {id:'c1',parent_comment_id:null,status:'published'},
  {id:'c2',parent_comment_id:'c1',status:'published'},
  {id:'hidden',parent_comment_id:null,status:'pending_review'}];
 const ordered=sortComments(source);
 assert.deepEqual(ordered.map(c=>c.id),['c1','c2','c3']);
 assert.throws(()=>sortComments([
   {id:'a',parent_comment_id:'b',status:'published'},
   {id:'b',parent_comment_id:'a',status:'published'}]),/Cyclic comment tree/);
});
test('production SQL is idempotent and preserves all three-level reply relationships in isolated SQLite',()=>{
 const lang={source_lang:'en',source_lang_mode:'manual',status:'published',
  content_version:1,verified_version:null,verified_method:null,verified_language:null,verified_score:null};
 const topic={...lang,id:'qa-topic-one',title:'QA One',body:'Original fixture body',
  symptom_duration_days:null,created_at:1795321800};
 const comments=[
  {...lang,id:'qa-comment-one',parent_comment_id:null,kind:'regular',progress_seq:null,
   body:'A first-level reply',created_at:1795321801},
  {...lang,id:'qa-comment-two',parent_comment_id:'qa-comment-one',kind:'regular',progress_seq:null,
   body:'A nested reply',created_at:1795321802},
  {...lang,id:'qa-comment-three',parent_comment_id:'qa-comment-two',kind:'regular',progress_seq:null,
   body:'A third-level reply',created_at:1795321803}
 ];
 const sql=buildInserts(topic,comments,[],fingerprint(topic.title,topic.body));
 assert.match(sql,/INSERT OR IGNORE INTO topics/);
 assert.match(sql,/INSERT OR IGNORE INTO comments/);
 assert.doesNotMatch(sql,/spine-topic-v1|spine-community/);
 const py=String.raw`
import json,sys,sqlite3
sql=sys.stdin.read()
conn=sqlite3.connect(':memory:')
conn.executescript("""
CREATE TABLE topics(id TEXT PRIMARY KEY,author_id TEXT,title TEXT,body TEXT,source_lang TEXT,source_lang_mode TEXT,status TEXT,symptom_duration_days INTEGER,content_hash TEXT UNIQUE,created_at INTEGER);
CREATE TABLE comments(id TEXT PRIMARY KEY,topic_id TEXT,author_id TEXT,parent_comment_id TEXT,kind TEXT,progress_seq INTEGER,body TEXT,source_lang TEXT,source_lang_mode TEXT,status TEXT,created_at INTEGER);
CREATE TABLE topic_terms(topic_id TEXT,term_id TEXT,PRIMARY KEY(topic_id,term_id));
CREATE TABLE content_language_verifications(content_type TEXT,content_id TEXT,content_version INTEGER,language TEXT,method TEXT,score REAL,PRIMARY KEY(content_type,content_id,content_version));
""")
conn.executescript(sql)
conn.executescript(sql)
topics=conn.execute("SELECT count(*) FROM topics").fetchone()[0]
comments=conn.execute("SELECT id,parent_comment_id,author_id FROM comments ORDER BY created_at").fetchall()
assert topics==1
assert len(comments)==3
assert [(c[0],c[1]) for c in comments]==[('qa-comment-one',None),('qa-comment-two','qa-comment-one'),('qa-comment-three','qa-comment-two')]
assert all(c[2]=='system-unknown-import' for c in comments)
assert conn.execute("SELECT author_id FROM topics").fetchone()[0]=='system-unknown-import'
print(json.dumps({'new_topics':topics,'comments':len(comments),'repeat_inserts_skipped':True,'parentage':'verified'}))
`;
 const checked=spawnSync('python3',['-c',py],{input:sql,encoding:'utf8'});
 assert.equal(checked.status,0,checked.stderr);
 const actual=JSON.parse(checked.stdout);
 assert.equal(actual.new_topics,1);
 assert.equal(actual.comments,3);
 assert.equal(actual.repeat_inserts_skipped,true);
});
