document.addEventListener("DOMContentLoaded", () => {
  const map = L.map("map", {
    center: [20, 0],
    zoom: 2,
    minZoom: 1,
    maxZoom: 10,
    zoomControl: false, // use custom +/- controls
    attributionControl: false,
  });

  const mapElement = document.getElementById("map");
  mapElement.style.backgroundColor = "#ffffff";

  // Keep land polygons below Leaflet's normal overlay pane (game shapes).
  const landPane = map.createPane("landPane");
  landPane.style.zIndex = "350";

  // Helper function to add GeoJSON layers with a specific color
  function addLayer(shape, color) {
    if (!shape) return;
    L.geoJSON(shape, {
      style: {
        color: color,        // Border color
        fillColor: color,    // Fill color
        weight: 2,
        fillOpacity: 0.7,    // Controls how opaque the fill is
      },
    }).addTo(map);
  }

  // Optionally load global border outlines (no fill)
  function addBorderOutlines(url) {
    // The same GeoJSON supplies land silhouettes and country border outlines.
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load border outlines');
        return r.json();
      })
      .then((geo) => {
        mapElement.style.backgroundColor = "#b9def2";
        L.geoJSON(geo, {
          pane: "landPane",
          interactive: false,
          style: {
            stroke: false,
            fill: true,
            fillColor: "#ffffff",
            fillOpacity: 1,
          },
        }).addTo(map);
        L.geoJSON(geo, {
          style: { color: "#888", weight: 1, fill: false },
        }).addTo(map);
      })
      .catch(() => {});
  }

  // Expose for external callers (e.g., hint prompt)
  window.addBorderOutlines = addBorderOutlines;

  if (window.SHOW_BORDER_LINES) {
    if (window.addBorderOutlines) {
      console.log("[Map] Adding border outlines as per game state.");
      window.addBorderOutlines('/static/map_data/border_outlines.geojson');
    }
  }
  
  // Add main country in black
  addLayer(countryShape, "black");

  // Add correct guesses in green
  addLayer(correctShapes, "green");

  // Add incorrect guesses in red
  addLayer(wrongShapes, "red");

  // Wire up custom zoom buttons (if present)
  const zi = document.getElementById('zoom-in');
  const zo = document.getElementById('zoom-out');
  if (zi) zi.addEventListener('click', () => map.zoomIn());
  if (zo) zo.addEventListener('click', () => map.zoomOut());

  // Fit bounds to all shapes
  const allLayers = [];
  if (countryShape) allLayers.push(L.geoJSON(countryShape));
  if (correctShapes) allLayers.push(L.geoJSON(correctShapes));
  if (wrongShapes) allLayers.push(L.geoJSON(wrongShapes));

  if (allLayers.length > 0) {
    const group = L.featureGroup(allLayers);
    map.fitBounds(group.getBounds().pad(0.2));
  }
});
