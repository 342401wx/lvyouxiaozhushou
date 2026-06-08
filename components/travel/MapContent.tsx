'use client';

import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Attraction } from '@/lib/types';

// Fix Leaflet default marker icon issue
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

L.Marker.prototype.options.icon = defaultIcon;

// Custom numbered icon
const createNumberedIcon = (number: string, isAttraction: boolean = true) => {
  const color = isAttraction ? '#0ea5e9' : '#14b8a6';
  return L.divIcon({
    className: 'custom-marker',
    html: `<div style="
      background: ${color};
      color: white;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: bold;
      border: 2px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    ">${number}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
};

function FitBounds({ attractions }: { attractions: Attraction[] }) {
  const map = useMap();

  useEffect(() => {
    if (attractions.length > 0) {
      const bounds = L.latLngBounds(attractions.map(a => [a.latitude, a.longitude]));
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [attractions, map]);

  return null;
}

interface MapContentProps {
  attractions: Attraction[];
  onAttractionClick?: (attraction: Attraction) => void;
  selectedDay?: number | null;
  inModal?: boolean;
}

export function MapContent({ attractions, onAttractionClick, selectedDay, inModal }: MapContentProps) {
  // Filter attractions based on selected day
  const filteredAttractions = selectedDay === null || selectedDay === undefined
    ? attractions
    : attractions.filter(a => a.dayNumber === selectedDay);

  // Default center (Zibo city center)
  const defaultCenter: [number, number] = [36.8131, 118.0517];
  const center = filteredAttractions.length > 0
    ? [filteredAttractions[0].latitude, filteredAttractions[0].longitude] as [number, number]
    : defaultCenter;

  return (
    <MapContainer
      center={center}
      zoom={12}
      style={{ height: '100%', width: '100%', borderRadius: '0.5rem' }}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {filteredAttractions.length > 0 && <FitBounds attractions={filteredAttractions} />}
      {filteredAttractions.map((attraction) => (
        <Marker
          key={attraction.id}
          position={[attraction.latitude, attraction.longitude]}
          icon={createNumberedIcon(`${attraction.dayNumber}-${attraction.stopNumber}`)}
          eventHandlers={{
            click: () => onAttractionClick?.(attraction),
          }}
        >
          <Popup>
            <div className="min-w-[200px]">
              <div className="font-medium text-slate-800">{attraction.name}</div>
              <div className="text-xs text-slate-500 mt-1">{attraction.category}</div>
              <div className="text-xs text-slate-600 mt-1">{attraction.address}</div>
              <div className="text-xs text-sky-600 mt-1">{attraction.ticket}</div>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
