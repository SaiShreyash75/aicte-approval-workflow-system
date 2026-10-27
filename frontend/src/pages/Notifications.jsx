import React, { useState, useEffect } from 'react';
import {
  Bell,
  Check,
  CheckCheck,
  Filter,
  RefreshCw,
  Clock,
  AlertTriangle,
  ShieldAlert,
  FileText,
  Building,
  CheckCircle2,
  CalendarCheck2
} from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Notifications() {
  const { refreshKey, triggerGlobalRefresh } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters state
  const [filterRead, setFilterRead] = useState('ALL'); // ALL, UNREAD, READ
  const [filterLevel, setFilterLevel] = useState('ALL'); // ALL, 1, 2, 3, 4
  const [filterEntity, setFilterEntity] = useState('ALL'); // ALL, APPLICATION, UNDERTAKING, DOCUMENT, EVC
  const [filterClosed, setFilterClosed] = useState('ALL'); // ALL, ACTIVE, CLOSED
  const [searchQuery, setSearchQuery] = useState('');

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const res = await api.get('/notifications?limit=200');
      setNotifications(res.data);
    } catch (e) {
      console.error('Error fetching notifications:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, [refreshKey]);

  const handleMarkRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/mark-read`);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      triggerGlobalRefresh();
    } catch (e) {
      console.error('Failed to mark read', e);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.post('/notifications/mark-all-read');
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      triggerGlobalRefresh();
    } catch (e) {
      console.error('Failed to mark all read', e);
    }
  };

  const getEscalationBadge = (level) => {
    switch (Number(level)) {
      case 4:
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-100 text-purple-800 border border-purple-300">
            L4 APEX
          </span>
        );
      case 3:
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-100 text-rose-800 border border-rose-300">
            L3 BUREAU
          </span>
        );
      case 2:
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-100 text-amber-800 border border-amber-300">
            L2 REGIONAL
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-blue-100 text-blue-800 border border-blue-200">
            L1 NOTICE
          </span>
        );
    }
  };

  // Distinct entity types
  const entityTypes = Array.from(
    new Set(notifications.map((n) => n.entity_type).filter(Boolean))
  );

  // Filtered notifications
  const filtered = notifications.filter((n) => {
    // Read filter
    if (filterRead === 'UNREAD' && n.is_read) return false;
    if (filterRead === 'READ' && !n.is_read) return false;

    // Escalation level filter
    if (filterLevel !== 'ALL' && n.escalation_level !== Number(filterLevel)) return false;

    // Entity type filter
    if (filterEntity !== 'ALL' && n.entity_type !== filterEntity) return false;

    // Closed filter
    if (filterClosed === 'ACTIVE' && n.is_closed) return false;
    if (filterClosed === 'CLOSED' && !n.is_closed) return false;

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = n.title?.toLowerCase().includes(q);
      const matchMsg = n.message?.toLowerCase().includes(q);
      const matchEntity = n.entity_type?.toLowerCase().includes(q);
      const matchTrigger = n.trigger_key?.toLowerCase().includes(q);
      if (!matchTitle && !matchMsg && !matchEntity && !matchTrigger) return false;
    }

    return true;
  });

  const totalUnread = notifications.filter((n) => !n.is_read).length;
  const totalEscalated = notifications.filter((n) => n.escalation_level >= 2).length;
  const totalClosed = notifications.filter((n) => n.is_closed).length;

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 leading-tight flex items-center gap-2">
            <Bell className="w-5 h-5 text-blue-600" />
            Statutory Notifications & Escalation Alerts
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time multi-tier regulatory alerts, stage SLA breaches, undertaking deadlines, and EVC tracking.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {totalUnread > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 transition-colors flex items-center gap-1.5"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark All Read
            </button>
          )}
          <button
            onClick={fetchNotifications}
            className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Metric summary counters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Alerts</div>
          <div className="text-2xl font-bold text-slate-900 mt-1">{notifications.length}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Unread Alerts</div>
          <div className="text-2xl font-bold text-blue-600 mt-1">{totalUnread}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Escalated (L2–L4)</div>
          <div className="text-2xl font-bold text-rose-600 mt-1">{totalEscalated}</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Resolved / Closed</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">{totalClosed}</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <span>Filters</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Read / Unread Filter */}
          <div>
            <label className="block text-[10px] font-semibold uppercase text-slate-500 mb-1">Status</label>
            <select
              value={filterRead}
              onChange={(e) => setFilterRead(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All (Read & Unread)</option>
              <option value="UNREAD">Unread Only</option>
              <option value="READ">Read Only</option>
            </select>
          </div>

          {/* Escalation Level Filter */}
          <div>
            <label className="block text-[10px] font-semibold uppercase text-slate-500 mb-1">Escalation Level</label>
            <select
              value={filterLevel}
              onChange={(e) => setFilterLevel(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Levels</option>
              <option value="1">L1 - Notice / Reminder</option>
              <option value="2">L2 - Regional Officer</option>
              <option value="3">L3 - Bureau Officer</option>
              <option value="4">L4 - Apex / Member Sec</option>
            </select>
          </div>

          {/* Entity Type Filter */}
          <div>
            <label className="block text-[10px] font-semibold uppercase text-slate-500 mb-1">Entity Type</label>
            <select
              value={filterEntity}
              onChange={(e) => setFilterEntity(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Entities</option>
              {entityTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          {/* Closed / Active Filter */}
          <div>
            <label className="block text-[10px] font-semibold uppercase text-slate-500 mb-1">Resolution State</label>
            <select
              value={filterClosed}
              onChange={(e) => setFilterClosed(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All (Active & Closed)</option>
              <option value="ACTIVE">Active Only</option>
              <option value="CLOSED">Closed / Resolved</option>
            </select>
          </div>

          {/* Search Query */}
          <div>
            <label className="block text-[10px] font-semibold uppercase text-slate-500 mb-1">Search Keyword</label>
            <input
              type="text"
              placeholder="Filter title or entity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-200 rounded-lg p-2 text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Notifications List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-500">Loading statutory alerts...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-500">
            No notifications match the specified filter criteria.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filtered.map((n) => (
              <div
                key={n.id}
                className={`p-4 transition-colors flex flex-col sm:flex-row sm:items-start justify-between gap-3 ${
                  n.is_read ? 'bg-white opacity-85' : 'bg-blue-50/30 hover:bg-blue-50/60'
                }`}
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {getEscalationBadge(n.escalation_level)}
                    <span className="text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
                      {n.entity_type} #{n.entity_id}
                    </span>
                    <span className="text-[10px] text-slate-500 font-medium">
                      Recipient: <strong className="text-slate-700">{n.recipient_role}</strong>
                    </span>
                    {n.is_closed ? (
                      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Resolved
                      </span>
                    ) : (
                      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full flex items-center gap-1">
                        <Clock className="w-3 h-3" /> Active
                      </span>
                    )}
                  </div>

                  <div className="font-semibold text-sm text-slate-900">{n.title}</div>
                  <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">{n.message}</p>

                  <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(n.created_at).toLocaleDateString()} {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {n.trigger_key && (
                      <span className="font-mono text-[10px] text-slate-400">
                        Trigger: {n.trigger_key}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  {!n.is_read && (
                    <button
                      onClick={() => handleMarkRead(n.id)}
                      className="px-2.5 py-1 text-xs font-medium rounded-lg text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 transition-colors flex items-center gap-1"
                      title="Mark as Read"
                    >
                      <Check className="w-3.5 h-3.5" />
                      Mark Read
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
