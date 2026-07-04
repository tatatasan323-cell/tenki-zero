# -*- coding: utf-8 -*-
"""体験版（docs/index.html）生成器
GitHub Pages で公開する“ブラウザ内だけで動く tenki-zero 体験版”を生成する。
- マスタ（費目/ルール/従業員）とサンプル3点（売上/経費/勤怠）を実ファイルから埋め込む
- 締めロジックは close.py のサブセットをJSで再実装（CSVのみ・保存なし・送信なし）
実行: python src/gen_demo.py
"""
import os, io, sys, json, csv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = os.path.join

def smart_read(path):
    raw = open(path, "rb").read()
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8")
    for enc in ("utf-8", "cp932"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")

def master(name):
    return [r for r in csv.reader(io.StringIO(smart_read(J(BASE, "masters", name)))) if any(c.strip() for c in r)][1:]

DATA = {
    "items": master("items.csv"),        # [code,name,group]
    "rules": master("rules.csv"),        # [pattern,code]
    "emps": master("employees.csv"),     # [code,name,dept,wtype,rate]
    "samples": {
        "sales": smart_read(J(BASE, "inbox", "sales", "売上連携_2026-05-01_2026-05-31.csv")),
        "expenses": smart_read(J(BASE, "inbox", "expenses", "経費正規化_2026-05.csv")),
        "attendance": smart_read(J(BASE, "inbox", "attendance", "勤怠_2026-05.csv")),
    },
}

HTML = r"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>tenki-zero 体験版 ─ 転記ゼロを、ブラウザで試す</title><style>
body{margin:0;font-family:"Segoe UI","Hiragino Kaku Gothic ProN","Yu Gothic UI",Meiryo,sans-serif;color:#e9f0fa;line-height:1.6;
 background:linear-gradient(165deg,#0a1020,#0c162b 55%,#0a1224);min-height:100vh}
.wrap{max-width:1040px;margin:0 auto;padding:22px 18px}
h1{font-size:1.5rem;font-weight:800;background:linear-gradient(112deg,#fff,#8fd0ff 55%,#ffd67a);
 -webkit-background-clip:text;background-clip:text;color:transparent;margin:.2em 0}
.sub{color:#b6cae2;font-size:.88rem;margin-bottom:6px}
.banner{background:linear-gradient(118deg,rgba(61,143,230,.18),rgba(55,195,154,.14));border:1px solid rgba(143,208,255,.3);
 border-radius:13px;padding:10px 16px;font-size:.86rem;color:#cfe0f2;margin:10px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.card{background:rgba(16,25,44,.66);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:16px 18px;margin:12px 0}
h3{font-size:1rem;color:#eaf3ff;border-left:4px solid #5aa2e6;padding-left:10px;margin:.1em 0 .5em}
.zone{border:2px dashed rgba(140,180,230,.4);border-radius:13px;padding:16px;text-align:center;color:#aec1d8;
 cursor:pointer;background:rgba(10,18,36,.4);transition:.15s;font-size:.88rem}
.zone:hover,.zone.hover{border-color:#5aa2e6;background:rgba(90,160,240,.1)}
.zone b{color:#8fd0ff}
.zone.exp{border-color:rgba(245,165,36,.45)} .zone.exp b{color:#ffd27a}
.zone.att{border-color:rgba(120,220,170,.45)} .zone.att b{color:#8fe6bb}
.list{font-size:.78rem;color:#9fb0c7;margin-top:7px;max-height:110px;overflow-y:auto}
.btn{background:linear-gradient(118deg,#3d8fe6,#37c39a);color:#fff;border:none;border-radius:11px;
 padding:11px 24px;font-size:1rem;font-weight:700;cursor:pointer;font-family:inherit;box-shadow:0 6px 18px rgba(60,150,230,.35)}
.btn.ghost{background:rgba(255,255,255,.06);color:#cfe0f2;border:1px solid rgba(255,255,255,.18);box-shadow:none;font-weight:600}
.btn:hover{filter:brightness(1.08)}
select{font-family:inherit;font-size:1rem;padding:8px 12px;border-radius:9px;border:1px solid rgba(255,255,255,.2);
 background:#0d1830;color:#e9f0fa;margin-right:10px}
.kpis{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px}
.kpi{flex:1;min-width:130px;background:linear-gradient(158deg,rgba(74,150,235,.22),rgba(13,22,42,.66));
 border:1px solid rgba(255,255,255,.1);border-radius:13px;padding:10px 14px}
.kpi .v{font-size:1.15rem;font-weight:800}.kpi .k{font-size:.72rem;color:#9fb2c9}
a.dl{display:inline-block;margin:3px 6px 3px 0;padding:6px 13px;border:1px solid rgba(143,208,255,.4);
 border-radius:9px;color:#8fd0ff;text-decoration:none;font-size:.84rem;cursor:pointer}
a.dl:hover{background:rgba(90,160,240,.12)}
.muted{color:#8ea1b8;font-size:.8rem}
li{margin:.3em 0;font-size:.9rem}
#log{font-size:.8rem;color:#b9ccdf;margin-top:8px;max-height:90px;overflow-y:auto}
.ok{color:#7fe0ae}.skip{color:#ffce7a}.err{color:#ff8a8a}
table{border-collapse:collapse;width:100%;font-size:.84rem;margin-top:6px}
th,td{border:1px solid rgba(255,255,255,.08);padding:5px 9px;text-align:right;color:#cdd9e8}
th{background:rgba(255,255,255,.05);color:#dce8f6} td.l,th.l{text-align:left}
.cta{background:linear-gradient(118deg,rgba(245,165,36,.14),rgba(61,143,230,.12));border:1px solid rgba(255,214,122,.35);
 border-radius:16px;padding:16px 20px;margin:14px 0}
</style></head><body><div class="wrap">
<h1>tenki-zero 体験版 ─ 転記ゼロを、ブラウザで試す</h1>
<div class="sub">売上・経費・勤怠を放り込んで「締める」を押すと、月次帳票が一括で出ます。</div>
<div class="banner">これは <b>体験版</b> です ―― すべてブラウザの中だけで動き、<b>数字はどこにも送信されず、保存もされません</b>（画面を閉じれば消えます）。
毎月“貯めて”自動で締める本物の城は、ページ下部を見てください。</div>

<div class="card" style="text-align:center">
  <button class="btn" onclick="loadSamples()">▶ サンプルデータで、いきなり試す（架空5店舗・1ヶ月分）</button>
  <span class="muted">　または、下の窓口に自分のCSVを放り込む</span>
</div>

<div class="grid">
  <div class="card"><h3>経費</h3>
    <div class="zone exp" data-type="expenses"><b>ここに放り込む</b><br>経費CSV（日付・取引先・金額）<br>請求書CSVもそのままOK</div>
    <div class="list" id="list-expenses"></div></div>
  <div class="card"><h3>売上</h3>
    <div class="zone" data-type="sales"><b>ここに放り込む</b><br>日次売上CSV（日付・店舗・売上）</div>
    <div class="list" id="list-sales"></div></div>
  <div class="card"><h3>勤怠</h3>
    <div class="zone att" data-type="attendance"><b>ここに放り込む</b><br>勤怠システムのCSV（SJISのままOK）</div>
    <div class="list" id="list-attendance"></div></div>
</div>

<div class="card">
  <h3>月次を締める</h3>
  <select id="month"></select>
  <button class="btn" onclick="doClose()">締める ─ 帳票を出力</button>
  <div id="result"></div>
</div>

<div id="log"></div>

<div class="cta">
  <h3 style="border-color:#ffd67a">これ、あなたの会社でも作れます</h3>
  <p style="font-size:.92rem;margin:.3em 0">この画面も、裏側の仕組みも ―― 私は <b>「こういうものが欲しい」とAIに渡しただけ</b> で、コードは1行も書いていません。
  つまり、これくらいのものは <b>あなたの会社のAIエージェントでも作れます</b>。自社の数字に合う“あなたの城”を、自分たちで建てるのが本筋です。</p>
  <p style="font-size:.9rem;margin:.5em 0 .2em">
  ▷ 作り方・設計図（全コード公開）: <a href="https://github.com/tatatasan323-cell/tenki-zero" style="color:#8fd0ff">github.com/tatatasan323-cell/tenki-zero</a><br>
  ▷ どうしても“この城ごと”欲しい方へ: 上のページの「Code → Download ZIP」→ 展開 → <b>起動.bat</b> をダブルクリック（毎月貯まる本物・Excel/PDF対応つき）</p>
</div>

<p class="muted">tenki-zero 体験版 ／ 制作: AI内製化工房 MITA ─ 連載「AI内製化の羅針盤」#13</p>
<input type="file" id="picker" multiple hidden>
</div><script>
const MASTERS = __DATA__;
let files={sales:[],expenses:[],attendance:[]};   // {name, text}
let curType=null;
const log=(m,c)=>{const d=document.getElementById('log');d.innerHTML='<div class="'+(c||'')+'">'+m+'</div>'+d.innerHTML;};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function smartDecode(buf){
  const b=new Uint8Array(buf);
  if(b.length>=3&&b[0]==0xEF&&b[1]==0xBB&&b[2]==0xBF) return new TextDecoder('utf-8').decode(b.subarray(3));
  try{ return new TextDecoder('utf-8',{fatal:true}).decode(b); }catch(e){}
  return new TextDecoder('shift_jis').decode(b);
}
function parseRows(text){
  text=text.replace(/\r\n/g,'\n').replace(/\r/g,'\n');
  const delim=(text.split('\t').length>text.split(',').length)?'\t':',';
  const rows=[]; let row=[],cur='',q=false;
  for(let i=0;i<text.length;i++){ const c=text[i];
    if(q){ if(c=='"'){ if(text[i+1]=='"'){cur+='"';i++;} else q=false; } else cur+=c; }
    else { if(c=='"') q=true; else if(c==delim){ row.push(cur); cur=''; } else if(c=='\n'){ row.push(cur); rows.push(row); row=[]; cur=''; } else cur+=c; }
  }
  if(cur.length||row.length){ row.push(cur); rows.push(row); }
  return rows.filter(r=>r.some(c=>c.trim()!==''));
}
const num=s=>{const t=String(s).replace(/[^0-9.\-]/g,'');const n=parseFloat(t);return isNaN(n)?0:n;};
const dt=s=>{const m=String(s).trim().match(/(\d{4})\D(\d{1,2})\D(\d{1,2})/);return m?m[1]+'-'+String(m[2]).padStart(2,'0')+'-'+String(m[3]).padStart(2,'0'):null;};
const ALIAS={date:['日付','請求日','取引日','営業日','date'],store:['店舗','店名','所属','store'],
 amount:['売上','金額','請求額','amount','total'],vendor:['取引先','仕入先','請求元','vendor'],
 item:['品目','内容','摘要','item'],emp:['従業員コード','社員コード','emp'],minutes:['実労働時間(分)','労働時間(分)','minutes']};
function headerMap(hdr){const m={};hdr.forEach((h,i)=>{h=String(h).trim();for(const f in ALIAS)if(ALIAS[f].includes(h))m[f]=i;});return m;}
function readTable(text,need,fname){
  const rows=parseRows(text);
  for(let hi=0;hi<Math.min(10,rows.length);hi++){
    const m=headerMap(rows[hi]);
    if(need.every(k=>k in m)){
      return rows.slice(hi+1).map(r=>{const o={};for(const k in m)o[k]=(r[m[k]]||'').trim();o.__f=fname;return o;});
    }
  }
  return null;
}
function refresh(){
  for(const t in files){
    document.getElementById('list-'+t).innerHTML=files[t].map(f=>'<div>'+esc(f.name)+'</div>').join('')||'<div style="opacity:.5">（まだありません）</div>';
  }
  const ms=new Set();
  for(const t in files) for(const f of files[t]) for(const m of (f.text.match(/\d{4}[-\/]\d{1,2}/g)||[])){
    const p=m.replace('/','-').split('-'); ms.add(p[0]+'-'+p[1].padStart(2,'0'));
  }
  const sel=document.getElementById('month'); const cur=sel.value;
  sel.innerHTML=[...ms].sort().reverse().map(m=>'<option>'+m+'</option>').join('')||'<option>----</option>';
  if(cur&&[...ms].includes(cur)) sel.value=cur;
}
function addFile(type,name,text){
  if(files[type].some(f=>f.text===text)){ log('― スキップ(同じ内容): '+name,'skip'); return; }
  files[type].push({name,text}); log('✔ 受付: '+name,'ok');
}
function loadSamples(){
  addFile('sales','売上連携_2026-05(サンプル).csv',MASTERS.samples.sales);
  addFile('expenses','経費正規化_2026-05(サンプル).csv',MASTERS.samples.expenses);
  addFile('attendance','勤怠_2026-05(サンプル).csv',MASTERS.samples.attendance);
  refresh(); document.getElementById('month').value='2026-05';
}
document.querySelectorAll('.zone').forEach(z=>{
  z.onclick=()=>{curType=z.dataset.type;document.getElementById('picker').click();};
  ['dragover','dragenter'].forEach(ev=>z.addEventListener(ev,e=>{e.preventDefault();z.classList.add('hover');}));
  z.addEventListener('dragleave',e=>z.classList.remove('hover'));
  z.addEventListener('drop',async e=>{e.preventDefault();z.classList.remove('hover');curType=z.dataset.type;
    for(const f of e.dataTransfer.files) addFile(curType,f.name,smartDecode(await f.arrayBuffer()));refresh();});
});
document.getElementById('picker').onchange=async e=>{
  for(const f of e.target.files) addFile(curType,f.name,smartDecode(await f.arrayBuffer()));refresh();};

const yen=n=>'¥'+Math.round(n).toLocaleString('ja-JP');
function svgBars(pairs,color){
  if(!pairs.length) return '';
  const W=640,H=200,pl=10,pb=28,pt=20,mx=Math.max(...pairs.map(p=>p[1]));
  const gap=(W-pl*2)/pairs.length,bw=Math.min(56,gap*0.62);let b='';
  pairs.forEach(([lab,v],i)=>{const x=pl+gap*i+(gap-bw)/2,h=(H-pt-pb)*(v/mx),y=pt+(H-pt-pb)-h;
    b+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+h.toFixed(1)+'" rx="3" fill="'+color+'"/>'
     +'<text x="'+(x+bw/2).toFixed(1)+'" y="'+(y-4).toFixed(1)+'" text-anchor="middle" font-size="10" fill="#c3d2e4">¥'+Math.round(v/1000).toLocaleString()+'k</text>'
     +'<text x="'+(x+bw/2).toFixed(1)+'" y="'+(H-pb+15)+'" text-anchor="middle" font-size="11" fill="#aebccd">'+esc(lab)+'</text>';});
  return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="max-width:680px">'+b+'</svg>';
}
let dls={};
function dlLink(name,csv){ dls[name]=csv; return '<a class="dl" onclick="dl(\''+name+'\')">'+name+'</a>'; }
function dl(name){ const blob=new Blob(['﻿'+dls[name]],{type:'text/csv'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click(); }
const csvOf=(hdr,rows)=>hdr.join(',')+'\n'+rows.map(r=>r.join(',')).join('\n')+'\n';

function doClose(){
  const month=document.getElementById('month').value;
  if(!/^\d{4}-\d{2}$/.test(month)){alert('データを入れてから月を選んでください');return;}
  const items={}; MASTERS.items.forEach(([c,n,g])=>items[c]=[n,g]);
  const emps={}; MASTERS.emps.forEach(r=>emps[r[0]]=r);
  // 売上: (日付,店舗) 後勝ち
  const sales={};
  for(const f of files.sales){ const rs=readTable(f.text,['date','amount'],f.name); if(!rs) continue;
    for(const r of rs){ const d=dt(r.date); if(!d||d.slice(0,7)!==month||!num(r.amount)) continue;
      sales[d+'|'+(r.store||f.name.replace(/\.\w+$/,''))]=num(r.amount); } }
  // 経費: 完全一致スキップ + ルール仕分け
  const seen=new Set(), exps=[];
  for(const f of files.expenses){ const rs=readTable(f.text,['date','amount'],f.name); if(!rs) continue;
    const fb=f.name.replace(/(_請求書)?\.\w+$/,'').replace(/\(サンプル\)/,'');
    for(const r of rs){ const d=dt(r.date), it=r.item||'';
      if(/合計|小計|total/i.test(it)) continue;
      if(!d||d.slice(0,7)!==month||!num(r.amount)) continue;
      const v=r.vendor||fb, key=d+'|'+v+'|'+it+'|'+Math.round(num(r.amount));
      if(seen.has(key)) continue; seen.add(key);
      let code='MISC'; for(const [pat,c] of MASTERS.rules){ if(v.toLowerCase().includes(pat.toLowerCase())){code=c;break;} }
      exps.push({d,v,it,a:num(r.amount),code}); } }
  // 勤怠: (日付,emp) 後勝ち
  const att={};
  for(const f of files.attendance){ const rs=readTable(f.text,['date','emp','minutes'],f.name); if(!rs) continue;
    for(const r of rs){ const d=dt(r.date); if(!d||d.slice(0,7)!==month) continue; att[d+'|'+r.emp]=num(r.minutes); } }

  const salesTotal=Object.values(sales).reduce((s,v)=>s+v,0);
  if(!salesTotal){document.getElementById('result').innerHTML='<p class="err">'+month+' の売上データがありません。</p>';return;}
  const byStore={},byDay={};
  for(const k in sales){ const [d,s]=k.split('|'); byStore[s]=(byStore[s]||0)+sales[k]; byDay[d]=(byDay[d]||0)+sales[k]; }
  const stores=Object.entries(byStore).sort((a,b)=>b[1]-a[1]);
  const byItem={}; exps.forEach(e=>{ const n=(items[e.code]||[e.code])[0]; byItem[n]=(byItem[n]||0)+e.a; });
  const cogs=exps.filter(e=>(items[e.code]||[])[1]==='売上原価').reduce((s,e)=>s+e.a,0);
  const miscN=exps.filter(e=>e.code==='MISC').length;
  // 給与もと
  const mins={}; for(const k in att){ const emp=k.split('|')[1]; mins[emp]=(mins[emp]||0)+att[k]; }
  const pay=Object.keys(emps).map(c=>{const [code,name,dept,wt,rate]=emps[c];
    const m=mins[c]||0; const base=wt==='月給'?+rate:Math.round(m/60*+rate);
    return [code,name,dept,wt,rate,(m/60).toFixed(1),m?base:(wt==='月給'&&m?base:m?base:(wt==='月給'?base:0))]; });
  const payTotal=pay.reduce((s,r)=>s+(+r[6]||0),0);
  const sga=Object.entries(byItem).filter(([n])=>n!=='仕入高').reduce((s,[,a])=>s+a,0)+payTotal;
  const gross=salesTotal-cogs, op=gross-sga;
  // 帳票CSV
  dls={};
  const plRows=[['売上高',Math.round(salesTotal),''],['売上原価(仕入高)',Math.round(cogs),'経費データより'],
   ['売上総利益',Math.round(gross),'粗利率 '+(gross/salesTotal*100).toFixed(1)+'%'],['給与手当',payTotal,'勤怠データより']]
   .concat(Object.entries(byItem).filter(([n])=>n!=='仕入高').sort((a,b)=>b[1]-a[1]).map(([n,a])=>[n,Math.round(a),'経費データより']))
   .concat([['販管費計',Math.round(sga),''],['営業利益',Math.round(op),'営業利益率 '+(op/salesTotal*100).toFixed(1)+'%']]);
  let links='';
  links+=dlLink('01_月次損益.csv',csvOf(['科目','金額','備考'],plRows));
  links+=dlLink('02_経費内訳_費目別.csv',csvOf(['費目','金額'],Object.entries(byItem).sort((a,b)=>b[1]-a[1]).map(([n,a])=>[n,Math.round(a)])));
  links+=dlLink('03_売上計上_店舗別.csv',csvOf(['店舗','売上','構成比%'],stores.map(([s,a])=>[s,Math.round(a),(a/salesTotal*100).toFixed(1)])));
  links+=dlLink('05_給与もと資料.csv',csvOf(['従業員コード','氏名','所属','給与区分','単価','実労働時間(h)','基本支給額(もと)'],pay));
  links+=dlLink('08_税理士パック_仕訳候補.csv',csvOf(['日付','科目','金額','摘要'],
    Object.keys(sales).sort().map(k=>{const [d,s]=k.split('|');return [d,'売上高',Math.round(sales[k]),'売上計上 '+s];})
    .concat(exps.map(e=>[e.d,(items[e.code]||[e.code])[0],Math.round(e.a),e.v+' '+e.it]))));
  const kpi=[['売上高',yen(salesTotal)],['売上総利益',yen(gross)+' ('+(gross/salesTotal*100).toFixed(1)+'%)'],
   ['営業利益',yen(op)+' ('+(op/salesTotal*100).toFixed(1)+'%)'],['未分類',miscN+' 件']];
  const wd=['日','月','火','水','木','金','土'],wsum={};
  Object.entries(byDay).forEach(([d,a])=>{const w=wd[new Date(d+'T00:00:00').getDay()];wsum[w]=(wsum[w]||0)+a;});
  const topWd=Object.entries(wsum).sort((a,b)=>b[1]-a[1])[0];
  const comments=[
   '売上トップは '+stores[0][0]+'（'+yen(stores[0][1])+'・構成比 '+(stores[0][1]/salesTotal*100).toFixed(1)+'%）。最下位 '+stores[stores.length-1][0]+' との差は '+(stores[0][1]/Math.max(stores[stores.length-1][1],1)).toFixed(1)+'倍。',
   '曜日では '+topWd[0]+'曜が最大（'+yen(topWd[1])+'）。仕込み・シフトは'+topWd[0]+'曜に厚く。',
   '原価率 '+(cogs/salesTotal*100).toFixed(1)+'%・人件費率 '+(payTotal/salesTotal*100).toFixed(1)+'%。',
   miscN?('未分類の経費が '+miscN+'件 ―― 本物の城では“仕分けルール”に1行足せば翌月から自動になります。'):'経費の未分類は 0件 ―― 仕分けルールは健在です。'];
  document.getElementById('result').innerHTML=
   '<div class="kpis">'+kpi.map(([k,v])=>'<div class="kpi"><div class="v">'+v+'</div><div class="k">'+k+'</div></div>').join('')+'</div>'
   +'<div class="card"><h3>分析コメント（自動生成）</h3><ul>'+comments.map(c=>'<li>'+c+'</li>').join('')+'</ul></div>'
   +'<div class="card"><h3>店舗別 売上</h3>'+svgBars(stores,'#37c39a')+'</div>'
   +'<div class="card"><h3>経費 費目別</h3>'+svgBars(Object.entries(byItem).sort((a,b)=>b[1]-a[1]).slice(0,7),'#f5a524')+'</div>'
   +'<p style="margin:.6em 0 .2em">帳票（クリックで保存）:</p>'+links
   +'<p class="muted">体験版はここまで（CSVのみ・保存されません）。毎月貯める／Excel・PDF取込／Excel帳票は、本物の城で。</p>';
}
refresh();
</script></body></html>"""

os.makedirs(J(BASE, "docs"), exist_ok=True)
html = HTML.replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
with open(J(BASE, "docs", "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("docs/index.html 生成: %.1f KB" % (os.path.getsize(J(BASE, "docs", "index.html")) / 1024))
