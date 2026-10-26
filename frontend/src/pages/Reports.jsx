import React, { useState, useEffect } from 'react';
import { Download, FileText, AlertTriangle, CalendarCheck2, Globe2 } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Reports() {
  const { refreshKey } = useAuth();
  const [pendency, setPendency] = useState(null);
  const [overdue, setOverdue] = useState(null);
  const [evc, setEvc] = useState(null);
  const [regionPerf, setRegionPerf] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      setLoading(true);
      try {
        const [pRes, oRes, eRes, rRes] = await Promise.all([
          api.get('/reports/pendency'),
          api.get('/reports/overdue'),
          api.get('/reports/evc'),
          api.get('/reports/region-performance')
        ]);
        setPendency(pRes.data);
        setOverdue(oRes.data);
        setEvc(eRes.data);
        setRegionPerf(rRes.data);
      } catch (err) {
        console.error("Error fetching reports", err);
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, [refreshKey]);

  const downloadFile = (endpoint, defaultFilename) => {
    const token = localStorage.getItem('aicte_token');
    fetch(`/api/reports/${endpoint}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((res) => res.blob())
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = defaultFilename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      })
      .catch((e) => alert("Download failed: " + e.message));
  };

  if (loading) {
    return <div className="p-12 text-center text-xs text-slate-500">Loading statutory reports dossiers...</div>;
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 leading-tight">Statutory Reports & Regulatory Export Center</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Generate official statutory dossiers, export pendency and bottleneck metrics, and download ReportLab PDF summaries.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Report 1: Pendency & Ageing */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                Workflow Analytics
              </span>
              <FileText className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="font-bold text-sm text-slate-900">Application Pendency & Ageing Dossier</h3>
            <p className="text-xs text-slate-500 mt-1">
              Detailed breakdown of all active applications, stage residence duration, and ageing buckets.
            </p>
            <div className="mt-3 text-xs text-slate-700">
              Total Active Files: <strong>{pendency?.total_pending || 0}</strong>
            </div>
          </div>
          <div className="pt-4 mt-4 border-t border-slate-100 flex items-center gap-2">
            <button
              onClick={() => downloadFile('pendency/csv', 'aicte_pendency_report.csv')}
              className="flex-1 py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Export CSV
            </button>
            <button
              onClick={() => downloadFile('pendency/pdf', 'aicte_pendency_report.pdf')}
              className="flex-1 py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 transition-colors shadow-xs"
            >
              <Download className="w-3.5 h-3.5" /> Download PDF
            </button>
          </div>
        </div>

        {/* Report 2: Overdue Dossier */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-rose-700 bg-rose-50 px-2 py-0.5 rounded">
                Non-Compliance Escalation
              </span>
              <AlertTriangle className="w-4 h-4 text-rose-500" />
            </div>
            <h3 className="font-bold text-sm text-slate-900">Statutory Non-Compliance & Overdue Cases</h3>
            <p className="text-xs text-slate-500 mt-1">
              Consolidated audit list of applications past SLA, breached undertakings, expired leases, and delayed EVCs.
            </p>
            <div className="mt-3 text-xs text-rose-700 font-bold">
              Total Overdue Breaches: <strong>{overdue?.total_overdue || 0}</strong>
            </div>
          </div>
          <div className="pt-4 mt-4 border-t border-slate-100 flex items-center gap-2">
            <button
              onClick={() => downloadFile('overdue/csv', 'aicte_overdue_cases.csv')}
              className="flex-1 py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Export CSV
            </button>
            <button
              onClick={() => downloadFile('overdue/pdf', 'aicte_overdue_cases.pdf')}
              className="flex-1 py-2 px-3 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 transition-colors shadow-xs"
            >
              <Download className="w-3.5 h-3.5" /> Download PDF
            </button>
          </div>
        </div>

        {/* Report 3: EVC Status */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-50 px-2 py-0.5 rounded">
                Inspection Operations
              </span>
              <CalendarCheck2 className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="font-bold text-sm text-slate-900">Expert Visit Committee (EVC) Status</h3>
            <p className="text-xs text-slate-500 mt-1">
              Status breakdown of queued, scheduled, and completed inspections with committee allocations.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-slate-100">
            <button
              onClick={() => downloadFile('evc/csv', 'aicte_evc_status.csv')}
              className="w-full py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Export EVC Status CSV
            </button>
          </div>
        </div>

        {/* Report 4: Region Performance */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                Jurisdiction Benchmark
              </span>
              <Globe2 className="w-4 h-4 text-slate-400" />
            </div>
            <h3 className="font-bold text-sm text-slate-900">Region-Wise Performance & Disposal Rate</h3>
            <p className="text-xs text-slate-500 mt-1">
              Comparative benchmark of Northern, Western, Southern, and Eastern offices on disposal efficiency.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-slate-100">
            <button
              onClick={() => downloadFile('region-performance/csv', 'aicte_region_performance.csv')}
              className="w-full py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold rounded-xl flex items-center justify-center gap-1.5 transition-colors"
            >
              <Download className="w-3.5 h-3.5" /> Export Region Benchmark CSV
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
