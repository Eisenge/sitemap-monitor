async function loadData(){

const groups = await fetch('/sitemap-monitor/data/groups.json')
.then(res=>res.json());

const websites = await fetch('/sitemap-monitor/data/websites.json')
.then(res=>res.json());


let html = "";

groups.forEach(group=>{

let sites = websites.filter(
w=>w.group === group.name
);


html += `
<div class="card">

<h2>${group.name}</h2>

<p>
网站数量:
${sites.length}
</p>

${sites.map(site=>`

<div class="site">

<b>${site.name}</b>

<br>

${site.url}

</div>

`).join("")}

</div>
`;

});


document.getElementById("app").innerHTML = html;

}


loadData();