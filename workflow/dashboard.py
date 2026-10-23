#!/usr/bin/env python3
"""
dashboard.py — render a LOCAL, self-contained HTML overview of findings.

Reads the engagement JSON and produces a single static HTML file (data embedded
at generation time) — no server, no network, works offline by opening the file
in a browser. It is a read-only snapshot.

PRIVACY: the output contains your findings (targets, evidence, PoCs). It is
written under the engagements base dir (default ~/.bb-engagements/, outside the
git repo) and must NOT be committed or shared. Regenerate it whenever you want a
fresh view.
"""
from __future__ import annotations

import json
import os
import time

from state import Engagement, SEVERITIES, STATUSES


def collect(base: str):
    """Aggregate every engagement under base into dashboard rows."""
    base = os.path.expanduser(base)
    engagements, findings = [], []
    if not os.path.isdir(base):
        return engagements, findings
    for name in sorted(os.listdir(base)):
        if not os.path.isfile(os.path.join(base, name, "state.json")):
            continue
        eng = Engagement(base, name)
        sc = eng.scope
        engagements.append({
            "name": name, "phase": eng.state.get("phase", ""),
            "in_scope": sc.in_scope, "out_of_scope": sc.out_of_scope,
            "findings": len(eng.state.get("findings", [])),
        })
        for f in eng.state.get("findings", []):
            row = dict(f)
            row["engagement"] = name
            findings.append(row)
    return engagements, findings


