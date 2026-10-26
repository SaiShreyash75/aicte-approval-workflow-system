import React, { useEffect, useState } from 'react';
import {
  FileText,
  AlertTriangle,
  Clock,
  CheckCircle2,
  TrendingUp,
  AlertOctagon,
  Users,
  ShieldCheck,
  Building,
  ArrowRight
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';

const AGEING_COLORS = {
  '0-7 days': '#10b981',   // emerald
  '8-15 days': '#f59e0b',  // amber
  '16-30 days': '#f97316', // orange
  '30+ days': '#ef4444',   // red
};

export default function Dashboard() {
  const { user, refreshKey } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);
      try {
        const res = await api.get('/dashboard/summary');
        setData(res.data);
      } catch (err) {
        console.error("Dashboard fetch error", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [refreshKey]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-500">Loading Statutory Intelligence Dashboard...</p>
        </div>
      </div>
    );
  }

  const kpi = data?.kpi || {};
  const ageingData = data?.ageing_buckets || [];
  const stageData = data?.by_stage || [];
  const regionData = data?.by_region || [];
  const workload = data?.officer_workload || [];
  const bottlenecks = data?.bottleneck_stages || [];

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Welcome & Role Context Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 uppercase tracking-wider">
              {data?.user_role} Workspace
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs font-medium text-slate-500">Session 2026-27</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 leading-tight">
            Welcome back, {data?.user_name}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time compliance monitoring, bottleneck tracking, and workflow governance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/applications"
            className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5"
          >
            <span>Review Applications</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Bottleneck Alert Banner */}
      {kpi.primary_bottleneck && kpi.primary_bottleneck !== 'None' && (
        <div className="bg-rose-50 border-l-4 border-rose-600 p-4 rounded-xl flex items-start gap-3 shadow-xs">
          <AlertOctagon className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-rose-900">
                Critical Stage Bottleneck Detected: {kpi.primary_bottleneck}
              </h4>
              <span className="text-[10px] font-bold px-1.5 py-0.5 bg-rose-200 text-rose-800 rounded">
                High Latency
              </span>
            </div>
            <p className="text-xs text-rose-800 mt-1">
              This stage currently has the highest volume of statutory SLA deadline breaches. Immediate officer scrutiny or SAC hearing escalation recommended.
            </p>
          </div>
          <Link
            to={`/applications?stage=${encodeURIComponent(kpi.primary_bottleneck)}`}
            className="text-xs font-bold text-rose-700 hover:text-rose-900 underline shrink-0 whitespace-nowrap"
          >
            Filter Stage Cases →
          </Link>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total & Pending */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Active Applications</span>
            <FileText className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">{kpi.pending_applications}</div>
          <div className="flex items-center gap-2 mt-2 text-[11px] text-slate-500">
            <span>Total: <strong>{kpi.total_applications}</strong></span>
            <span>•</span>
            <span className="text-emerald-600 font-semibold">{kpi.approved_applications} Approved</span>
          </div>
        </div>

        {/* Card 2: SLA Overdue (Red) */}
        <div className="bg-white p-4 rounded-2xl border border-rose-200 shadow-xs hover:border-rose-300 transition-all bg-gradient-to-br from-white to-rose-50/30">
          <div className="flex items-center justify-between text-rose-600 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-700">SLA Overdue (Breach)</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-2xl font-black text-rose-600">{kpi.overdue_sla_count}</div>
          <div className="text-[11px] text-rose-700 font-medium mt-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-600 animate-pulse" />
            <span>Requires Human Officer Decision</span>
          </div>
        </div>

        {/* Card 3: SLA Approaching (Amber) */}
        <div className="bg-white p-4 rounded-2xl border border-amber-200 shadow-xs hover:border-amber-300 transition-all bg-gradient-to-br from-white to-amber-50/30">
          <div className="flex items-center justify-between text-amber-600 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-800">Near SLA Target</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-black text-amber-600">{kpi.sla_amber_count}</div>
          <div className="text-[11px] text-amber-800 font-medium mt-2">
            ≤ 2 Days remaining in current stage
          </div>
        </div>

        {/* Card 4: Compliance Deficiencies */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Compliance Alerts</span>
            <ShieldCheck className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            {kpi.overdue_undertakings_count + kpi.expiring_documents_count}
          </div>
          <div className="text-[11px] text-slate-500 mt-2 flex items-center gap-1.5 flex-wrap">
            <span className="text-purple-700 font-semibold">{kpi.overdue_undertakings_count} Undertakings</span>
            <span>•</span>
            <span className="text-amber-700 font-semibold">{kpi.expiring_documents_count} Certs Expiring</span>
          </div>
        </div>
      </div>

      {/* Charts Section: Stage-wise Pendency & Ageing Buckets */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Stage-wise Pendency Bar Chart */}
        <div className="lg:col-span-7 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-sm text-slate-900">Stage-Wise Application Pendency</h3>
              <p className="text-[11px] text-slate-500">Volume of active applications across workflow stages</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stageData} margin={{ top: 10, right: 10, left: -20, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="stage"
                  tick={{ fontSize: 9, fill: '#64748b' }}
                  angle={-25}
                  textAnchor="end"
                  interval={0}
                />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="count" name="Applications" fill="#2563eb" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Ageing Buckets Chart */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-sm text-slate-900">Ageing Analysis</h3>
              <p className="text-[11px] text-slate-500">Pending duration in current stage</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ageingData} margin={{ top: 10, right: 10, left: -20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="count" name="Applications">
                  {ageingData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={AGEING_COLORS[entry.bucket] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Regional & Officer Workload Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Regional Distribution */}
        <div className="lg:col-span-6 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-bold text-sm text-slate-900">Jurisdiction Workload (Region-Wise)</h3>
              <p className="text-[11px] text-slate-500">Applications distributed across 4 regional offices</p>
            </div>
          </div>
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={regionData} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} allowDecimals={false} />
                <YAxis type="category" dataKey="region" tick={{ fontSize: 10, fill: '#334155' }} width={110} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="count" name="Applications" fill="#4f46e5" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Officer Workload Breakdown */}
        <div className="lg:col-span-6 bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-bold text-sm text-slate-900">Officer Workload & Allocation</h3>
                <p className="text-[11px] text-slate-500">Active pending files allocated per competent authority</p>
              </div>
              <Users className="w-4 h-4 text-slate-400" />
            </div>

            <div className="divide-y divide-slate-100 max-h-56 overflow-y-auto">
              {workload.map((off, idx) => (
                <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-bold text-slate-800">{off.officer_name}</div>
                    <div className="text-[11px] text-slate-500">{off.role} • {off.region}</div>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-slate-900 text-sm">{off.active_cases}</span>
                    <span className="text-[10px] text-slate-400 block">active files</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 text-center">
            Automatic workload balancing evaluated based on regional jurisdiction.
          </div>
        </div>
      </div>
    </div>
  );
}
