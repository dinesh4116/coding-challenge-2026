let charts = [];
function refresh() {
  fetch('/api/summary').then(r => r.json()).then(s => {
    const sev = s.severity, open = Object.values(sev).reduce((a, b) => a + b, 0);
    const kpi = (v, l, c = '') => `<div class="card kpi ${c}"><div class="v">${v}</div><div class="mut">${l}</div></div>`;
    document.getElementById('kpis').innerHTML =
      kpi(s.totals.campaigns, 'Campaigns monitored') + kpi(s.totals.data_points.toLocaleString(), 'Data points analyzed') +
      kpi(s.totals.affected, 'Campaigns needing attention', 'warn') + kpi(sev.critical || 0, 'Critical alerts', 'crit');
    charts.forEach(c => c.destroy());
    charts = [
      makeChart('dailyChart', 'bar', s.daily.map(d => d.d.slice(5)), [{data: s.daily.map(d => d.n), backgroundColor: '#6366f1', borderRadius: 6}]),
      makeChart('sevChart', 'doughnut', ['Critical', 'High', 'Medium', 'Low'],
        [{data: ['critical', 'high', 'medium', 'low'].map(k => sev[k] || 0),
          backgroundColor: [SEV_COLORS.critical, SEV_COLORS.high, SEV_COLORS.medium, SEV_COLORS.low], borderWidth: 0}],
        {cutout: '68%'})];
  });
  fetch('/api/alerts?severity=medium&status=open&days=14&limit=8').then(r => r.json())
    .then(a => renderAlerts(document.getElementById('alertList'), a, false, refresh));
}
refresh();
setInterval(refresh, 30000);   // live refresh every 30s
