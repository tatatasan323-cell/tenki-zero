# -*- coding: utf-8 -*-
"""tenki-zero ─ 受付画面（城の玄関ホール）

使い方:
    python app.py
    → ブラウザが開く（http://127.0.0.1:8760）。経費・売上・勤怠をアップロードして「締める」を押すだけ。

- 完全ローカル: 127.0.0.1のみで待ち受け。データはこのPCから一歩も出ない
- 何度でもアップロード可。同じ内容のファイルは自動でスキップ（内容ハッシュで判定）
- 行レベルの重複（同じ日の同じ数字）も close.py 側で自動排除
- Excel(.xlsx)/PDFの請求書もそのまま投入可（requirements.txt の借り物を入れた場合）
"""
import os, io, sys, json, base64, hashlib, re, socket, webbrowser
import urllib.request, importlib, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import close as tz

BASE = os.path.dirname(os.path.abspath(__file__))
J = os.path.join
PORT = 8760
TYPES = {"sales": "売上", "expenses": "経費", "attendance": "勤怠"}

def inbox_hashes():
    """inbox内の全ファイルの内容ハッシュ（既存ファイルも対象＝同一内容の再投入を確実に検出）"""
    hs = {}
    for t in TYPES:
        d = J(BASE, "inbox", t)
        for f in os.listdir(d):
            if f.startswith("."):
                continue
            p = J(d, f)
            if os.path.isfile(p):
                hs[hashlib.sha1(open(p, "rb").read()).hexdigest()] = f
    return hs

def list_files():
    out = {}
    for t in TYPES:
        d = J(BASE, "inbox", t)
        out[t] = [{"name": f, "kb": round(os.path.getsize(J(d, f)) / 1024, 1)}
                  for f in sorted(os.listdir(d)) if not f.startswith(".")]
    return out

def months_available():
    ms = set()
    for t in TYPES:
        d = J(BASE, "inbox", t)
        for f in os.listdir(d):
            for m in re.findall(r"(\d{4})[-_/年]?(\d{2})", f):
                ms.add("%s-%s" % m)
    return sorted(ms, reverse=True)

