import { MapContainer, Polygon, TileLayer, Tooltip } from "react-leaflet";
import type { Plot } from "../api";

interface Props {
  plots: Plot[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  center: [number, number];
  zoom: number;
}

export default function PlotMap({ plots, selectedId, onSelect, center, zoom }: Props) {
  return (
    <div className="h-72 overflow-hidden rounded-lg border border-stone-200">
      <MapContainer
        key={`${center[0]},${center[1]}`}
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution="Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics"
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />
        <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}" />
        {plots.map((p) => (
          <Polygon
            key={p.id}
            positions={p.geometry.coordinates[0].map(([lng, lat]) => [lat, lng] as [number, number])}
            pathOptions={{
              color: p.id === selectedId ? "#15803d" : "#f59e0b",
              weight: p.id === selectedId ? 4 : 2,
              fillOpacity: 0.4,
            }}
            eventHandlers={{ click: () => onSelect(p.id) }}
          >
            <Tooltip>
              {p.farmer} — {p.village} ({p.crop_current})
            </Tooltip>
          </Polygon>
        ))}
      </MapContainer>
    </div>
  );
}
