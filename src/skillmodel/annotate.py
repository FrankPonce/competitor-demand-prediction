"""Local verification page for the gold set (Sprint 11).

    python -m src.skillmodel.annotate        → open http://localhost:8800

Shows each pre-labelled sentence with its skill spans highlighted. Click a span to remove it, select text to add a
span, Enter (or "Correct") to confirm and move on. Every change is saved immediately to
data/skillmodel/gold.jsonl, so you can stop and continue later. Local only: binds to 127.0.0.1.
"""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "skillmodel"
PRE, GOLD = D / "gold_prelabels.jsonl", D / "gold.jsonl"
PORT = 8800


def load() -> list[dict]:
    pre = [json.loads(l) for l in PRE.open(encoding="utf-8")]
    if GOLD.exists():
        done = {r["id"]: r for r in map(json.loads, GOLD.open(encoding="utf-8"))}
        pre = [done.get(r["id"], r) for r in pre]
    return pre


def save(rows: list[dict]) -> None:
    tmp = GOLD.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(GOLD)


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gold set · verify</title><link rel="icon" href="data:,">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1b222c;--grid:#21262d;--axis:#30363d;--text:#e6edf3;--t2:#9198a1;--muted:#6e7681;--acc:#58a6ff;--ok:#3fb950;--warn:#d29922}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 Inter,system-ui,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:28px 20px 60px}
header{display:flex;align-items:center;gap:16px;flex-wrap:wrap}h1{font-size:20px;margin:0;letter-spacing:-.02em}
.bar{flex:1;min-width:200px;height:8px;background:var(--grid);border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,#b95115,#9c7bd2,#2d6ac1,#5ea529)}
.count{font:13px JetBrains Mono,monospace;color:var(--t2)}
.card{background:var(--panel);border:1px solid var(--grid);border-radius:14px;padding:26px;margin-top:22px}
.meta{font:12px JetBrains Mono,monospace;color:var(--muted);display:flex;gap:14px;flex-wrap:wrap}
.meta b{color:var(--t2);font-weight:500}.st{padding:1px 8px;border-radius:999px;border:1px solid var(--axis)}
.st.verified{color:#7ee2a8;border-color:rgba(63,185,80,.45)}
#sent{font-size:22px;line-height:1.75;margin:18px 0 6px;user-select:text;cursor:text}
mark{background:rgba(88,166,255,.18);color:var(--text);border-bottom:2px solid var(--acc);border-radius:4px;padding:1px 2px;cursor:pointer}
mark:hover{background:rgba(248,81,73,.22);border-color:#f85149;text-decoration:line-through}
.spans{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;min-height:32px}
.chip{font:13px JetBrains Mono,monospace;background:var(--panel2);border:1px solid var(--axis);border-radius:999px;padding:4px 10px;cursor:pointer}
.chip:hover{border-color:#f85149;color:#ffa198}.chip::after{content:" ×";color:var(--muted)}
.none{color:var(--muted);font-size:13px}
.actions{display:flex;gap:10px;margin-top:22px;flex-wrap:wrap}
button{font:500 14px Inter,sans-serif;border-radius:10px;padding:9px 16px;cursor:pointer;border:1px solid var(--axis);background:transparent;color:var(--text)}
button.primary{background:var(--ok);border-color:var(--ok);color:#0d1117}button:hover{filter:brightness(1.15)}
.help{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:22px}
.help div{background:var(--panel);border:1px solid var(--grid);border-radius:14px;padding:16px 18px;font-size:13.5px;color:var(--t2)}
.help h3{margin:0 0 6px;font-size:13px;color:var(--text)}.help ul{margin:0;padding-left:18px}
kbd{font:12px JetBrains Mono,monospace;border:1px solid var(--axis);border-radius:5px;padding:0 5px;color:var(--text)}
.toast{position:fixed;bottom:18px;right:18px;background:var(--panel2);border:1px solid var(--axis);border-radius:10px;padding:8px 12px;font:12px JetBrains Mono,monospace;opacity:0;transition:opacity .3s}
.toast.show{opacity:1}
@media(max-width:700px){.help{grid-template-columns:1fr}#sent{font-size:19px}}
</style></head><body><div class="wrap">
<header><h1>Gold set · verify skill spans</h1><div class="bar"><i id="prog"></i></div><span class="count" id="count"></span></header>
<div class="card"><div class="meta" id="meta"></div><div id="sent"></div><div class="spans" id="spans"></div>
<div class="actions"><button class="primary" id="ok">Correct <kbd>Enter</kbd></button><button id="prev">← Back <kbd>←</kbd></button>
<button id="skip">Skip <kbd>→</kbd></button><button id="clear">Remove all spans</button><button id="next-un">Next unverified</button></div></div>
<div class="help"><div><h3>How</h3><ul><li><b>Remove</b> a span: click it in the sentence (or its chip).</li><li><b>Add</b> a span: select the text with the mouse; it is added on release.</li>
<li><b>Confirm</b> with <kbd>Enter</kbd>. Everything saves instantly; close the tab any time.</li></ul></div>
<div><h3>A skill is…</h3><ul><li>a tool, language, method, domain or certification the candidate needs or uses</li>
<li><b>not</b> a team, customer, product as context, trait, years or degree</li><li>the shortest complete name; each list item separately</li></ul></div></div>
</div><div class="toast" id="toast">saved</div>
<script>
let rows=[],i=0;
const $=s=>document.querySelector(s), esc=s=>s.replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
async function api(method,body){const r=await fetch("/api",{method,headers:{"Content-Type":"application/json"},body:body&&JSON.stringify(body)});return r.json();}
function toast(t){const e=$("#toast");e.textContent=t;e.classList.add("show");clearTimeout(e._t);e._t=setTimeout(()=>e.classList.remove("show"),900);}
async function persist(msg){await api("POST",rows[i]);toast(msg||"saved");}
function render(){
  const r=rows[i], v=rows.filter(x=>x.status==="verified").length;
  $("#count").textContent=`${i+1} / ${rows.length} · ${v} verified`; $("#prog").style.width=(100*v/rows.length)+"%";
  $("#meta").innerHTML=`<b>${esc(r.company)}</b><span>${esc(r.role_family||"")}</span><span>${r.id}</span><span class="st ${r.status}">${r.status}</span>`;
  const sp=[...r.spans].sort((a,b)=>a.start-b.start); let h="",p=0;
  sp.forEach((s,k)=>{h+=esc(r.text.slice(p,s.start))+`<mark data-k="${r.spans.indexOf(s)}">${esc(r.text.slice(s.start,s.end))}</mark>`;p=s.end;});
  $("#sent").innerHTML=h+esc(r.text.slice(p));
  $("#spans").innerHTML=r.spans.length?sp.map(s=>`<span class="chip" data-k="${r.spans.indexOf(s)}">${esc(s.text)}</span>`).join(""):`<span class="none">No skill spans in this sentence</span>`;
}
function offsetIn(node,off){ // character offset of (node, off) within #sent
  const root=$("#sent"); let n=0; const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  while(w.nextNode()){ if(w.currentNode===node) return n+off; n+=w.currentNode.textContent.length; } return -1; }
$("#sent").addEventListener("mouseup",async e=>{
  const sel=getSelection(); if(!sel.rangeCount||sel.isCollapsed){ const m=e.target.closest("mark"); if(m){rows[i].spans.splice(+m.dataset.k,1);render();await persist("span removed");} return; }
  const rg=sel.getRangeAt(0); let a=offsetIn(rg.startContainer,rg.startOffset), b=offsetIn(rg.endContainer,rg.endOffset); sel.removeAllRanges();
  if(a<0||b<0) return; if(a>b)[a,b]=[b,a]; const t=rows[i].text;
  while(a<b&&/[\s.,;:()]/.test(t[a]))a++; while(b>a&&/[\s.,;:()]/.test(t[b-1]))b--; // trim spaces and punctuation
  if(b<=a) return;
  rows[i].spans=rows[i].spans.filter(s=>s.end<=a||s.start>=b); rows[i].spans.push({start:a,end:b,text:t.slice(a,b)}); rows[i].spans.sort((x,y)=>x.start-y.start);
  render(); await persist("span added");
});
$("#spans").addEventListener("click",async e=>{const c=e.target.closest(".chip"); if(!c)return; rows[i].spans.splice(+c.dataset.k,1); render(); await persist("span removed");});
async function confirm(){rows[i].status="verified"; await persist("verified ✓"); if(i<rows.length-1)i++; render();}
$("#ok").onclick=confirm; $("#prev").onclick=()=>{if(i>0)i--;render();}; $("#skip").onclick=()=>{if(i<rows.length-1)i++;render();};
$("#clear").onclick=async()=>{rows[i].spans=[];render();await persist("cleared");};
$("#next-un").onclick=()=>{const j=rows.findIndex(r=>r.status!=="verified"); if(j>=0){i=j;render();} else toast("all verified 🎉");};
addEventListener("keydown",e=>{ if(e.key==="Enter"){e.preventDefault();confirm();} else if(e.key==="ArrowLeft"){if(i>0)i--;render();} else if(e.key==="ArrowRight"){if(i<rows.length-1)i++;render();} });
api("GET").then(d=>{rows=d; const j=rows.findIndex(r=>r.status!=="verified"); i=j>=0?j:0; render();});
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    rows: list[dict] = []

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api"):
            self._send(200, json.dumps(H.rows, ensure_ascii=False).encode(), "application/json")
        else:
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")

    def do_POST(self):
        row = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        ids = {r["id"]: k for k, r in enumerate(H.rows)}
        if row.get("id") not in ids:
            self._send(400, b'{"error":"unknown id"}', "application/json")
            return
        text = H.rows[ids[row["id"]]]["text"]  # the sentence itself can never be edited from the page
        spans = [{"start": int(s["start"]), "end": int(s["end"]), "text": text[int(s["start"]):int(s["end"])]}
                 for s in row.get("spans", []) if 0 <= int(s["start"]) < int(s["end"]) <= len(text)]
        H.rows[ids[row["id"]]] = {**H.rows[ids[row["id"]]], "spans": sorted(spans, key=lambda s: s["start"]),
                                  "status": "verified" if row.get("status") == "verified" else H.rows[ids[row["id"]]]["status"]}
        save(H.rows)
        self._send(200, b'{"ok":true}', "application/json")


def main() -> None:
    H.rows = load()
    if not GOLD.exists():
        save(H.rows)
    v = sum(r["status"] == "verified" for r in H.rows)
    print(f"{v}/{len(H.rows)} verified · saving to {GOLD.relative_to(ROOT)} · http://localhost:{PORT}  (Ctrl+C to stop)")
    webbrowser.open(f"http://localhost:{PORT}")
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
