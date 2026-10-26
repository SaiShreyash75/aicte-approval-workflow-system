import React, { useState } from 'react';
import { Calendar, FastForward, RotateCcw, X, Check } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function SimulateTimeModal({ isOpen, onClose }) {
  const { systemTime, triggerGlobalRefresh } = useAuth();
  const [customDate, setCustomDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');

  if (!isOpen) return null;

  const handleAdvance = async (days) => {
    setLoading(true);
    setMsg('');
    try {
      const res = await api.post('/admin/time/advance', { days });
      setMsg(`Virtual clock advanced by +${days} days!`);
      triggerGlobalRefresh();
    } catch (e) {
      setMsg('Error advancing time: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSetCustom = async () => {
    if (!customDate) return;
    setLoading(true);
    setMsg('');
    try {
      await api.post('/admin/time/set', { target_date: new Date(customDate).toISOString() });
      setMsg(`Virtual clock set to ${customDate}!`);
      triggerGlobalRefresh();
    } catch (e) {
      setMsg('Error setting date: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setMsg('');
    try {
      await api.post('/admin/time/reset');
      setMsg('Virtual clock reset to real current time!');
      triggerGlobalRefresh();
    } catch (e) {
      setMsg('Error resetting clock: ' + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="p-4 bg-slate-900 text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-amber-400" />
            <h3 className="font-bold text-base">Virtual Time Simulation Control</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-center">
            <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-1">
              Active Virtual Clock
            </div>
            <div className="text-lg font-mono font-bold text-slate-800">
              {systemTime?.formatted_date || 'Loading...'}
            </div>
            <div className="mt-1">
              {systemTime?.is_simulated ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                  • SIMULATED CLOCK ACTIVE
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">
                  • REAL TIME SYNCHRONIZED
                </span>
              )}
            </div>
          </div>

          {msg && (
            <div className="text-xs p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-800 flex items-center gap-1.5 font-medium">
              <Check className="w-4 h-4 text-blue-600 shrink-0" />
              <span>{msg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Advance Virtual Timeline (Triggers Live Escalations)
            </label>
            <div className="grid grid-cols-4 gap-2">
              <button
                disabled={loading}
                onClick={() => handleAdvance(1)}
                className="py-2 px-3 text-xs font-semibold bg-white border border-slate-300 hover:border-blue-600 hover:text-blue-600 rounded-lg shadow-xs transition-all flex items-center justify-center gap-1"
              >
                <FastForward className="w-3.5 h-3.5" /> +1 Day
              </button>
              <button
                disabled={loading}
                onClick={() => handleAdvance(7)}
                className="py-2 px-3 text-xs font-semibold bg-white border border-slate-300 hover:border-blue-600 hover:text-blue-600 rounded-lg shadow-xs transition-all flex items-center justify-center gap-1"
              >
                <FastForward className="w-3.5 h-3.5" /> +7 Days
              </button>
              <button
                disabled={loading}
                onClick={() => handleAdvance(15)}
                className="py-2 px-3 text-xs font-semibold bg-white border border-slate-300 hover:border-blue-600 hover:text-blue-600 rounded-lg shadow-xs transition-all flex items-center justify-center gap-1"
              >
                <FastForward className="w-3.5 h-3.5" /> +15 Days
              </button>
              <button
                disabled={loading}
                onClick={() => handleAdvance(30)}
                className="py-2 px-3 text-xs font-semibold bg-white border border-slate-300 hover:border-blue-600 hover:text-blue-600 rounded-lg shadow-xs transition-all flex items-center justify-center gap-1"
              >
                <FastForward className="w-3.5 h-3.5" /> +30 Days
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Set Specific Target Date
            </label>
            <div className="flex gap-2">
              <input
                type="date"
                value={customDate}
                onChange={(e) => setCustomDate(e.target.value)}
                className="flex-1 text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              />
              <button
                disabled={loading || !customDate}
                onClick={handleSetCustom}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
              >
                Apply
              </button>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-200">
            <button
              disabled={loading}
              onClick={handleReset}
              className="w-full py-2.5 px-4 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center justify-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Reset Virtual Clock to Real Date
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
