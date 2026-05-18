'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import 'leaflet/dist/leaflet.css';

const MapContainer = dynamic(() => import('react-leaflet').then(m => m.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import('react-leaflet').then(m => m.TileLayer), { ssr: false });
const Marker = dynamic(() => import('react-leaflet').then(m => m.Marker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then(m => m.Popup), { ssr: false });

interface Location {
  lat: number;
  lon: number;
}

interface DeliveryMapProps {
  orderId: string;
}

export default function DeliveryMap({ orderId }: DeliveryMapProps) {
  const [position, setPosition] = useState<Location | null>(null);

  useEffect(() => {
    import('leaflet').then((L) => {
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
        shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
      });
    });

    const eventSource = new EventSource(`http://localhost:8000/api/stream/${orderId}`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.location) {
        setPosition({ lat: data.location.latitude, lon: data.location.longitude });
      }
    };

    return () => eventSource.close();
  }, [orderId]);

  return (
    <div className="h-[500px] w-full shadow-inner rounded-xl overflow-hidden border border-slate-200 mt-6">
      <MapContainer center={[37.33, -121.88]} zoom={12} className="h-full w-full">
        <TileLayer 
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">carto.com</a>'
        />
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