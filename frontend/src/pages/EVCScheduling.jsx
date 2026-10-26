import React, { useState, useEffect } from 'react';
import { CalendarCheck2, Clock, Users, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function EVCScheduling() {
  const { user, refreshKey, triggerGlobalRefresh } = useAuth();
  const [evcs, setEvcs] = useState([]);
  const [loading, setLoading] = useState(true);

  // Scheduling modal
  const [schedModalApp, setSchedModalApp] = useState(null);
  const [schedDate, setSchedDate] = useState('');
  const [commMembers, setCommMembers] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchEvcs = async () => {
      setLoading(true);
      try {
        const res = await api.get('/evc');
        setEvcs(res.data);
      } catch (e) {
        console.error("Error loading EVCs", e);
      } finally {
        setLoading(false);
      }
    };
    fetchEvcs();
  }, [refreshKey]);

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!schedModalApp) return;
    setSubmitting(true);
    try {
      await api.post(`/evc/${schedModalApp.application_id}/schedule`, {
        scheduled_date: new Date(schedDate).toISOString(),
        committee_members: commMembers
      });
      setSchedModalApp(null);
      setSchedDate('');
      setCommMembers('');
      triggerGlobalRefresh();
    } catch (e) {
      alert("Error scheduling EVC: " + (e.response?.data?.detail || e.message));
    } finally {
      setSubmitting(false);
    }
  };

  const canSchedule = ['Regional Officer', 'Bureau Officer', 'Admin'].includes(user?.role);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 leading-tight">Expert Visit Committee (EVC) Operations Desk</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Schedule inspections, allocate expert committees, track priority flags, and monitor visit delays.
        </p>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading EVC records...</div>
        ) : evcs.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">No EVC dossiers found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Application No</th>
                  <th className="py-3 px-4">Institution Name</th>
                  <th className="py-3 px-4">EVC Status</th>
                  <th className="py-3 px-4">Inspection Date</th>
                  <th className="py-3 px-4">Allocated Committee</th>
                  <th className="py-3 px-4">Findings & Recommendations</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {evcs.map((evc) => (
                  <tr key={evc.id} className="hover:bg-slate-50/80">
                    <td className="py-3.5 px-4 font-mono font-bold text-slate-900">{evc.application_no}</td>
                    <td className="py-3.5 px-4 max-w-xs truncate text-slate-800">{evc.institution_name}</td>
                    <td className="py-3.5 px-4">
                      {evc.is_overdue ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300 animate-pulse">
                          🚨 OVERDUE ({evc.days_overdue}d)
                        </span>
                      ) : evc.status === 'COMPLETED' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          ✓ COMPLETED
                        </span>
                      ) : evc.status === 'SCHEDULED' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                          SCHEDULED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                          QUEUED
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      {evc.scheduled_date ? new Date(evc.scheduled_date).toLocaleDateString() : 'Not Scheduled'}
                    </td>
                    <td className="py-3.5 px-4 max-w-xs text-slate-600 truncate">
                      {evc.committee_members || 'Pending Allocation'}
                    </td>
                    <td className="py-3.5 px-4 max-w-xs">
                      {evc.recommendations ? (
                        <span className="font-bold text-slate-800">{evc.recommendations}</span>
                      ) : (
                        <span className="text-slate-400 italic">Report Pending</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {evc.status === 'QUEUED' && canSchedule && (
                        <button
                          onClick={() => setSchedModalApp(evc)}
                          className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-[11px] font-bold transition-colors"
                        >
                          Schedule Visit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Schedule EVC Modal */}
      {schedModalApp && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Schedule EVC Inspection: {schedModalApp.application_no}
            </h3>
            <form onSubmit={handleScheduleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Inspection Date</label>
                <input
                  type="date"
                  required
                  value={schedDate}
                  onChange={(e) => setSchedDate(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="block font-bold text-slate-700 mb-1">Nominated Committee Members</label>
                <input
                  type="text"
                  required
                  value={commMembers}
                  onChange={(e) => setCommMembers(e.target.value)}
                  placeholder="e.g. Prof. Ramanathan (IIT Delhi), Dr. Sharma"
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSchedModalApp(null)}
                  className="px-3 py-1.5 font-bold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg"
                >
                  {submitting ? 'Saving...' : 'Confirm Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
