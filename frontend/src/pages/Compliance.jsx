import React, { useState, useEffect } from 'react';
import { ShieldCheck, FileCheck, AlertTriangle, Clock, Check, X, Upload } from 'lucide-react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Compliance() {
  const { user, refreshKey, triggerGlobalRefresh } = useAuth();
  const [tab, setTab] = useState('undertakings'); // 'undertakings' or 'documents'
  const [undertakings, setUndertakings] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);

  // Verification modal
  const [verifyItem, setVerifyItem] = useState(null); // { type: 'UNDERTAKING' | 'DOCUMENT', item: obj }
  const [remarks, setRemarks] = useState('');
  const [verifyAction, setVerifyAction] = useState('VERIFY');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [uRes, dRes] = await Promise.all([
          api.get('/compliance/undertakings'),
          api.get('/compliance/documents')
        ]);
        setUndertakings(uRes.data);
        setDocuments(dRes.data);
      } catch (e) {
        console.error("Error loading compliance", e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [refreshKey]);

  const canVerify = ['Regional Officer', 'Bureau Officer', 'Admin'].includes(user?.role);

  const handleVerifySubmit = async (e) => {
    e.preventDefault();
    if (!verifyItem) return;
    setSubmitting(true);
    try {
      if (verifyItem.type === 'UNDERTAKING') {
        await api.post(`/compliance/undertakings/${verifyItem.item.id}/verify`, {
          action: verifyAction,
          remarks: remarks.trim() || 'Verified compliance document submission.'
        });
      } else {
        await api.post(`/compliance/documents/${verifyItem.item.id}/verify`, {
          action: verifyAction,
          remarks: remarks.trim() || 'Verified certificate renewal.',
          new_expiry_date: null
        });
      }
      setVerifyItem(null);
      setRemarks('');
      triggerGlobalRefresh();
    } catch (e) {
      alert("Error processing verification: " + (e.response?.data?.detail || e.message));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-xl font-bold text-slate-900 leading-tight">Institutional Compliance & Document Validity</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Track statutory time-bound undertakings, monitor land lease & safety certificate expiry countdowns, and verify renewal submissions.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-4 text-xs font-bold">
        <button
          onClick={() => setTab('undertakings')}
          className={`pb-3 px-2 flex items-center gap-2 border-b-2 transition-all ${
            tab === 'undertakings'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-400 hover:text-slate-700'
          }`}
        >
          <FileCheck className="w-4 h-4" />
          <span>Statutory Undertakings ({undertakings.length})</span>
        </button>
        <button
          onClick={() => setTab('documents')}
          className={`pb-3 px-2 flex items-center gap-2 border-b-2 transition-all ${
            tab === 'documents'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-400 hover:text-slate-700'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Land Lease & Statutory Documents ({documents.length})</span>
        </button>
      </div>

      {/* Tab 1: Undertakings */}
      {tab === 'undertakings' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Undertaking Condition</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Compliance Status</th>
                  <th className="py-3 px-4">Evidence Uploaded</th>
                  <th className="py-3 px-4">Officer Remarks</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {undertakings.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/80">
                    <td className="py-3.5 px-4 max-w-sm">
                      <div className="font-bold text-slate-800">{u.condition_title}</div>
                      <div className="text-[11px] text-slate-500 line-clamp-1">{u.description}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      {new Date(u.due_date).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4">
                      {u.status === 'VERIFIED' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          ✓ VERIFIED
                        </span>
                      ) : u.status === 'OVERDUE' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 animate-pulse">
                          🚨 OVERDUE
                        </span>
                      ) : u.status === 'SUBMITTED' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                          SUBMITTED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                          PENDING
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      {u.evidence_files && u.evidence_files.length > 0 ? (
                        <span className="text-[11px] text-blue-600 font-mono font-medium">
                          {u.evidence_files[0].file_name}
                        </span>
                      ) : (
                        <span className="text-slate-400 italic">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 italic max-w-xs truncate">
                      {u.officer_remarks || 'Pending review'}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {u.status === 'SUBMITTED' && canVerify && (
                        <button
                          onClick={() => setVerifyItem({ type: 'UNDERTAKING', item: u })}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-bold transition-colors"
                        >
                          Verify Evidence
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Documents */}
      {tab === 'documents' && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 text-[11px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4">Document Type</th>
                  <th className="py-3 px-4">Title / Registration</th>
                  <th className="py-3 px-4">Issue Date</th>
                  <th className="py-3 px-4">Expiry Date</th>
                  <th className="py-3 px-4">Validity Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50/80">
                    <td className="py-3.5 px-4 font-bold text-slate-800">{d.document_type}</td>
                    <td className="py-3.5 px-4 max-w-sm truncate text-slate-700">{d.title}</td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">{d.issue_date}</td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">{d.expiry_date}</td>
                    <td className="py-3.5 px-4">
                      {d.status === 'EXPIRED' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 animate-pulse">
                          EXPIRED ({Math.abs(d.days_to_expiry)}d ago)
                        </span>
                      ) : d.status === 'EXPIRING_SOON' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">
                          EXPIRING SOON ({d.days_to_expiry}d left)
                        </span>
                      ) : d.status === 'RENEWAL_SUBMITTED' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                          RENEWAL SUBMITTED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                          VALID ({d.days_to_expiry}d left)
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      {d.status === 'RENEWAL_SUBMITTED' && canVerify && (
                        <button
                          onClick={() => setVerifyItem({ type: 'DOCUMENT', item: d })}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-bold transition-colors"
                        >
                          Verify Renewal
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Verification Modal */}
      {verifyItem && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Officer Verification Decision: {verifyItem.item.condition_title || verifyItem.item.title}
            </h3>
            <form onSubmit={handleVerifySubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Decision</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setVerifyAction('VERIFY')}
                    className={`flex-1 py-2 rounded-lg font-bold border ${
                      verifyAction === 'VERIFY' ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-slate-50 text-slate-700'
                    }`}
                  >
                    Verify & Close Alert
                  </button>
                  <button
                    type="button"
                    onClick={() => setVerifyAction('REJECT')}
                    className={`flex-1 py-2 rounded-lg font-bold border ${
                      verifyAction === 'REJECT' ? 'bg-rose-600 text-white border-rose-600' : 'bg-slate-50 text-slate-700'
                    }`}
                  >
                    Reject Submission
                  </button>
                </div>
              </div>
              <div>
                <label className="block font-bold text-slate-700 mb-1">Officer Examination Remarks *</label>
                <textarea
                  required
                  rows={3}
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Enter scrutiny findings and verification remarks..."
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setVerifyItem(null)}
                  className="px-3 py-1.5 font-bold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg"
                >
                  {submitting ? 'Recording...' : 'Confirm Decision'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