def render(base: str) -> str:
    engagements, findings = collect(base)
    data = json.dumps({"engagements": engagements, "findings": findings,
                       "severities": SEVERITIES, "statuses": STATUSES,
                       "generated": time.strftime("%Y-%m-%d %H:%M:%S")},
                      indent=0)
    # never let embedded data close the <script> early
    data = data.replace("</", "<\\/")
    return _TEMPLATE.replace("/*DATA*/", data)


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bug-bounty findings</title>
<style>
  :root {
    --bg:#f6f7f9; --panel:#fff; --ink:#1a1d21; --muted:#5b6470; --line:#e3e6ea;
    --accent:#2f6fed;
    --info:#6b7280; --low:#2f9e5f; --medium:#c9820a; --high:#e0602a; --critical:#d23b3b;
    --candidate:#6b7280; --confirmed:#2f6fed; --reported:#7a4fd0; --duplicate:#9aa2ad; --invalid:#c0c4cc;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg:#14171a; --panel:#1c2024; --ink:#e7eaee; --muted:#9aa2ad; --line:#2a2f35; --accent:#5a8bff;
    }
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
    font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  .wrap { max-width:1200px; margin:0 auto; padding:24px 16px 64px; }
  h1 { font-size:20px; margin:0 0 2px; }
  .sub { color:var(--muted); font-size:12px; margin-bottom:20px; }
  .cards { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:18px; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:10px;
    padding:12px 14px; min-width:110px; }
  .card .n { font-size:22px; font-weight:650; }
  .card .l { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.04em; }
  .controls { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:14px; align-items:center; }
  select,input[type=search] { background:var(--panel); color:var(--ink);
    border:1px solid var(--line); border-radius:8px; padding:7px 9px; font-size:13px; }
  input[type=search] { flex:1; min-width:180px; }
  table { width:100%; border-collapse:collapse; background:var(--panel);
    border:1px solid var(--line); border-radius:10px; overflow:hidden; }
  th,td { text-align:left; padding:9px 11px; border-bottom:1px solid var(--line); vertical-align:top; }
  th { font-size:11px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted);
    cursor:pointer; user-select:none; white-space:nowrap; }
  tr.row { cursor:pointer; }
  tr.row:hover { background:rgba(127,127,127,.06); }
  td.tgt { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; word-break:break-all; }
  .pill { display:inline-block; padding:1px 8px; border-radius:999px; font-size:11px;
    font-weight:600; color:#fff; white-space:nowrap; }
  .warn { color:var(--critical); font-weight:700; }
  .detail td { background:rgba(127,127,127,.04); }
  .detail pre { white-space:pre-wrap; word-break:break-word; margin:6px 0; padding:8px 10px;
    background:rgba(127,127,127,.08); border-radius:8px; font-size:12px; }
  .kv { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.04em; margin-top:8px; }
  .empty { color:var(--muted); padding:24px; text-align:center; }
  .hint { color:var(--muted); font-size:11px; margin-top:10px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Bug-bounty findings</h1>
  <div class="sub" id="meta"></div>
  <div class="cards" id="cards"></div>
  <div class="controls">
    <select id="f-eng"><option value="">all engagements</option></select>
    <select id="f-status"><option value="">all statuses</option></select>
    <select id="f-sev"><option value="">all severities</option></select>
    <input type="search" id="f-q" placeholder="search title / target / class / notes…">
  </div>
  <table>
    <thead><tr>
      <th data-k="id">ID</th><th data-k="engagement">Engagement</th>
      <th data-k="severity">Severity</th><th data-k="status">Status</th>
      <th data-k="vuln_class">Class</th><th data-k="target">Target</th>
    </tr></thead>
    <tbody id="tb"></tbody>
  </table>
  <div class="hint">Local read-only snapshot — contains findings data; do not commit or share this file.</div>
</div>
<script type="application/json" id="data">/*DATA*/</script>
<script>
  const D = JSON.parse(document.getElementById("data").textContent);
  const esc = s => (s==null?"":String(s)).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const sevRank = s => { const i = D.severities.indexOf(s); return i<0?0:i; };
  let sortKey="severity", sortDir=-1;

  document.getElementById("meta").textContent =
    `${D.findings.length} finding(s) across ${D.engagements.length} engagement(s) · generated ${D.generated}`;

  // summary cards: totals + per-severity + scope warnings
  const bySev = {}; D.severities.forEach(s=>bySev[s]=0);
  let warns=0; D.findings.forEach(f=>{ if(bySev[f.severity]!=null)bySev[f.severity]++; if(f.scope_warning&&f.scope_warning.length)warns++; });
  const confirmed = D.findings.filter(f=>f.status==="confirmed"||f.status==="reported").length;
  const cards = [["engagements",D.engagements.length],["findings",D.findings.length],["confirmed",confirmed]]
    .concat(D.severities.slice().reverse().map(s=>[s,bySev[s]]));
  if(warns) cards.push(["⚠ scope warnings",warns]);
  document.getElementById("cards").innerHTML = cards.map(([l,n])=>
    `<div class="card"><div class="n">${n}</div><div class="l">${esc(l)}</div></div>`).join("");

  // populate filters
  const engSel=document.getElementById("f-eng");
  D.engagements.forEach(e=>{ const o=document.createElement("option"); o.value=e.name; o.textContent=`${e.name} (${e.findings})`; engSel.appendChild(o); });
  const stSel=document.getElementById("f-status");
  D.statuses.forEach(s=>{ const o=document.createElement("option"); o.value=s; o.textContent=s; stSel.appendChild(o); });
  const svSel=document.getElementById("f-sev");
  D.severities.slice().reverse().forEach(s=>{ const o=document.createElement("option"); o.value=s; o.textContent=s; svSel.appendChild(o); });

  const F={eng:"",status:"",sev:"",q:""};
  engSel.onchange=e=>{F.eng=e.target.value;draw();};
  stSel.onchange=e=>{F.status=e.target.value;draw();};
  svSel.onchange=e=>{F.sev=e.target.value;draw();};
  document.getElementById("f-q").oninput=e=>{F.q=e.target.value.toLowerCase();draw();};
  document.querySelectorAll("th[data-k]").forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; if(sortKey===k)sortDir*=-1; else{sortKey=k;sortDir=1;} draw();
  });

  function rows(){
    let r=D.findings.filter(f=>
      (!F.eng||f.engagement===F.eng)&&(!F.status||f.status===F.status)&&(!F.sev||f.severity===F.sev)&&
      (!F.q||[f.title,f.target,f.vuln_class,f.notes,f.id].join(" ").toLowerCase().includes(F.q)));
    r.sort((a,b)=>{
      let va,vb;
      if(sortKey==="severity"){va=sevRank(a.severity);vb=sevRank(b.severity);}
      else{va=(a[sortKey]||"").toString().toLowerCase();vb=(b[sortKey]||"").toString().toLowerCase();}
      return (va<vb?-1:va>vb?1:0)*sortDir;
    });
    return r;
  }

  function draw(){
    const tb=document.getElementById("tb"); const r=rows(); tb.innerHTML="";
    if(!r.length){ tb.innerHTML=`<tr><td colspan="6" class="empty">No findings match.</td></tr>`; return; }
    r.forEach(f=>{
      const tr=document.createElement("tr"); tr.className="row";
      const warn=f.scope_warning&&f.scope_warning.length?` <span class="warn" title="PoC/target touched out-of-scope: ${esc(f.scope_warning.join(', '))}">⚠</span>`:"";
      tr.innerHTML=
        `<td>${esc(f.id)}</td><td>${esc(f.engagement)}</td>`+
        `<td><span class="pill" style="background:var(--${f.severity})">${esc(f.severity)}</span></td>`+
        `<td><span class="pill" style="background:var(--${f.status})">${esc(f.status)}</span></td>`+
        `<td>${esc(f.vuln_class)}</td>`+
        `<td class="tgt">${esc(f.target)}${f.param?` <span style="color:var(--muted)">?${esc(f.param)}</span>`:""}${warn}</td>`;
      const det=document.createElement("tr"); det.className="detail"; det.style.display="none";
      det.innerHTML=`<td colspan="6">
        <div><strong>${esc(f.title||"(untitled)")}</strong></div>
        ${f.skills_used&&f.skills_used.length?`<div class="kv">skills</div>${esc(f.skills_used.join(', '))}`:""}
        ${f.evidence?`<div class="kv">evidence</div><pre>${esc(f.evidence)}</pre>`:""}
        ${f.poc?`<div class="kv">poc</div><pre>${esc(f.poc)}</pre>`:""}
        ${f.notes?`<div class="kv">notes</div>${esc(f.notes)}`:""}
        ${f.scope_warning&&f.scope_warning.length?`<div class="kv warn">scope warning</div><span class="warn">${esc(f.scope_warning.join(', '))}</span>`:""}
        <div class="kv">phase found / created / updated</div>${esc(f.phase_found)} · ${esc(f.created)} · ${esc(f.updated)}</td>`;
      tr.onclick=()=>{ det.style.display=det.style.display==="none"?"":"none"; };
      tb.appendChild(tr); tb.appendChild(det);
    });
  }
  draw();
</script>
</body>
</html>"""
