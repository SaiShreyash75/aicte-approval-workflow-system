import React, { useState } from 'react';
import { Calendar, Clock, LogOut, ShieldCheck, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import NotificationDropdown from './NotificationDropdown';
import SimulateTimeModal from './SimulateTimeModal';

export default function TopBar() {
  const { user, systemTime, logout } = useAuth();
  const [showSimModal, setShowSimModal] = useState(false);

  const canSimulate = user?.role === 'Admin' || user?.role === 'Bureau Officer';

  return (
    <>
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="px-4 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-blue-900 text-white font-bold flex items-center justify-center text-base shadow-xs">
              AICTE
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-900 leading-tight">
                AICTE Approval & Compliance System
              </h1>
              <p className="text-[11px] text-slate-500 hidden sm:block">
                All India Council for Technical Education • Statutory Scrutiny Portal
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            {/* Virtual Clock Display */}
            <div className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200/80 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs">
              <Clock className="w-4 h-4 text-slate-500" />
              <div className="flex flex-col text-left">
                <span className="font-mono font-semibold text-slate-800 text-[11px] sm:text-xs">
                  {systemTime?.formatted_date ? systemTime.formatted_date.split(' ')[0] : 'Loading...'}
                </span>
                {systemTime?.is_simulated ? (
                  <span className="text-[9px] text-amber-700 font-bold uppercase tracking-wider">Simulated</span>
                ) : (
                  <span className="text-[9px] text-emerald-600 font-medium">Real Time</span>
                )}
              </div>
            </div>

            {/* Admin Simulate Time Button */}
            {canSimulate && (
              <button
                onClick={() => setShowSimModal(true)}
                className="flex items-center gap-1.5 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold px-2.5 py-1.5 rounded-lg text-xs shadow-xs transition-colors"
                title="Open Live Time Simulator Panel"
              >
                <Calendar className="w-3.5 h-3.5" />
                <span className="hidden md:inline">Simulate Time</span>
              </button>
            )}

            {/* In-App Notifications Bell */}
            <NotificationDropdown />

            {/* User Profile & Role */}
            <div className="h-7 w-px bg-slate-200" />
            <div className="flex items-center gap-2">
              <div className="text-right hidden sm:block">
                <div className="text-xs font-bold text-slate-800 leading-none">{user?.full_name?.split(' ')[0]}</div>
                <div className="text-[10px] font-semibold text-blue-700 uppercase tracking-wider mt-0.5">{user?.role}</div>
              </div>
              <button
                onClick={logout}
                className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Simulator Modal */}
      <SimulateTimeModal isOpen={showSimModal} onClose={() => setShowSimModal(false)} />
    </>
  );
}
