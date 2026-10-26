import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCcw,
  XCircle,
  FileText,
  Calendar,
  Building,
  History,
  ShieldCheck,
  Send,
  Sparkles
} from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function ApplicationDetail() {
  const { id } = useParams();
  const { user, systemTime, refreshKey, triggerGlobalRefresh } = useAuth();
  const [app, setApp] = useState(null);
  const [loading, setLoading] = useState(true);

  // Transition modal state
  const [modalAction, setModalAction] = useState(null); // 'APPROVE', 'REVERT', 'REJECT'
  const [remarks, setRemarks] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState('');

  const fetchDetail = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/applications/${id}`);
      setApp(res.data);
    } catch (e) {
      console.error("Error fetching detail", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [id, refreshKey]);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-500">Loading statutory application dossier...</p>
        </div>
      </div>
    );
  }

  if (!app) {
    return (
      <div className="p-8 text-center text-slate-500 text-sm">
        Application dossier not found.{' '}
        <Link to="/applications" className="text-blue-600 underline">Back to List</Link>
      </div>
    );
  }

  const isRoleAllowed = app.allowed_roles?.includes(user?.role) || user?.role === 'Admin';

  const handleExecuteTransition = async (e) => {
    e.preventDefault();
    if (!remarks.trim() && (modalAction === 'REVERT' || modalAction === 'REJECT')) {
      setActionError('Mandatory remarks / reasons required for Revert or Reject decisions.');
      return;
    }
    setSubmitting(true);
    setActionError('');
    try {
      await api.post(`/applications/${id}/transition`, {
        action: modalAction,
        remarks: remarks.trim() || 'Approved to advance to next statutory stage.'
      });
      setModalAction(null);
      setRemarks('');
      triggerGlobalRefresh();
    } catch (err) {
      setActionError(err.response?.data?.detail || 'Failed to process workflow transition.');
    } finally {
      setSubmitting(false);
    }
  };

  // Stepper logic based on route
  const getRouteSteps = () => {
    if (app.route_name === 'Only Scrutiny') {
      return ['Preliminary Scrutiny', 'Scrutiny Committee Review', 'Final Approval'];
    } else if (app.route_name === 'Scrutiny+EVC') {
      return ['Preliminary Scrutiny', 'EVC Queue', 'EVC Inspection', 'Regional Committee Review', 'Final Approval'];
    } else if (app.route_name === 'EVC+SAC/SHC') {
      return ['EVC Queue', 'EVC Inspection', 'SAC/SHC Review', 'Final Approval'];
    } else if (app.route_name === 'Only EVC') {
      return ['EVC Queue', 'EVC Inspection', 'Final Approval'];
    }
    return [app.current_stage];
  };

  const steps = getRouteSteps();
  const currentStepIndex = steps.indexOf(app.current_stage);

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Back button & Action summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Link
          to="/applications"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Applications Queue</span>
        </Link>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Dossier ID: #{app.id}</span>
          <span className="text-xs bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded-md">
            {app.route_name}
          </span>
          {app.priority === 'HIGH' && (
            <span className="text-xs bg-amber-100 text-amber-900 font-bold px-2 py-0.5 rounded-md flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-amber-600" /> High Priority
            </span>
          )}
        </div>
      </div>

      {/* Main Details Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">
              Application Ref. No.
            </div>
            <h2 className="text-2xl font-black text-slate-900 font-mono tracking-tight">{app.application_no}</h2>
            <div className="text-sm font-semibold text-slate-700 mt-1 flex items-center gap-2 flex-wrap">
              <span>{app.institution_name}</span>
              <span className="text-slate-300">•</span>
              <span className="text-xs text-slate-500 font-mono font-medium">Code: {app.institution_code}</span>
              <span className="text-slate-300">•</span>
              <span className="text-xs text-slate-500">{app.region_name}</span>
            </div>
          </div>

          <div className="flex flex-col sm:items-end text-left sm:text-right">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Overall Status</div>
            <div className="text-base font-bold text-slate-900 mt-0.5">
              {app.status === 'APPROVED' ? (
                <span className="text-emerald-700 bg-emerald-100 px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Approved by Authority
                </span>
              ) : app.status === 'REVERTED' ? (
                <span className="text-amber-700 bg-amber-100 px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1">
                  <RotateCcw className="w-3.5 h-3.5" /> Reverted for Rectification
                </span>
              ) : (
                <span className="text-blue-700 bg-blue-100 px-3 py-1 rounded-full text-xs font-bold inline-flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> In Progress (Stage: {app.current_stage})
                </span>
              )}
            </div>
            {app.stage_due_date && (
              <div className="text-[11px] text-slate-500 mt-1 font-mono">
                Stage Target Deadline: {new Date(app.stage_due_date).toLocaleDateString()}
              </div>
            )}
          </div>
        </div>

        {/* Workflow Stepper */}
        <div className="pt-4 border-t border-slate-100">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Approval Workflow Route Pipeline ({app.route_name})
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
            {steps.map((st, idx) => {
              const isPast = idx < currentStepIndex || app.status === 'APPROVED';
              const isCurrent = idx === currentStepIndex && app.status !== 'APPROVED';
              const isReverted = app.status === 'REVERTED' && st === app.current_stage;

              return (
                <div
                  key={st}
                  className={`p-3 rounded-xl border text-xs transition-all ${
                    isReverted
                      ? 'bg-amber-50 border-amber-300 text-amber-900 font-bold'
                      : isCurrent
                      ? 'bg-blue-600 text-white border-blue-600 shadow-md font-bold'
                      : isPast
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200 font-semibold'
                      : 'bg-slate-50 text-slate-400 border-slate-200'
                  }`}
                >
                  <div className="text-[10px] uppercase tracking-wider opacity-80 mb-0.5">
                    Stage {idx + 1}
                  </div>
                  <div className="truncate text-xs">{st}</div>
                  <div className="mt-1 flex items-center gap-1 text-[10px]">
                    {isReverted ? (
                      <span>⚠️ Reverted</span>
                    ) : isCurrent ? (
                      <span>● Active Stage</span>
                    ) : isPast ? (
                      <span className="flex items-center gap-0.5"><CheckCircle2 className="w-3 h-3 text-emerald-600" /> Completed</span>
                    ) : (
                      <span>Pending</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Statutory Decision Workspace & Action Buttons */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="font-bold text-sm text-slate-900">Competent Authority Decision Workspace</h3>
            <p className="text-xs text-slate-500">Every statutory approve, revert, or reject action requires a human officer decision.</p>
          </div>
          <div>
            {isRoleAllowed ? (
              <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-full">
                <CheckCircle2 className="w-3.5 h-3.5" /> Authorized for Decision
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-bold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
                Read-Only Inspection Mode
              </span>
            )}
          </div>
        </div>

        {isRoleAllowed ? (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <div className="text-xs font-bold text-slate-800">
                Authorized Actions for Stage: <span className="text-blue-700">{app.current_stage}</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5">
                Roles permitted: {app.allowed_roles?.join(', ')} • Current user: {user?.full_name} ({user?.role})
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => setModalAction('APPROVE')}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{app.next_stage ? `Approve & Forward to ${app.next_stage}` : 'Grant Final Approval'}</span>
              </button>
              <button
                onClick={() => setModalAction('REVERT')}
                className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 text-xs font-bold rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Revert with Remarks</span>
              </button>
              <button
                onClick={() => setModalAction('REJECT')}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Reject Application</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600">
            ℹ️ <strong>Read-Only Notice:</strong> Actions at stage <strong>"{app.current_stage}"</strong> are authorized only for:{" "}
            <strong>{app.allowed_roles?.join(', ') || 'Admin'}</strong>. Your current role is <strong>"{user?.role}"</strong>.
          </div>
        )}
      </div>

      {/* Case Summary Box */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <h3 className="font-bold text-sm text-slate-900">Auto-Generated Statutory Case Summary</h3>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">Template Generated on Stage Advance</span>
        </div>
        <pre className="p-4 bg-slate-950 text-emerald-400 font-mono text-xs rounded-xl overflow-x-auto whitespace-pre-wrap leading-relaxed border border-slate-800">
          {app.case_summary || 'No case summary generated yet.'}
        </pre>
      </div>

      {/* Stage History & Audit Log */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-slate-700" />
            <h3 className="font-bold text-sm text-slate-900">Stage Transition History & Decisions</h3>
          </div>
          <span className="text-xs text-slate-400">{app.stage_transitions?.length || 0} transitions recorded</span>
        </div>

        {app.stage_transitions && app.stage_transitions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3">From Stage</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">To Stage</th>
                  <th className="py-2.5 px-3">Authorized Officer</th>
                  <th className="py-2.5 px-3">Mandatory Remarks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {app.stage_transitions.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                      {new Date(t.created_at).toLocaleDateString()} {new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-2.5 px-3 text-slate-700">{t.from_stage}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        t.action === 'APPROVE' ? 'bg-emerald-100 text-emerald-800' :
                        t.action === 'REVERT' ? 'bg-amber-100 text-amber-800' :
                        t.action === 'REJECT' ? 'bg-rose-100 text-rose-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {t.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-900 font-bold">{t.to_stage}</td>
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-slate-800">{t.performed_by_name}</div>
                      <div className="text-[10px] text-slate-400">{t.performed_by_role}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700 italic max-w-sm">{t.remarks}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-6 text-xs text-slate-400">No previous stage transitions logged.</div>
        )}
      </div>

      {/* Action Modal (Approve, Revert, Reject) */}
      {modalAction && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className={`p-4 text-white flex items-center justify-between ${
              modalAction === 'APPROVE' ? 'bg-emerald-700' :
              modalAction === 'REVERT' ? 'bg-amber-600' : 'bg-rose-700'
            }`}>
              <h3 className="font-bold text-sm">
                Confirm Statutory Decision: {modalAction} Application
              </h3>
              <button onClick={() => setModalAction(null)} className="text-white/80 hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleExecuteTransition} className="p-5 space-y-4">
              <div>
                <p className="text-xs text-slate-600 leading-relaxed">
                  You are about to execute action <strong>{modalAction}</strong> on application{' '}
                  <strong className="font-mono text-slate-900">{app.application_no}</strong>.
                </p>
                {modalAction === 'REVERT' && (
                  <p className="text-xs text-amber-800 bg-amber-50 p-2 rounded-lg mt-2 font-medium">
                    ⚠️ Application will revert to stage <strong>Re-Scrutiny</strong>. Specific deficiency remarks must be communicated to the institution.
                  </p>
                )}
                {modalAction === 'REJECT' && (
                  <p className="text-xs text-rose-800 bg-rose-50 p-2 rounded-lg mt-2 font-medium">
                    ⚠️ Application will be set to statutory status <strong>REJECTED</strong>. Detailed speaking order remarks are mandatory.
                  </p>
                )}
              </div>

              {actionError && (
                <div className="text-xs p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-medium">
                  {actionError}
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Mandatory Statutory Remarks / Reasons <span className="text-rose-600">*</span>
                </label>
                <textarea
                  rows={4}
                  required={modalAction === 'REVERT' || modalAction === 'REJECT'}
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder={
                    modalAction === 'APPROVE'
                      ? 'Enter scrutiny findings or approval concurrence remarks...'
                      : 'Specify deficiency details or statutory clause under which application is reverted/rejected...'
                  }
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                />
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModalAction(null)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className={`px-5 py-2 text-xs font-bold text-white rounded-xl shadow-md transition-colors flex items-center gap-1.5 ${
                    modalAction === 'APPROVE' ? 'bg-emerald-600 hover:bg-emerald-700' :
                    modalAction === 'REVERT' ? 'bg-amber-600 hover:bg-amber-700' :
                    'bg-rose-600 hover:bg-rose-700'
                  }`}
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{submitting ? 'Recording Decision...' : `Confirm ${modalAction}`}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
