const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

function renderAlerts(el, alerts, hideCampaign = false, reload) {
  if (!alerts.length) { el.innerHTML = '<p class="mut empty">&#10003; No meaningful alerts. All campaigns are within their normal range.</p>'; return; }
  el.innerHTML = alerts.map(a => `
    <div class="alert ${esc(a.severity)}">
      <div class="between">
        <div><span class="badge ${esc(a.severity)}">${esc(a.severity)}</span>
          <b>${esc(a.metric.toUpperCase())} ${esc(a.alert_type)}</b>
          ${hideCampaign ? '' : `&middot; <a href="/campaigns/${a.campaign_id}">${esc(a.campaign_name)}</a>`}</div>
        <span class="mut">${esc(a.metric_date)}</span></div>
      <p>${esc(a.explanation)}</p>
      <p class="rec"><b>Next step:</b> ${esc(a.recommendation)}</p>
      <div class="between"><span class="mut">z = ${esc(a.z_score)}</span>
        ${a.status === 'open' ? `<button class="btn sm ghost" data-ack="${a.id}">Acknowledge</button>` : '<span class="badge ok">acknowledged</span>'}</div>
    </div>`).join('');
  el.querySelectorAll('[data-ack]').forEach(b => b.onclick = () =>
    fetch(`/api/alerts/${b.dataset.ack}/status`, {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({status: 'acknowledged'})}).then(() => reload ? reload() : (b.closest('.alert').style.opacity = .4)));
}
