(function(){const n=document.createElement("link").relList;if(n&&n.supports&&n.supports("modulepreload"))return;for(const t of document.querySelectorAll('link[rel="modulepreload"]'))a(t);new MutationObserver(t=>{for(const s of t)if(s.type==="childList")for(const i of s.addedNodes)i.tagName==="LINK"&&i.rel==="modulepreload"&&a(i)}).observe(document,{childList:!0,subtree:!0});function r(t){const s={};return t.integrity&&(s.integrity=t.integrity),t.referrerPolicy&&(s.referrerPolicy=t.referrerPolicy),t.crossOrigin==="use-credentials"?s.credentials="include":t.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function a(t){if(t.ep)return;t.ep=!0;const s=r(t);fetch(t.href,s)}})();const o=document.getElementById("output"),d=document.getElementById("message"),u=document.getElementById("run"),p=document.getElementById("sample"),c=["My package is late and I need an update.","I was charged twice and need a refund.","Someone used my account without permission. This is a fraud issue.","My item arrived damaged and I need support."];function m(){o.innerHTML=`
    <div class="card result-card">
      <h3>Running analysis</h3>
      <p>Evaluating intent, retrieving similar precedents, and deciding whether the message should be auto-handled.</p>
    </div>
  `}function l(e){o.innerHTML=`
    <div class="card result-card">
      <div class="error">${e}</div>
    </div>
  `}function f(e){const n=e.decision==="auto_handle"?"auto":"escalate",r=(e.precedents||[]).map(a=>`
    <li>
      <div>${a.customer_msg}</div>
      <span class="similarity">Similarity: ${a.similarity}</span>
    </li>
  `).join("");o.innerHTML=`
    <article class="result-card">
      <h3>Intent</h3>
      <div class="metric-row">
        <span class="value">${e.intent}</span>
        <span class="pill ${n}">${e.decision}</span>
      </div>
      <div class="metric-row">
        <span>Confidence</span>
        <span class="value">${e.confidence}</span>
      </div>
      <div class="metric-row">
        <span>Reason</span>
        <span>${e.reason}</span>
      </div>
    </article>

    <article class="result-card">
      <h3>Precedents</h3>
      <ul class="precedent-list">${r}</ul>
    </article>

    <article class="result-card">
      <h3>Draft reply</h3>
      <p>${e.draft_reply}</p>
    </article>
  `}async function h(){const e=d.value.trim();if(!e){l("Please enter a customer message before running the agent.");return}m();try{const n=await fetch("http://localhost:8000/api/agent/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:e,brand:"AmazonHelp"})});if(!n.ok)throw new Error(`API request failed with status ${n.status}`);const r=await n.json();f(r)}catch(n){l(`The demo could not connect to the backend. Make sure the API is running on localhost:8000. ${n.message}`)}}function g(){const e=c[Math.floor(Math.random()*c.length)];d.value=e}u.addEventListener("click",h);p.addEventListener("click",g);
