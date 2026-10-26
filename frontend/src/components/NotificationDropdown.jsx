import React, { useState, useEffect } from 'react';
import { Bell, Check, CheckCheck, Clock, ExternalLink } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function NotificationDropdown() {
  const { refreshKey } = useAuth();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifs = async () => {
    try {
      const [listRes, countRes] = await Promise.all([
        api.get('/notifications?limit=30'),
        api.get('/notifications/unread-count')
      ]);
      setNotifications(listRes.data);
      setUnreadCount(countRes.data.unread_count);
    } catch (e) {
      console.error("Error fetching notifications", e);
    }
  };

  useEffect(() => {
    fetchNotifs();
  }, [refreshKey]);

  const markRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/mark-read`);
      fetchNotifs();
    } catch (e) {
      console.error(e);
    }
  };

  const markAllRead = async () => {
    try {
      await api.post('/notifications/mark-all-read');
      fetchNotifs();
    } catch (e) {
      console.error(e);
    }
  };

  const getEscalationBadge = (level) => {
    switch (level) {
      case 4:
        return <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-purple-100 text-purple-800 border border-purple-300">L4 APEX</span>;
      case 3:
        return <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-rose-100 text-rose-800 border border-rose-300">L3 BUREAU</span>;
      case 2:
        return <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800 border border-amber-300">L2 REGIONAL</span>;
      default:
        return <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-blue-100 text-blue-800 border border-blue-200">L1 NOTICE</span>;
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-colors"
        title="Notifications & Escalation Alerts"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 min-w-4 px-1 items-center justify-center rounded-full bg-rose-600 text-[10px] font-bold text-white shadow-xs">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-slate-200 z-50 overflow-hidden">
          <div className="p-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-800 text-sm">Notifications & Escalations</span>
              <span className="text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full font-medium">
                {unreadCount} unread
              </span>
            </div>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
              >
                <CheckCheck className="w-3.5 h-3.5" /> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-slate-400 text-sm">No notifications available</div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className={`p-3 text-xs transition-colors ${
                    n.is_read ? 'bg-white opacity-80' : 'bg-blue-50/40 hover:bg-blue-50/70'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {getEscalationBadge(n.escalation_level)}
                      <span className="font-bold text-slate-700">{n.entity_type}</span>
                      <span className="text-[10px] text-slate-500 font-mono">#{n.entity_id}</span>
                    </div>
                    {!n.is_read && (
                      <button
                        onClick={() => markRead(n.id)}
                        className="text-slate-400 hover:text-blue-600 p-0.5"
                        title="Mark as read"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <div className="font-semibold text-slate-900 mb-0.5">{n.title}</div>
                  <div className="text-slate-600 text-[11px] leading-relaxed mb-1.5">{n.message}</div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(n.created_at).toLocaleDateString()} {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    {n.is_closed ? (
                      <span className="text-emerald-600 font-medium bg-emerald-50 px-1 rounded">Resolved</span>
                    ) : (
                      <span className="text-amber-600 font-medium">Active</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-2 bg-slate-50 border-t border-slate-200 text-center">
            <span className="text-[11px] text-slate-500">Escalation Ladder: Institution → RO → Bureau → Apex</span>
          </div>
        </div>
      )}
    </div>
  );
}
