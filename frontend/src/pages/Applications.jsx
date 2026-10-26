import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, AlertTriangle, Clock, ArrowUpRight, ShieldCheck, Sparkles } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Applications() {
  const { user, systemTime, refreshKey } = useAuth();
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedRoute, setSelectedRoute] = useState('ALL');
  const [selectedStage, setSelectedStage] = useState('ALL');
  const [selectedSla, setSelectedSla] = useState('ALL'); // ALL, RED, AMBER, ON_TRACK

  useEffect(() => {
    const fetchApplications = async () => {
      setLoading(true);
      try {
        const res = await api.get('/applications');
        setApps(res.data);
      } catch (e) {
        console.error("Error loading applications", e);
      } finally {
        setLoading(false);
      }
    };
    fetchApplications();
  }, [refreshKey]);

  // Compute SLA status relative to systemTime
  const getSlaMeta = (stageDueDate, status) => {
    if (!stageDueDate || status === 'APPROVED' || status === 'REJECTED') {
      return { state: 'RESOLVED', label: status, color: 'text-slate-500 bg-slate-100 border-slate-200' };
    }
    const sysDate = systemTime?.simulated_date ? new Date(systemTime.simulated_date) : new Date();
    const dueDate = new Date(stageDueDate);
    const diffDays = Math.ceil((dueDate - sysDate) / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
      return {
        state: 'RED',
        label: `${Math.abs(diffDays)}d Overdue`,
        color: 'text-rose-700 bg-rose-50 border-rose-300 font-bold animate-pulse'
      };
    } else if (diffDays <= 2) {
      return {
        state: 'AMBER',
        label: `${diffDays}d Left (Near SLA)`,
        color: 'text-amber-800 bg-amber-50 border-amber-300 font-bold'
      };
    }
    return {
      state: 'ON_TRACK',
      label: `${diffDays}d remaining`,
      color: 'text-emerald-700 bg-emerald-50 border-emerald-200 font-medium'
    };
  };

  const filteredApps = apps.filter((app) => {
    const matchesSearch =
      app.application_no.toLowerCase().includes(search.toLowerCase()) ||
      (app.institution_name && app.institution_name.toLowerCase().includes(search.toLowerCase()));

    const matchesRoute = selectedRoute === 'ALL' || app.route_name === selectedRoute;
    const matchesStage = selectedStage === 'ALL' || app.current_stage === selectedStage;

    const slaMeta = getSlaMeta(app.stage_due_date, app.status);
    const matchesSla =
      selectedSla === 'ALL' ||
      (selectedSla === 'RED' && slaMeta.state === 'RED') ||
      (selectedSla === 'AMBER' && slaMeta.state === 'AMBER') ||
      (selectedSla === 'ON_TRACK' && slaMeta.state === 'ON_TRACK');

    return matchesSearch && matchesRoute && matchesStage && matchesSla;
  });

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 leading-tight">Institutional Applications Dossier</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time scrutiny queue, stage timeline monitoring, and statutory decision records.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="font-semibold text-slate-500">Showing {filteredApps.length} of {apps.length} cases</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3">
          {/* Search */}
          <div className="lg:col-span-4 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by Application No. or Institute Name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
            />
          </div>

          {/* Route Filter */}
          <div className="lg:col-span-3">
            <select
              value={selectedRoute}
              onChange={(e) => setSelectedRoute(e.target.value)}
              className="w-full py-2 px-3 text-xs border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-hidden bg-white text-slate-700"
            >
              <option value="ALL">All Routes</option>
              <option value="Only Scrutiny">Only Scrutiny</option>
              <option value="Scrutiny+EVC">Scrutiny + EVC</option>
              <option value="EVC+SAC/SHC">EVC + SAC/SHC</option>
              <option value="Only EVC">Only EVC</option>
            </select>
          </div>

          {/* Stage Filter */}
          <div className="lg:col-span-3">
            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="w-full py-2 px-3 text-xs border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-hidden bg-white text-slate-700"
            >
              <option value="ALL">All Stages</option>
              <option value="Preliminary Scrutiny">Preliminary Scrutiny</option>
              <option value="Scrutiny Committee Review">Scrutiny Committee Review</option>
              <option value="Re-Scrutiny">Re-Scrutiny</option>
              <option value="EVC Queue">EVC Queue</option>
              <option value="EVC Inspection">EVC Inspection</option>
              <option value="Regional Committee Review">Regional Committee Review</option>
              <option value="SAC/SHC Review">SAC/SHC Review</option>
              <option value="Final Approval">Final Approval</option>
            </select>
          </div>

          {/* SLA Filter */}
          <div className="lg:col-span-2">
            <select
              value={selectedSla}
              onChange={(e) => setSelectedSla(e.target.value)}
              className="w-full py-2 px-3 text-xs border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-hidden bg-white text-slate-700"
            >
              <option value="ALL">All SLA States</option>
              <option value="RED">🚨 Overdue (Red)</option>
              <option value="AMBER">⚠️ Near SLA (Amber)</option>
              <option value="ON_TRACK">✅ On Track</option>
            </select>
          </div>
        </div>
      </div>

      {/* Applications Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading applications...</div>
        ) : filteredApps.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">No applications match the selected criteria.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Application Details</th>
                  <th className="py-3 px-4">Institution</th>
                  <th className="py-3 px-4">Approval Route</th>
                  <th className="py-3 px-4">Current Stage</th>
                  <th className="py-3 px-4">SLA Deadline</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredApps.map((app) => {
                  const sla = getSlaMeta(app.stage_due_date, app.status);
                  return (
                    <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-mono font-bold text-slate-900 text-xs">{app.application_no}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          Submitted: {new Date(app.submitted_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="font-semibold text-slate-800 line-clamp-1">{app.institution_name}</div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          {app.priority === 'HIGH' && (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 bg-amber-100 text-amber-800 text-[10px] font-bold rounded">
                              <Sparkles className="w-2.5 h-2.5" /> High Priority
                            </span>
                          )}
                          <span className="text-[10px] text-slate-400 font-mono">ID: {app.institution_id}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          {app.route_name}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-800">{app.current_stage}</div>
                        <div className="mt-0.5">
                          {app.status === 'REVERTED' ? (
                            <span className="text-[10px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">
                              REVERTED (Re-Scrutiny)
                            </span>
                          ) : app.status === 'APPROVED' ? (
                            <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">
                              APPROVED
                            </span>
                          ) : (
                            <span className="text-[10px] font-medium text-slate-500">In Progress</span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-block px-2.5 py-1 rounded-md text-[11px] border ${sla.color}`}>
                          {sla.label}
                        </span>
                        {app.stage_due_date && (
                          <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
                            Due: {new Date(app.stage_due_date).toLocaleDateString()}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          to={`/applications/${app.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-blue-600 hover:text-white text-slate-700 rounded-lg text-xs font-bold transition-all shadow-2xs"
                        >
                          <span>Review</span>
                          <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
