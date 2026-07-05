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
    "depts": master("depts.csv"),        # [code,name]
    "holidays": [r[0] for r in master("holidays.csv")],
    "samples": {
        "sales": smart_read(J(BASE, "inbox", "sales", "売上連携_2026-05-01_2026-05-31.csv")),
        "expenses": smart_read(J(BASE, "inbox", "expenses", "経費正規化_2026-05.csv")),
        "expenses2": smart_read(J(BASE, "inbox", "expenses", "内部経費_2026-05.csv")),
        "attendance": smart_read(J(BASE, "inbox", "attendance", "勤怠_2026-05.csv")),
    },
}

HTML = r"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>tenki-zero 体験版 ─ 転記ゼロを、ブラウザで試す</title><style>
body{margin:0;font-family:"Segoe UI","Hiragino Kaku Gothic ProN","Yu Gothic UI",Meiryo,sans-serif;color:#e9f0fa;line-height:1.6;
 background:linear-gradient(165deg,#0a1020,#0c162b 55%,#0a1224);min-height:100vh}
.wrap{max-width:1180px;margin:0 auto;padding:22px 18px}
.grid2{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:14px;align-items:start}
.grid2 .col>.card:first-child{margin-top:12px}
@media(max-width:920px){.grid2{grid-template-columns:1fr}}
.lgd{display:flex;flex-wrap:wrap;gap:6px 14px;margin:2px 0 8px;font-size:.74rem;color:#b6cae2}
.lg{display:inline-flex;align-items:center;gap:5px}
.lg i{width:11px;height:11px;border-radius:3px;display:inline-block}
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
table.mx{border-collapse:collapse;width:100%;font-size:.8rem;min-width:640px}
table.mx th,table.mx td{border:1px solid rgba(255,255,255,.1);padding:5px 8px;text-align:right;color:#cdd9e8;white-space:nowrap}
table.mx th{background:rgba(90,160,240,.16);color:#eaf3ff}
table.mx td.l,table.mx th.l{text-align:left;position:sticky;left:0;background:#0e1a30}
table.mx tr.hl td{background:rgba(55,195,154,.12);color:#eaffef}
table.mx tr:last-child td{border-top:2px solid rgba(255,255,255,.25)}
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
    <div class="zone exp" data-type="expenses"><b>ここに放り込む</b><br>経費CSV／請求書CSVそのまま<br>Excel(.xlsx)もOK</div>
    <div class="list" id="list-expenses"></div></div>
  <div class="card"><h3>売上</h3>
    <div class="zone" data-type="sales"><b>ここに放り込む</b><br>日次売上CSV（日付・店舗・売上）<br>
      <span style="font-size:.72rem;color:#8ea1b8">※レジ明細などバラバラの売上は、#12記事の売上集計ツールで綺麗にしてから</span></div>
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

<p class="muted" style="border-top:1px solid rgba(255,255,255,.08);padding-top:12px;margin-top:18px">
<b>tenki-zero ─ 体験版</b> ／ 制作：AI内製化工房 MITA　｜　公式チャンネル：https://note.com/ai_naiseika ─ 連載「AI内製化の羅針盤」#13<br>
すべてブラウザの中だけで動きます（送信・保存なし）。ご利用は自己責任で。会計・税務の最終判断は税理士等の専門家にご相談ください。</p>
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
const dt=s=>{s=String(s).trim();
  if(/^[45]\d{4}(\.0+)?$/.test(s)){const d=new Date(Date.UTC(1899,11,30)+(+s)*86400000);return d.toISOString().slice(0,10);}  // Excelの日付シリアル値
  const m=s.match(/(\d{4})\D(\d{1,2})\D(\d{1,2})/);return m?m[1]+'-'+String(m[2]).padStart(2,'0')+'-'+String(m[3]).padStart(2,'0'):null;};

// ===== Excel(.xlsx)読み取り ― 借り物ゼロ(xlsxの正体は“圧縮XML”。解凍はブラウザ標準のDecompressionStream) =====
const unesc=s=>String(s)
  .replace(/&#x([0-9a-fA-F]+);/g,(_,h)=>String.fromCodePoint(parseInt(h,16)))
  .replace(/&#(\d+);/g,(_,d)=>String.fromCodePoint(+d))
  .replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&apos;/g,"'").replace(/&amp;/g,'&');
async function xlsxToCsv(buf){
  const u8=new Uint8Array(buf), dv=new DataView(buf);
  let e=-1;
  for(let i=u8.length-22;i>=Math.max(0,u8.length-65558);i--){ if(dv.getUint32(i,true)===0x06054b50){e=i;break;} }
  if(e<0) throw 'not-zip';
  const n=dv.getUint16(e+10,true); let p=dv.getUint32(e+16,true);
  const entries={};
  for(let i=0;i<n;i++){
    if(dv.getUint32(p,true)!==0x02014b50) break;
    const method=dv.getUint16(p+10,true), csize=dv.getUint32(p+20,true),
      nl=dv.getUint16(p+28,true), el=dv.getUint16(p+30,true), cl=dv.getUint16(p+32,true),
      lho=dv.getUint32(p+42,true);
    entries[new TextDecoder().decode(u8.subarray(p+46,p+46+nl))]={method,csize,lho};
    p+=46+nl+el+cl;
  }
  async function get(name){
    const f=entries[name]; if(!f) return null;
    const nl=dv.getUint16(f.lho+26,true), el=dv.getUint16(f.lho+28,true);
    const data=u8.subarray(f.lho+30+nl+el, f.lho+30+nl+el+f.csize);
    if(f.method===0) return new TextDecoder().decode(data);
    return await new Response(new Blob([data]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).text();
  }
  const ss=[]; const ssx=await get('xl/sharedStrings.xml');
  if(ssx) for(const m of ssx.matchAll(/<si[^>]*>([\s\S]*?)<\/si>/g))
    ss.push(unesc([...m[1].matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(t=>t[1]).join('')));
  const shName=Object.keys(entries).filter(k=>/^xl\/worksheets\/sheet\d+\.xml$/.test(k)).sort()[0];
  const sx=await get(shName); if(!sx) throw 'no-sheet';
  const rows=[];
  for(const rm of sx.matchAll(/<row[^>]*>([\s\S]*?)<\/row>/g)){
    const cells={}; let mx=0;
    for(const cm of rm[1].matchAll(/<c([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)){
      const ref=(cm[1].match(/r="([A-Z]+)\d+"/)||[])[1]||'', t=(cm[1].match(/t="(\w+)"/)||[])[1]||'', inner=cm[2]||'';
      let v='';
      if(t==='inlineStr') v=unesc([...inner.matchAll(/<t[^>]*>([\s\S]*?)<\/t>/g)].map(x=>x[1]).join(''));
      else { const vm=inner.match(/<v>([\s\S]*?)<\/v>/); v=vm?unesc(vm[1]):''; if(t==='s') v=ss[+v]??''; }
      let ci=0; for(const ch of ref) ci=ci*26+(ch.charCodeAt(0)-64);
      ci=Math.max(0,ci-1); cells[ci]=v; mx=Math.max(mx,ci);
    }
    const row=[]; for(let i=0;i<=mx;i++) row.push(cells[i]??'');
    if(row.some(c=>String(c).trim()!=='')) rows.push(row);
  }
  return rows.map(r=>r.map(c=>{c=String(c);return /[",\n]/.test(c)?'"'+c.replace(/"/g,'""')+'"':c;}).join(',')).join('\n');
}
async function fileToText(f){
  const n=f.name.toLowerCase();
  if(n.endsWith('.xlsx')||n.endsWith('.xlsm')) return await xlsxToCsv(await f.arrayBuffer());
  if(n.endsWith('.pdf')) throw 'pdf';
  return smartDecode(await f.arrayBuffer());
}
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
function checkSales(text,name){
  // 売上ファイルの試し読み。読めない/明細型は受付で断り、#12の門へ案内する
  const G='#12記事の売上集計ツールで「連携用CSV」にしてから入れてください';
  const rs=readTable(text,['date','amount'],name)||[];
  const per={}, stores=new Set(); let valid=0;
  for(const r of rs){ const d=dt(r.date); if(!d||!num(r.amount)) continue;
    valid++; const st=r.store||name.replace(/\.\w+$/,''); stores.add(st);
    per[d+'|'+st]=(per[d+'|'+st]||0)+1; }
  if(!valid) return {level:'err',msg:'売上として読める行がありません ─ レジ明細などバラバラの売上は、'+G};
  if(Math.max(...Object.values(per))>1)
    return {level:'err',msg:'同じ日・同じ店舗の行が複数あります（レシート明細のようです）─ このまま入れると数字が欠けます。'+G};
  const known=new Set(MASTERS.depts.map(r=>r[1]));
  const unknown=[...stores].filter(s=>!known.has(s));
  if(unknown.length) return {level:'err',msg:'店舗マスタにない店舗名があります（'+unknown.slice(0,3).join('、')+'）─ '+G};
  return {level:'ok',msg:'売上として読めます（'+new Set(Object.keys(per).map(k=>k.split('|')[0])).size+'日分・'+[...stores].sort().join('、')+'）'};
}
function addFile(type,name,text){
  if(files[type].some(f=>f.text===text)){ log('― スキップ(同じ内容): '+name,'skip'); return; }
  if(type==='sales'){
    const c=checkSales(text,name);
    if(c.level==='err'){ log('⛔ 受付できません: '+name+' ─ '+c.msg,'err'); return; }
    files[type].push({name,text}); log('✔ 受付: '+name,'ok'); log('　'+c.msg,'ok');
    return;
  }
  files[type].push({name,text}); log('✔ 受付: '+name,'ok');
}
function loadSamples(){
  addFile('sales','売上連携_2026-05(サンプル).csv',MASTERS.samples.sales);
  addFile('expenses','経費正規化_2026-05(サンプル).csv',MASTERS.samples.expenses);
  addFile('expenses','内部経費_2026-05(サンプル).csv',MASTERS.samples.expenses2);
  addFile('attendance','勤怠_2026-05(サンプル).csv',MASTERS.samples.attendance);
  refresh(); document.getElementById('month').value='2026-05';
}
async function takeFiles(fs){
  for(const f of fs){
    try{ addFile(curType,f.name,await fileToText(f)); }
    catch(err){
      if(err==='pdf') log('✕ PDFは体験版では読めません: '+f.name+' ―― AIに「この表をCSVにして」と頼むか、本物の城（Python版）でどうぞ','err');
      else log('✕ 読み取れませんでした: '+f.name,'err');
    }
  }
  refresh();
}
document.querySelectorAll('.zone').forEach(z=>{
  z.onclick=()=>{curType=z.dataset.type;document.getElementById('picker').click();};
  ['dragover','dragenter'].forEach(ev=>z.addEventListener(ev,e=>{e.preventDefault();z.classList.add('hover');}));
  z.addEventListener('dragleave',e=>z.classList.remove('hover'));
  z.addEventListener('drop',e=>{e.preventDefault();z.classList.remove('hover');curType=z.dataset.type;takeFiles(e.dataTransfer.files);});
});
document.getElementById('picker').onchange=e=>takeFiles(e.target.files);

const yen=n=>'¥'+Math.round(n).toLocaleString('ja-JP');
function svgBars(pairs,color,labelEvery,showVal){
  if(!pairs.length) return ''; labelEvery=labelEvery||1; showVal=showVal!==false;
  const W=640,H=200,pl=10,pb=28,pt=20,mx=Math.max(...pairs.map(p=>p[1]));
  const gap=(W-pl*2)/pairs.length,bw=Math.min(56,gap*0.62);let b='';
  pairs.forEach(([lab,v],i)=>{const x=pl+gap*i+(gap-bw)/2,h=(H-pt-pb)*(v/mx),y=pt+(H-pt-pb)-h;
    b+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+h.toFixed(1)+'" rx="3" fill="'+color+'"/>';
    if(showVal) b+='<text x="'+(x+bw/2).toFixed(1)+'" y="'+(y-4).toFixed(1)+'" text-anchor="middle" font-size="10" fill="#c3d2e4">¥'+Math.round(v/1000).toLocaleString()+'k</text>';
    if(i%labelEvery===0) b+='<text x="'+(x+bw/2).toFixed(1)+'" y="'+(H-pb+15)+'" text-anchor="middle" font-size="11" fill="#aebccd">'+esc(lab)+'</text>';});
  return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="max-width:680px">'+b+'</svg>';
}
function deptMatrix(stores, byStore, exps, items, pay){
  const cols=stores.concat(['本部','全社合計']);
  const blank=()=>{const o={};cols.forEach(c=>o[c]=0);return o;};
  const deptOf=(it,v)=>{const t=(it||'')+' '+(v||'');for(const s of stores)if(t.includes(s))return s;return '本部';};
  const salesTotal=byStore.reduce((s,x)=>s+x[1],0)||1;
  const rev=blank(); byStore.forEach(x=>rev[x[0]]=x[1]); rev['全社合計']=byStore.reduce((s,x)=>s+x[1],0);
  let cogsTotal=0; const sga=[], sgaMap={};
  exps.forEach(e=>{ if((items[e.code]||[])[1]==='売上原価'){cogsTotal+=e.a;return;}
    const n=(items[e.code]||[e.code])[0]; let row=sgaMap[n]; if(!row){row=blank();sgaMap[n]=row;sga.push([n,row]);}
    const d=deptOf(e.it,e.v); row[d]+=e.a; row['全社合計']+=e.a; });
  let pr=sgaMap['給与手当']; if(!pr){pr=blank();sgaMap['給与手当']=pr;sga.unshift(['給与手当',pr]);}
  pay.forEach(r=>{pr[r[2]]=(pr[r[2]]||0)+(+r[6]||0);pr['全社合計']+=(+r[6]||0);});
  const cogs=blank(); stores.forEach(s=>cogs[s]=Math.round(cogsTotal*(rev[s]||0)/salesTotal)); cogs['全社合計']=cogsTotal;
  const gross=blank(); cols.forEach(c=>gross[c]=rev[c]-cogs[c]);
  sga.sort((a,b)=>(a[0]==='給与手当'?-1:b[0]==='給与手当'?1:b[1]['全社合計']-a[1]['全社合計']));
  const sgaTot=blank(); cols.forEach(c=>sga.forEach(x=>sgaTot[c]+=x[1][c]));
  const op=blank(); cols.forEach(c=>op[c]=gross[c]-sgaTot[c]);
  const R=d=>cols.map(c=>Math.round(d[c]));
  const rows=[['売上高'].concat(R(rev)),['売上原価(仕入・按分)'].concat(R(cogs)),['売上総利益'].concat(R(gross))]
    .concat(sga.map(x=>[x[0]].concat(R(x[1]))))
    .concat([['販管費計'].concat(R(sgaTot)),['営業利益'].concat(R(op))]);
  return {cols,rows};
}
function matrixHtml(m){
  const cell=(v,emph)=>'<td'+(v<0?' style="color:#ff8a8a"':'')+'>'+(emph?'<b>'+yen(v)+'</b>':yen(v))+'</td>';
  const th=m.cols.map(c=>'<th>'+c+'</th>').join('');
  const body=m.rows.map(r=>{const emph=['売上高','売上総利益','営業利益'].includes(r[0]);
    const cls=['売上総利益','営業利益'].includes(r[0])?' class="hl"':'';
    return '<tr'+cls+'><td class="l">'+r[0]+'</td>'+r.slice(1).map(v=>cell(v,emph)).join('')+'</tr>';}).join('');
  return '<div style="overflow-x:auto"><table class="mx"><tr><th class="l">勘定科目</th>'+th+'</tr>'+body+'</table></div>'
    +'<p class="muted">※仕入は売上比で店舗按分。本部＝管理部門(費用のみ)。転記なし・自動集計。</p>';
}
const PALETTE=['#5aa2e6','#37c39a','#f5a524','#ff6b81','#9b7ede','#4fc3e0','#e0a24a','#7fca6b','#e07aa0','#c9863f','#6f9fce','#d9b34a','#8fd0ff','#ff9f7a'];
const WDN=['月','火','水','木','金','土','日'], HOL=new Set(MASTERS.holidays);
function svgDaily(rows){  // rows: [[date,amt]]
  const W=720,H=210,pl=48,pb=28,pt=14,pr=8,plotH=H-pt-pb;
  const mx=Math.max(...rows.map(r=>r[1]),1),n=rows.length||1,gap=(W-pl-pr)/n,bw=Math.min(18,gap*0.72);
  const COL={w:'#5aa2e6',sat:'#3fb7d6',sun:'#ff6b81',hol:'#f5a524'},LC={w:'#9fb0c7',sat:'#7fd6ec',sun:'#ff9db0',hol:'#ffca7a'};
  let g='';
  for(let i=0;i<3;i++){const y=pt+plotH*(1-i/2);
    g+='<line x1="'+pl+'" y1="'+y.toFixed(1)+'" x2="'+(W-pr)+'" y2="'+y.toFixed(1)+'" stroke="rgba(255,255,255,.08)"/>'
     +'<text x="'+(pl-6)+'" y="'+(y+4).toFixed(1)+'" text-anchor="end" font-size="10" fill="#8296ad">¥'+Math.round(mx*i/2/1000).toLocaleString()+'k</text>';}
  rows.forEach(([d,a],i)=>{const wd=new Date(d+'T00:00:00').getDay(),jw=(wd+6)%7;
    const t=HOL.has(d)?'hol':(wd===6?'sat':(wd===0?'sun':'w'));
    const x=pl+gap*i+(gap-bw)/2,h=plotH*(a/mx),y=pt+plotH-h;
    g+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+h.toFixed(1)+'" rx="2" fill="'+COL[t]+'"><title>'+d+'('+WDN[jw]+') '+yen(a)+'</title></rect>'
     +'<text x="'+(x+bw/2).toFixed(1)+'" y="'+(H-pb+12)+'" text-anchor="middle" font-size="8.5" fill="'+LC[t]+'">'+(+d.slice(8))+'</text>';});
  return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="max-width:100%">'+g+'</svg>';
}
function svgHstack(segs){const W=720,H=40,total=segs.reduce((s,x)=>s+x[1],0)||1;let x=0,g='';
  segs.forEach(([n,a,c])=>{const w=W*a/total;
    g+='<rect x="'+x.toFixed(1)+'" y="6" width="'+Math.max(0.5,w).toFixed(1)+'" height="28" fill="'+c+'"><title>'+n+' '+yen(a)+'（'+(a/total*100).toFixed(1)+'%）</title></rect>';x+=w;});
  return '<svg viewBox="0 0 '+W+' '+H+'" width="100%" style="max-width:100%">'+g+'</svg>';}
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
      const hay=(v+' '+it).toLowerCase(); let code='MISC';
      for(const [pat,c] of MASTERS.rules){ if(hay.includes(pat.toLowerCase())){code=c;break;} }
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
  const mtx=deptMatrix(stores.map(s=>s[0]), stores, exps, items, pay);
  links+=dlLink('11_部門別損益マトリクス.csv',csvOf(['勘定科目'].concat(mtx.cols),mtx.rows));
  const dayFull=Object.keys(byDay).sort().map(d=>[d,byDay[d]]);
  const costEntries=Object.entries(byItem).concat([['給与手当',payTotal]]).sort((a,b)=>b[1]-a[1]);
  const totCost=costEntries.reduce((s,x)=>s+x[1],0)||1;
  const segs=costEntries.map(([n,a],i)=>[n,a,PALETTE[i%PALETTE.length]]);
  const lgd=segs.map(([n,a,c])=>'<span class="lg"><i style="background:'+c+'"></i>'+n+' '+yen(a)+'（'+(a/totCost*100).toFixed(1)+'%）</span>').join('');
  const dayLgd='<span class="lg"><i style="background:#5aa2e6"></i>平日</span><span class="lg"><i style="background:#3fb7d6"></i>土</span><span class="lg"><i style="background:#ff6b81"></i>日</span><span class="lg"><i style="background:#f5a524"></i>祝</span>';
  document.getElementById('result').innerHTML=
   '<div class="kpis">'+kpi.map(([k,v])=>'<div class="kpi"><div class="v">'+v+'</div><div class="k">'+k+'</div></div>').join('')+'</div>'
   +'<div class="grid2">'
     +'<div class="card"><h3>部門別 損益マトリクス（一目で全社／店舗／管理部門）</h3>'+matrixHtml(mtx)+'</div>'
     +'<div class="col">'
       +'<div class="card"><h3>日次売上（土日祝を色分け）</h3><div class="lgd">'+dayLgd+'</div>'+svgDaily(dayFull)+'</div>'
       +'<div class="card"><h3>経費・費用の内訳（積み上げ）</h3>'+svgHstack(segs)+'<div class="lgd">'+lgd+'</div></div>'
       +'<div class="card"><h3>店舗別 売上</h3>'+svgBars(stores,'#37c39a')+'</div>'
     +'</div>'
   +'</div>'
   +'<div class="card"><h3>分析コメント（自動生成）</h3><ul>'+comments.map(c=>'<li>'+c+'</li>').join('')+'</ul></div>'
   +'<p style="margin:.6em 0 .2em">帳票（クリックで保存）:</p>'+links
   +'<p class="muted">体験版はここまで（CSV・Excel対応／保存されません）。毎月“貯める”・PDF取込・Excel形式の帳票は、本物の城で。</p>';
}
refresh();
</script></body></html>"""

os.makedirs(J(BASE, "docs"), exist_ok=True)
html = HTML.replace("__DATA__", json.dumps(DATA, ensure_ascii=False))
with open(J(BASE, "docs", "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("docs/index.html 生成: %.1f KB" % (os.path.getsize(J(BASE, "docs", "index.html")) / 1024))