PAGE = """<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>tenki-zero 受付</title><style>
:root{--glass:rgba(16,25,44,.66)}
body{margin:0;font-family:"Segoe UI","Yu Gothic UI",Meiryo,sans-serif;color:#e9f0fa;line-height:1.6;
 background:linear-gradient(165deg,#0a1020,#0c162b 55%,#0a1224);min-height:100vh}
.wrap{max-width:1040px;margin:0 auto;padding:22px 18px}
h1{font-size:1.5rem;font-weight:800;background:linear-gradient(112deg,#fff,#8fd0ff 55%,#ffd67a);
 -webkit-background-clip:text;background-clip:text;color:transparent;margin:.2em 0}
.sub{color:#b6cae2;font-size:.88rem;margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.card{background:var(--glass);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:16px 18px;margin:12px 0}
h3{font-size:1rem;color:#eaf3ff;border-left:4px solid #5aa2e6;padding-left:10px;margin:.1em 0 .5em}
.zone{border:2px dashed rgba(140,180,230,.4);border-radius:13px;padding:18px;text-align:center;color:#aec1d8;
 cursor:pointer;background:rgba(10,18,36,.4);transition:.15s;font-size:.9rem}
.zone:hover,.zone.hover{border-color:#5aa2e6;background:rgba(90,160,240,.1)}
.zone b{color:#8fd0ff}
.zone.exp{border-color:rgba(245,165,36,.45)} .zone.exp b{color:#ffd27a}
.zone.att{border-color:rgba(120,220,170,.45)} .zone.att b{color:#8fe6bb}
.list{font-size:.8rem;color:#9fb0c7;margin-top:8px;max-height:130px;overflow-y:auto}
.list div{padding:1px 0;border-bottom:1px dashed rgba(255,255,255,.06)}
.btn{background:linear-gradient(118deg,#3d8fe6,#37c39a);color:#fff;border:none;border-radius:11px;
 padding:11px 26px;font-size:1rem;font-weight:700;cursor:pointer;font-family:inherit;box-shadow:0 6px 18px rgba(60,150,230,.35)}
.btn:hover{filter:brightness(1.08)}
select{font-family:inherit;font-size:1rem;padding:8px 12px;border-radius:9px;border:1px solid rgba(255,255,255,.2);
 background:#0d1830;color:#e9f0fa;margin-right:12px}
.kpis{display:flex;gap:12px;flex-wrap:wrap;margin-top:10px}
.kpi{flex:1;min-width:130px;background:linear-gradient(158deg,rgba(74,150,235,.22),rgba(13,22,42,.66));
 border:1px solid rgba(255,255,255,.1);border-radius:13px;padding:10px 14px}
.kpi .v{font-size:1.15rem;font-weight:800}.kpi .k{font-size:.72rem;color:#9fb2c9}
a.dl{display:inline-block;margin:3px 6px 3px 0;padding:6px 13px;border:1px solid rgba(143,208,255,.4);
 border-radius:9px;color:#8fd0ff;text-decoration:none;font-size:.84rem}
a.dl:hover{background:rgba(90,160,240,.12)}
.muted{color:#8ea1b8;font-size:.8rem}
#log{font-size:.83rem;color:#b9ccdf;margin-top:8px;max-height:110px;overflow-y:auto}
.ok{color:#7fe0ae}.skip{color:#ffce7a}.err{color:#ff8a8a}
</style></head><body><div class="wrap">
<h1>tenki-zero ─ 受付</h1>
<div class="sub">月末までに、届いた書類をここへ放り込んでおくだけ。何度でも追加OK・<b>同じものは自動でスキップ</b>されます。データはこのPCから出ません。</div>

<div class="grid">
  <div class="card"><h3>経費（請求書）</h3>
    <div class="zone exp" data-type="expenses"><b>ここに放り込む</b><br>正規化CSV / バラバラ請求書CSV<br>Excel(.xlsx) / PDF もOK</div>
    <div class="list" id="list-expenses"></div></div>
  <div class="card"><h3>売上</h3>
    <div class="zone" data-type="sales"><b>ここに放り込む</b><br>売上集計ツールの「連携用CSV」<br>日次売上CSV / Excel もOK</div>
    <div class="list" id="list-sales"></div></div>
  <div class="card"><h3>勤怠</h3>
    <div class="zone att" data-type="attendance"><b>ここに放り込む</b><br>勤怠システムのエクスポートCSV<br>(SJISのままでOK)</div>
    <div class="list" id="list-attendance"></div></div>
</div>

<div class="card">
  <h3>月次を締める</h3>
  <select id="month"></select>
  <button class="btn" onclick="doClose()">締める ─ 帳票を出力</button>
  <span class="muted">　CSV・Excel・役員ダッシュボード(HTML)が一括で出ます</span>
  <div id="result"></div>
</div>

<div class="card"><h3>手書きの書類は？</h3>
  <p class="muted" style="font-size:.86rem">スマホで撮影して、AIに「<b style="color:#ffd27a">この表をCSVにして</b>」と頼んでください。出てきたCSVを、上の受け箱へ ――
  それがいちばん速くて確実です（この城の入口は、いつもAIです）。</p></div>

<div id="log"></div>
<input type="file" id="picker" multiple hidden>
</div><script>
let curType=null;
const log=(m,c)=>{const d=document.getElementById('log');d.innerHTML='<div class="'+(c||'')+'">'+m+'</div>'+d.innerHTML;};
async function refresh(){
  const r=await fetch('/api/files').then(r=>r.json());
  for(const t in r.files){
    document.getElementById('list-'+t).innerHTML=r.files[t].map(f=>'<div>'+f.name+'　<span style="opacity:.6">'+f.kb+'KB</span></div>').join('')||'<div style="opacity:.5">（まだありません）</div>';
  }
  const sel=document.getElementById('month'); const cur=sel.value;
  sel.innerHTML=r.months.map(m=>'<option>'+m+'</option>').join('')||'<option>2026-05</option>';
  if(cur) sel.value=cur;
}
async function sendFiles(files){
  for(const f of files){
    const b64=await new Promise(res=>{const rd=new FileReader();rd.onload=()=>res(rd.result.split(',')[1]);rd.readAsDataURL(f);});
    const r=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({type:curType,name:f.name,b64})}).then(r=>r.json());
    log((r.saved?'✔ 受付: ':'― スキップ(同じ内容): ')+f.name, r.saved?'ok':'skip');
  }
  refresh();
}
document.querySelectorAll('.zone').forEach(z=>{
  z.onclick=()=>{curType=z.dataset.type;document.getElementById('picker').click();};
  ['dragover','dragenter'].forEach(ev=>z.addEventListener(ev,e=>{e.preventDefault();z.classList.add('hover');}));
  z.addEventListener('dragleave',e=>z.classList.remove('hover'));
  z.addEventListener('drop',e=>{e.preventDefault();z.classList.remove('hover');curType=z.dataset.type;sendFiles(e.dataTransfer.files);});
});
document.getElementById('picker').onchange=e=>sendFiles(e.target.files);
async function doClose(){
  const m=document.getElementById('month').value;
  document.getElementById('result').innerHTML='<p class="muted">締めています…</p>';
  let r;
  try{
    r=await fetch('/api/close',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({month:m})}).then(r=>r.json());
  }catch(e){
    document.getElementById('result').innerHTML='<p class="err">サーバと通信できませんでした ─ 受付ウィンドウ(黒い画面)を閉じて、起動.bat をもう一度ダブルクリックしてください</p>';return;
  }
  if(!r.ok){document.getElementById('result').innerHTML='<p class="err">'+r.error+'</p>';return;}
  const yen=n=>'¥'+n.toLocaleString('ja-JP');
  let h='<div class="kpis">'
    +'<div class="kpi"><div class="v">'+yen(r.sales)+'</div><div class="k">売上高</div></div>'
    +'<div class="kpi"><div class="v">'+yen(r.gross)+'</div><div class="k">売上総利益 ('+r.gross_rate+'%)</div></div>'
    +'<div class="kpi"><div class="v">'+yen(r.op)+'</div><div class="k">営業利益 ('+r.op_rate+'%)</div></div>'
    +'<div class="kpi"><div class="v">'+r.misc+' 件</div><div class="k">未分類（要ルール追加）</div></div></div>';
  const d=r.dedup;
  if(d.sales_replaced+d.expenses_skipped+d.attendance_replaced>0)
    h+='<p class="muted">重複を自動排除しました ─ 売上上書き'+d.sales_replaced+'件／経費スキップ'+d.expenses_skipped+'件／勤怠上書き'+d.attendance_replaced+'件</p>';
  h+='<p style="margin:.6em 0 .2em">出力（クリックで保存／ダッシュボードは開く）:</p>'
    +r.outputs.map(f=>'<a class="dl" href="/out/'+r.month+'/'+encodeURIComponent(f)+'" '+(f.endsWith('.html')?'target="_blank"':'download')+'>'+f+'</a>').join('');
  if(r.warnings.length) h+='<p class="err" style="font-size:.82rem">'+r.warnings.join('<br>')+'</p>';
  document.getElementById('result').innerHTML=h;
}
refresh();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 標準の逐次ログは抑制
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode("utf-8"))

    def do_GET(self):
        if self.path == "/":
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/files":
            return self._send(200, json.dumps({"files": list_files(), "months": months_available()},
                                              ensure_ascii=False))
        m = re.match(r"^/out/(\d{4}-\d{2})/(.+)$", self.path)
        if m:
            import urllib.parse
            name = urllib.parse.unquote(m.group(2))
            p = J(BASE, "out", m.group(1), name)
            if os.path.isfile(p) and os.path.abspath(p).startswith(J(BASE, "out")):
                ct = "text/html; charset=utf-8" if p.endswith(".html") else "application/octet-stream"
                extra = {} if p.endswith(".html") else {
                    "Content-Disposition": "attachment; filename*=UTF-8''" + urllib.parse.quote(name)}
                return self._send(200, open(p, "rb").read(), ct, extra)
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return self._send(400, json.dumps({"ok": False, "error": "bad request"}))
        if self.path == "/api/upload":
            t = req.get("type")
            if t not in TYPES:
                return self._send(400, json.dumps({"ok": False, "error": "種別が不明です"}))
            name = os.path.basename(req.get("name", "upload.csv"))
            data = base64.b64decode(req.get("b64", ""))
            h = hashlib.sha1(data).hexdigest()
            hs = inbox_hashes()
            if h in hs:                                   # 同一内容 → 自動スキップ
                return self._send(200, json.dumps({"ok": True, "saved": False, "dup_of": hs[h]},
                                                  ensure_ascii=False))
            p = J(BASE, "inbox", t, name)
            stem, ext = os.path.splitext(name)
            k = 2
            while os.path.exists(p):                      # 同名・別内容 → 連番で共存
                p = J(BASE, "inbox", t, "%s_%d%s" % (stem, k, ext))
                k += 1
            open(p, "wb").write(data)
            return self._send(200, json.dumps({"ok": True, "saved": True}, ensure_ascii=False))
        if self.path == "/api/close":
            month = req.get("month", "")
            if not re.match(r"^\d{4}-\d{2}$", month):
                return self._send(400, json.dumps({"ok": False, "error": "月の形式が不正です"}))
            try:
                importlib.reload(tz)   # 受付を立ち上げたまま close.py が更新されても最新で締める
                r = tz.close(month)
                r["outdir"] = os.path.basename(r.get("outdir", ""))
            except Exception as e:
                traceback.print_exc()
                return self._send(200, json.dumps(
                    {"ok": False, "error": "締め処理でエラー: %s ─ 受付ウィンドウを閉じて 起動.bat をやり直してください" % e},
                    ensure_ascii=False))
            return self._send(200, json.dumps(r, ensure_ascii=False))
        return self._send(404, json.dumps({"error": "not found"}))

class Srv(ThreadingHTTPServer):
    allow_reuse_address = False           # Windowsの“二重bind”を防ぐ(使用中なら素直に失敗させる)

def listening(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0

def is_tenki(port):
    try:
        html = urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=1).read(4096).decode("utf-8", "ignore")
        return "tenki-zero" in html
    except Exception:
        return False

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    srv = None
    for port in range(PORT, PORT + 10):
        if listening(port):
            if is_tenki(port):            # すでに受付が起動中 → 新しく立てずにブラウザで開くだけ
                url = "http://127.0.0.1:%d" % port
                print("受付はすでに起動しています → ブラウザで開きます:", url)
                webbrowser.open(url)
                sys.exit(0)
            print("ポート %d は別のアプリが使用中 → 次を試します" % port)
            continue
        try:
            srv = Srv(("127.0.0.1", port), H)
            break
        except OSError:
            continue
    if srv is None:
        print("空きポートが見つかりませんでした。他のアプリを閉じてから、もう一度どうぞ。")
        sys.exit(1)
    url = "http://127.0.0.1:%d" % port
    print("tenki-zero 受付を開きます:", url, "（終了は Ctrl+C）")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    srv.serve_forever()
