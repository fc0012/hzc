async function loadData(){
  const res = await fetch('/api/servers');
  const data = await res.json();
  const tb = document.querySelector('#tb tbody');
  tb.innerHTML='';
  data.forEach(r=>{
    const tr=document.createElement('tr');
    const ratio=(r.ratio*100).toFixed(1)+'%';
    tr.innerHTML=`<td>${r.id}</td><td>${r.name}</td><td>${r.ip}</td><td>${r.status}</td><td>${r.used_tb}</td><td>${r.limit_tb}</td><td class="${r.over_threshold?'warn':''}">${ratio}</td><td><button onclick="rotate(${r.id})">重建</button></td>`;
    tb.appendChild(tr);
  })
}

async function rotate(id){
  if(!confirm('确认重建该服务器?')) return;
  const res = await fetch(`/api/rotate/${id}`,{method:'POST'});
  const data = await res.json();
  alert(JSON.stringify(data));
  loadData();
}

loadData();
setInterval(loadData, 60000);
