'use strict';
const byId=id=>document.getElementById(id);
let token='', revision=0, nextOffset=null;
const status=message=>{byId('status').textContent=message;};
async function api(query='', options={}) {
  const response=await fetch('/_shin/api/content'+query,{...options,credentials:'omit',headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'}});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error||'操作に失敗しました');
  return data;
}
function blank(){revision=0;for(const id of ['slug','title','body'])byId(id).value='';byId('slug').readOnly=false;byId('published').checked=false;byId('revision').textContent='新規記事';}
async function list(offset=0){
  const collection=byId('collection').value;
  const query=new URLSearchParams({offset:String(offset)});if(collection)query.set('collection',collection);
  const data=await api('?'+query);
  if(!byId('collection').options.length){for(const name of data.collections){const option=document.createElement('option');option.value=name;option.textContent=name;byId('collection').append(option);}}
  byId('items').replaceChildren();
  for(const item of data.items){const button=document.createElement('button');button.type='button';button.className='item';button.textContent=item.title+' · '+(item.published?'公開':'下書き');button.addEventListener('click',()=>edit(item.slug).catch(error=>status(error.message)));byId('items').append(button);}
  nextOffset=data.next;byId('next').hidden=nextOffset===null;
}
async function edit(slug){const q=new URLSearchParams({collection:byId('collection').value,slug});const data=await api('?'+q);for(const key of ['slug','title','body'])byId(key).value=data[key];byId('slug').readOnly=true;byId('published').checked=data.published;revision=data.revision;byId('revision').textContent='revision '+revision;status('読み込みました。');}
byId('login').addEventListener('submit',async event=>{event.preventDefault();token=byId('token').value;try{await list();byId('token').value='';byId('auth').hidden=true;byId('studio').hidden=false;blank();status('編集を開始しました。');}catch(error){token='';status(error.message);}});
byId('logout').addEventListener('click',()=>{token='';byId('token').value='';byId('auth').hidden=false;byId('studio').hidden=true;byId('items').replaceChildren();byId('collection').replaceChildren();blank();status('ロックしました。');});
byId('new').addEventListener('click',blank);
byId('collection').addEventListener('change',()=>{blank();list().catch(error=>status(error.message));});
byId('next').addEventListener('click',()=>list(nextOffset).catch(error=>status(error.message)));
byId('editor').addEventListener('submit',async event=>{event.preventDefault();byId('save').disabled=true;try{const data=await api('',{method:'PUT',body:JSON.stringify({collection:byId('collection').value,slug:byId('slug').value,title:byId('title').value,body:byId('body').value,published:byId('published').checked,revision})});revision=data.revision;byId('slug').readOnly=true;byId('revision').textContent='revision '+revision;await list();status(data.published?'公開して保存しました。':'下書きを保存しました。');}catch(error){status(error.message);}finally{byId('save').disabled=false;}});
