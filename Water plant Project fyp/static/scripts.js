// Handle Toggle for Demo Data Mode
document
  .getElementById("data-mode-toggle")
  .addEventListener("change", function () {
    fetch("/dashboard/toggle_demo_data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ demo_data: this.checked }),
    }).then(() => location.reload());
  });

// Handle Adding Graph (Real Data Mode)
const addGraphBtn = document.getElementById("add-graph-btn");
if (addGraphBtn) {
  addGraphBtn.addEventListener("click", () => {
    window.location.href = "/dashboard/add_graph";
  });
}

// Render Graphs
function renderGraph(graphConfig) {
  const graphId = `graph-${graphConfig.id}`;
  const graphElement = document.querySelector(`#${graphId} .graph-content`);

  // Example: Render a Gauge Chart
  if (graphConfig.type === "Gauge") {
    const { min_val, max_val, color } = graphConfig;
    Plotly.newPlot(graphElement, [
      {
        type: "indicator",
        mode: "gauge+number",
        value: Math.random() * (max_val - min_val) + min_val,
        gauge: {
          axis: { range: [min_val, max_val] },
          bar: { color: color },
        },
      },
    ]);
  }
}

// Load all configured graphs
document.querySelectorAll(".graph-content").forEach((graph) => {
  const graphConfig = JSON.parse(graph.dataset.config);
  renderGraph(graphConfig);
});
