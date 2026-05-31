'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import 'leaflet/dist/leaflet.css';

const MapContainer = dynamic(() => import('react-leaflet').then(m => m.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import('react-leaflet').then(m => m.TileLayer), { ssr: false });
const Marker = dynamic(() => import('react-leaflet').then(m => m.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then(m => m.Popup), { ssr: false });
const Polyline = dynamic(() => import('react-leaflet').then(m => m.Polyline), { ssr: false });
const CircleMarker = dynamic(() => import('react-leaflet').then(m => m.CircleMarker), { ssr: false });

interface Location {
  lat: number;
  lon: number;
}

interface DeliveryMapProps {
  orderId: string;
  apiBaseUrl: string;
}

export default function DeliveryMap({ orderId, apiBaseUrl }: DeliveryMapProps) {
  const [position, setPosition] = useState<Location | null>(null);
  const [path, setPath] = useState<Location[]>([]);

  useEffect(() => {
    import('leaflet').then((L) => {
      delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
      });
    });

    const eventSource = new EventSource(`${apiBaseUrl}/api/stream/${orderId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.location) {
        const nextPosition = {
          lat: data.location.latitude,
          lon: data.location.longitude,
        };

        if (typeof nextPosition.lat !== 'number' || typeof nextPosition.lon !== 'number') {
          return;
        }

        setPosition(nextPosition);
        setPath((currentPath) => {
          const lastPosition = currentPath[currentPath.length - 1];
          if (
            lastPosition &&
            lastPosition.lat === nextPosition.lat &&
            lastPosition.lon === nextPosition.lon
          ) {
            return currentPath;
          }

          return [...currentPath, nextPosition].slice(-500);
        });
      }
    };

    eventSource.addEventListener('complete', () => {
      eventSource.close();
    });

    return () => eventSource.close();
  }, [apiBaseUrl, orderId]);

  return (
    <div className="h-[500px] w-full shadow-inner rounded-xl overflow-hidden border border-slate-200 mt-6">
      <MapContainer center={[37.33, -121.88]} zoom={12} className="h-full w-full">
        <TileLayer 
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">carto.com</a>'
        />
        {path.length > 1 && (
          <>
            <Polyline
              positions={path.map(point => [point.lat, point.lon])}
              pathOptions={{
                color: '#f97316',
                weight: 6,
                opacity: 0.95,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
            {path.slice(0, -1).map((point, index) => (
              <CircleMarker
                key={`${point.lat}-${point.lon}-${index}`}
                center={[point.lat, point.lon]}
                radius={3}
                pathOptions={{
                  color: '#fff7ed',
                  fillColor: '#f97316',
                  fillOpacity: 0.9,
                  weight: 1,
                }}
              />
            ))}
          </>
        )}
        {position && (
          <Marker position={[position.lat, position.lon]}>
            <Popup>
              <div className="font-sans text-xs">
                <span className="font-bold text-emerald-600 animate-pulse">● Live Courier</span>
                <p className="mt-1 text-slate-500 font-mono">{orderId.slice(0, 8)}...</p>
              </div>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
