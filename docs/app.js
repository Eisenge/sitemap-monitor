async function load(){
let g=await fetch('../data/groups.json').then(r=>r.json());
let w=await fetch('../data/websites.json').then(r=>r.json());
document.getElementById('app').innerHTML=g.map(x=>'<div class="card"><h2>'+x.name+'</h2>'+w.filter(y=>y.group==x.name).map(y=>y.name+' '+y.url).join('<br>')+'</div>').join('');
}
function addGroup(){alert('升级版接口预留');}
function addSite(){alert('升级版接口预留');}
load();
