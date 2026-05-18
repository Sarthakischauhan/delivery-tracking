'use client';

import { useState } from 'react';
import DeliveryMap from './components/DeliveryMap';

export default function Home() {
  const [order, setOrder] = useState<{ order_id: string; assigned_driver: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const startOrder = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/orders', { method: 'POST' });
      const data = await res.json();
      setOrder(data);
    } catch (err) {
      console.error('Failed to initiate tracker:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-slate-900">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-xl border border-slate-100 p-8">
        <header className="border-b border-slate-100 pb-6 mb-6">
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">Dynamic Delivery Registry</h1>
          <p className="text-sm text-slate-500 mt-1">Real-time geospatial event streaming engine built over Apache Kafka.</p>
        </header>

        {!order ? (
          <div className="flex flex-col items-center justify-center py-12">
            <button
              onClick={startOrder}
              disabled={loading}
              className="px-6 py-3 bg-slate-900 text-white rounded-lg font-medium tracking-wide hover:bg-slate-800 transition-colors disabled:bg-slate-400 shadow-md"
            >
              {loading ? 'Assigning Courier...' : 'Place Tracking Request'}
            </button>
          </div>
        ) : (
          <div>
            <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200 font-mono text-sm">
              <div>
                <span className="text-slate-400 text-xs block uppercase tracking-wider font-sans">System Order Identity</span>
                <span className="font-semibold text-slate-700">{order.order_id}</span>
              </div>
              <div>
                <span className="text-slate-400 text-xs block uppercase tracking-wider font-sans">Assigned Driver Vector</span>
                <span className="font-semibold text-emerald-600">{order.assigned_driver}</span>
              </div>
            </div>
            
            <DeliveryMap orderId={order.order_id} />
          </div>
        )}
      </div>
    </main>
  );
}