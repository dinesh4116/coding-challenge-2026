const rows = window.dashboardRows || [];
const selectedMetric = window.selectedMetric || "CTR (%)";

function validNumbers(values) {
    return values
        .filter(value =>
            value !== null &&
            value !== undefined &&
            Number.isFinite(Number(value))
        )
        .map(Number);
}

function median(values) {
    const valid = validNumbers(values).sort((a, b) => a - b);

    if (valid.length === 0) return null;

    const middle = Math.floor(valid.length / 2);

    return valid.length % 2
        ? valid[middle]
        : (valid[middle - 1] + valid[middle]) / 2;
}

function countTier(tier) {
    return rows.filter(row => row.tier === tier).length;
}

function updateSummary() {
    document.getElementById("totalAssets").textContent = rows.length;
    document.getElementById("goodCount").textContent = countTier("Good");
    document.getElementById("averageCount").textContent = countTier("Average");
    document.getElementById("poorCount").textContent = countTier("Poor");
}

function createTierChart() {
    const canvas = document.getElementById("tierChart");
    if (!canvas) return;

    new Chart(canvas, {
        type: "doughnut",

        data: {
            labels: ["Good", "Average", "Poor", "Insufficient data"],

            datasets: [{
                data: [
                    countTier("Good"),
                    countTier("Average"),
                    countTier("Poor"),
                    countTier("Insufficient data")
                ],

                backgroundColor: [
                    "#16a34a",
                    "#eab308",
                    "#dc2626",
                    "#9ca3af"
                ],

                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}

function createMediaChart() {
    const canvas = document.getElementById("mediaChart");
    if (!canvas) return;

    const imageRows = rows.filter(row => row.asset_type === "Image");
    const videoRows = rows.filter(row => row.asset_type === "Video");

    const imageMedian = median(
        imageRows.map(row => row.metric_value)
    );

    const videoMedian = median(
        videoRows.map(row => row.metric_value)
    );

    new Chart(canvas, {
        type: "bar",

        data: {
            labels: ["Images", "Videos"],

            datasets: [{
                label: `Median ${selectedMetric}`,
                data: [imageMedian, videoMedian],
                backgroundColor: ["#6366f1", "#0891b2"],
                borderRadius: 8
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: `Median ${selectedMetric}`
                    }
                }
            },

            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

function createFeatureChart() {
    const canvas = document.getElementById("featureChart");
    if (!canvas) return;

    const tiers = [
        { name: "Good", color: "#16a34a" },
        { name: "Average", color: "#eab308" },
        { name: "Poor", color: "#dc2626" },
        { name: "Insufficient data", color: "#9ca3af" }
    ];

    const datasets = tiers.map(tier => ({
        label: tier.name,

        data: rows
            .filter(row =>
                row.tier === tier.name &&
                row.brightness !== null &&
                row.metric_value !== null
            )
            .map(row => ({
                x: Number(row.brightness),
                y: Number(row.metric_value),
                filename: row.filename
            })),

        backgroundColor: tier.color,
        pointRadius: 6,
        pointHoverRadius: 9
    }));

    new Chart(canvas, {
        type: "scatter",

        data: { datasets },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            scales: {
                x: {
                    title: {
                        display: true,
                        text: "Brightness (0–255)"
                    }
                },

                y: {
                    title: {
                        display: true,
                        text: selectedMetric
                    }
                }
            },

            plugins: {
                legend: {
                    position: "bottom"
                },

                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const point = context.raw;

                            return `${point.filename}: brightness ${point.x}, `
                                + `${selectedMetric} ${point.y}`;
                        }
                    }
                }
            }
        }
    });
}

function downloadCSV() {
    if (!rows.length) return;

    const columns = [
        "filename",
        "asset_type",
        "brightness",
        "contrast",
        "saturation",
        "edge_density",
        "motion",
        "duration",
        "impressions",
        "clicks",
        "conversions",
        "spend",
        "revenue",
        "ctr",
        "conversion_rate",
        "cpa",
        "roas",
        "metric_value",
        "tier"
    ];

    function escapeCSV(value) {
        if (value === null || value === undefined) return "";

        return '"' + String(value).replace(/"/g, '""') + '"';
    }

    const output = [
        columns.map(escapeCSV).join(",")
    ];

    rows.forEach(row => {
        output.push(
            columns.map(column => escapeCSV(row[column])).join(",")
        );
    });

    const blob = new Blob(
        ["\uFEFF" + output.join("\r\n")],
        { type: "text/csv;charset=utf-8;" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "ad_creative_analysis.csv";

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(url);
}

document.addEventListener("DOMContentLoaded", function () {
    if (rows.length > 0) {
        updateSummary();
        createTierChart();
        createMediaChart();
        createFeatureChart();
    }

    const downloadButton = document.getElementById("downloadCsv");

    if (downloadButton) {
        downloadButton.addEventListener("click", downloadCSV);
    }
});