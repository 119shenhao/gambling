import {readFileSync,readdirSync,mkdirSync,rmSync,copyFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
// Isolated source build. Never connect to a remote D1 or run external content collection.
for(const args of [['node_modules/typescript/bin/tsc','--noEmit'],['--test','tests/gambling.test.mjs']]){
 const result=spawnSync(process.execPath,args,{stdio:'inherit'});
 if(result.status!==0)throw Error('Source checks failed; refusing build');
}
// The optional remote migration script is gated by WORKERS_CI and the exact dev branch.
const remote=spawnSync(process.execPath,['scripts/preview-migrate.mjs'],{stdio:'inherit'});
if(remote.status!==0)throw Error('Isolated Preview D1 preparation failed');
// One-time OAuth Secret setup completed. Do not run it on ordinary builds.
const ownerGrant=spawnSync(process.execPath,['scripts/grant-owner-dev-once.mjs'],{stdio:'inherit'});
if(ownerGrant.status!==0)throw Error('Verified DEV Owner role grant failed; refusing preview build.');


function createVersionedFrontend() {
 // Static JS and CSS are served directly from Cloudflare Assets/CDN (no extra
 // Worker invocations). A unique directory for every content revision avoids
 // browsers mixing an old entry module with newly deployed dependencies.
 const root='public';
 const names=readdirSync(root,{withFileTypes:true})
  .filter(item=>item.isFile()&&/\.(js|css)$/.test(item.name))
  .map(item=>item.name).sort();
 if(!names.includes('app.js')||!names.includes('styles.css'))throw Error('Frontend entry assets missing');
 const h=createHash('sha256');
 for(const name of names){h.update(name);h.update('\0');h.update(readFileSync(join(root,name)));}
 const revision=h.digest('hex').slice(0,16);
 const folder=join(root,'_app');
 rmSync(folder,{recursive:true,force:true});
 mkdirSync(join(folder,revision),{recursive:true});
 for(const name of names)copyFileSync(join(root,name),join(folder,revision,name));
 const htmlFile=join(root,'index.html');
 const html=readFileSync(htmlFile,'utf8');
 const entry=/<link rel="stylesheet" href="\/(?:_app\/[a-f0-9]{16}\/)?styles\.css"><script type="module" src="\/(?:_app\/[a-f0-9]{16}\/)?app\.js"><\/script>/;
 if(!entry.test(html))throw Error('Frontend HTML entry markup changed; refusing a stale deployment');
 const replacement='<link rel="stylesheet" href="/_app/'+revision+'/styles.css">'+
  '<script type="module" src="/_app/'+revision+'/app.js"></script>';
 writeFileSync(htmlFile,html.replace(entry,replacement),'utf8');
 console.log('Frontend asset revision '+revision+' ('+names.length+' versioned CSS/JS files)');
}
createVersionedFrontend();
