import React, { useState, useEffect } from 'react';
import { History, Shield, Lock, Search } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function AuditTrail() {
  const { refreshKey } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      try {
        const res = await api.get('/audit-logs?limit=150');
        setLogs(res.data);
      } catch (e) {
        console.error("Error loading audit logs", e);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, [refreshKey]);

  const filteredLogs = logs.filter((log) => {
    const term = search.toLowerCase();
    return (
      log.action.toLowerCase().includes(term) ||
      log.entity_type.toLowerCase().includes(term) ||
      (log.remarks && log.remarks.toLowerCase().includes(term)) ||
      log.role.toLowerCase().includes(term)
    );
  });

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200 mb-1">
            <Lock className="w-3 h-3" /> Append-Only Immutable Ledger
          </div>
          <h2 className="text-xl font-bold text-slate-900 leading-tight">Statutory Audit Trail</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Every submission, scrutiny transition, EVC schedule, alert, and closure is permanently logged.
          </p>
        </div>
        <div className="w-72">
          <input
            type="text"
            placeholder="Search audit trail by action or role..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-xs p-2 border border-slate-300 rounded-xl"
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading audit ledger...</div>
        ) : filteredLogs.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">No audit entries found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Log ID</th>
                  <th className="py-2.5 px-3">Timestamp (UTC)</th>
                  <th className="py-2.5 px-3">Actor / Role</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Entity Type & ID</th>
                  <th className="py-2.5 px-3">State Transition</th>
                  <th className="py-2.5 px-3">Audit Narrative</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {filteredLogs.map((l) => (
                  <tr key={l.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-400">#{l.id}</td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500">
                      {new Date(l.created_at).toLocaleDateString()}{' '}
                      {new Date(l.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-bold text-slate-800">{l.role}</span>
                      {l.user_id && <span className="text-[10px] text-slate-400 block font-mono">User #{l.user_id}</span>}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-800 border border-slate-200">
                        {l.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-700">
                      {l.entity_type} #{l.entity_id || '-'}
                    </td>
                    <td className="py-2.5 px-3 text-[11px] max-w-xs text-slate-600 truncate">
                      {l.new_state || '-'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 italic max-w-sm truncate">
                      {l.remarks || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
