import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  CalendarCheck2,
  ShieldAlert,
  Bell,
  BarChart3,
  History,
  Building2,
  Scale
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Sidebar() {
  const { user } = useAuth();
  const role = user?.role || '';

  const links = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['Admin', 'Regional Officer', 'Bureau Officer', 'Committee Member', 'Institution'] },
    { to: '/applications', label: 'Applications', icon: FileText, roles: ['Admin', 'Regional Officer', 'Bureau Officer', 'Committee Member', 'Institution'] },
    { to: '/evc', label: 'EVC Inspections', icon: CalendarCheck2, roles: ['Admin', 'Regional Officer', 'Bureau Officer', 'Committee Member'] },
    { to: '/compliance', label: 'Compliance & Documents', icon: ShieldAlert, roles: ['Admin', 'Regional Officer', 'Bureau Officer', 'Institution'] },
    { to: '/notifications', label: 'Notifications & Alerts', icon: Bell, roles: ['Admin', 'Regional Officer', 'Bureau Officer', 'Committee Member', 'Institution'] },
    { to: '/reports', label: 'Reports & Exports', icon: BarChart3, roles: ['Admin', 'Regional Officer', 'Bureau Officer'] },
    { to: '/audit', label: 'Immutable Audit Trail', icon: History, roles: ['Admin', 'Regional Officer', 'Bureau Officer'] },
  ];

  const filteredLinks = links.filter((l) => l.roles.includes(role));

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-[calc(100vh-80px)] border-r border-slate-800">
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <Scale className="w-5 h-5 text-amber-400 shrink-0" />
          <div className="text-xs">
            <div className="font-bold text-white tracking-wide">STATUTORY DESK</div>
            <div className="text-[10px] text-amber-400 font-semibold uppercase">{role}</div>
          </div>
        </div>
      </div>

      <nav className="p-3 space-y-1 flex-1">
        {filteredLinks.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40 text-[11px] text-slate-400 space-y-1">
        <div className="flex items-center gap-1.5 font-bold text-slate-300 text-xs">
          <Building2 className="w-3.5 h-3.5 text-blue-400" />
          <span>Session 2026–27</span>
        </div>
        <p className="text-[10px] text-slate-400 leading-tight">
          AICTE Centralized Approval Workflow & Rule Engine
        </p>
      </div>
    </aside>
  );
}
