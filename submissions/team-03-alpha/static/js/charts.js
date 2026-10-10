const SEV_COLORS = {critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#38bdf8'};
Chart.defaults.color = '#8b97b5';
Chart.defaults.font.family = 'Inter, system-ui, sans-serif';

function makeChart(id, type, labels, datasets, extra = {}) {
  return new Chart(document.getElementById(id), {
    type, data: {labels, datasets},
    options: {
      responsive: true, maintainAspectRatio: false, interaction: {mode: 'index', intersect: false},
      plugins: {legend: {display: datasets.length > 1 || type === 'doughnut'}},
      scales: type === 'doughnut' ? {} : {
        x: {grid: {display: false}, ticks: {maxTicksLimit: 8}},
        y: {grid: {color: '#1f2a44'}, beginAtZero: true, ticks: {precision: 0}}},
      ...extra}
  });
}
