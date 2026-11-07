// Renders Chart.js line charts from <script type="application/json"> blocks.
// Re-renders after HTMX swaps and when the color scheme changes.
(function () {
  "use strict";

  const root = document.documentElement;
  const locale = root.dataset.locale || "hu-HU";
  const currency = root.dataset.currency || "Ft";
  const NBSP = "\u00a0";
  const full = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const compact = new Intl.NumberFormat(locale, { notation: "compact", maximumFractionDigits: 1 });
  const money = (v) => full.format(v) + NBSP + currency;

  const cssVar = (name) => getComputedStyle(root).getPropertyValue(name).trim();

  // Vertical crosshair at the hovered x position.
  const crosshair = {
    id: "crosshair",
    afterDatasetsDraw(chart) {
      const active = chart.tooltip && chart.tooltip.getActiveElements();
      if (!active || !active.length) return;
      const x = active[0].element.x;
      const { top, bottom } = chart.chartArea;
      const ctx = chart.ctx;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, bottom);
      ctx.lineWidth = 1;
      ctx.strokeStyle = cssVar("--text-muted");
      ctx.stroke();
      ctx.restore();
    },
  };

  function render(canvas) {
    if (typeof Chart === "undefined") return;
    const source = document.getElementById(canvas.dataset.chart);
    if (!source) return;
    const spec = JSON.parse(source.textContent);
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    const ink = cssVar("--text-secondary");
    const grid = cssVar("--grid");
    const surface = cssVar("--surface-1");

    new Chart(canvas, {
      type: "line",
      data: {
        labels: spec.labels,
        datasets: spec.datasets.map((d) => {
          const color = cssVar("--series-" + d.slot);
          return {
            label: d.label,
            data: d.data,
            borderColor: color,
            backgroundColor: color,
            borderWidth: 2,
            borderDash: d.dashed ? [6, 4] : [],
            pointRadius: 0,
            pointHitRadius: 12,
            pointHoverRadius: 5,
            pointHoverBorderWidth: 2,
            pointHoverBorderColor: surface,
            tension: 0,
          };
        }),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            position: "top",
            align: "start",
            labels: { color: ink, usePointStyle: true, pointStyle: "line", boxWidth: 28 },
          },
          tooltip: {
            backgroundColor: surface,
            titleColor: cssVar("--text-primary"),
            bodyColor: ink,
            borderColor: grid,
            borderWidth: 1,
            padding: 10,
            usePointStyle: true,
            callbacks: { label: (c) => " " + c.dataset.label + ": " + money(c.parsed.y) },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            border: { color: grid },
            ticks: { color: ink, maxTicksLimit: 8, maxRotation: 0 },
          },
          y: {
            beginAtZero: true,
            grid: { color: grid },
            border: { display: false },
            ticks: { color: ink, maxTicksLimit: 6, callback: (v) => compact.format(v) + NBSP + currency },
          },
        },
      },
      plugins: [crosshair],
    });
  }

  function renderAll(scope) {
    (scope || document).querySelectorAll("canvas[data-chart]").forEach(render);
  }

  document.addEventListener("DOMContentLoaded", () => renderAll());
  document.addEventListener("htmx:afterSettle", (e) => renderAll(e.detail.target));
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => renderAll());
})();
