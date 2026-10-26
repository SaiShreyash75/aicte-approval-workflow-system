import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail, ShieldAlert, ArrowRight, UserCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import StatutoryBanner from '../components/StatutoryBanner';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('Aicte@123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const quickRoles = [
    { label: 'Admin (Apex Authority)', email: 'admin@aicte.gov.in', role: 'Admin', desc: 'System Administrator & Apex Oversight' },
    { label: 'Regional Officer (North)', email: 'ro.north@aicte.gov.in', role: 'Regional Officer', desc: 'Scrutiny & Regional Decisions' },
    { label: 'Bureau Officer (Approval)', email: 'bo.approval@aicte.gov.in', role: 'Bureau Officer', desc: 'Central Bureau Reviews & Ratification' },
    { label: 'Committee Member (EVC)', email: 'evc.expert1@aicte.gov.in', role: 'Committee Member', desc: 'On-site EVC Inspection & Appraisals' },
    { label: 'Institution (DIAET Delhi)', email: 'principal.diaet@aicte.edu', role: 'Institution', desc: 'Engineering College Applicant' },
  ];

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials or connection error');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (demoEmail) => {
    setEmail(demoEmail);
    setPassword('Aicte@123');
    setLoading(true);
    setError('');
    login(demoEmail, 'Aicte@123')
      .then(() => navigate('/dashboard'))
      .catch((err) => setError(err.response?.data?.detail || 'Quick login failed'))
      .finally(() => setLoading(false));
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between text-slate-100">
      <StatutoryBanner />

      <div className="flex-1 flex items-center justify-center p-4 sm:p-6 my-4">
        <div className="max-w-4xl w-full grid grid-cols-1 lg:grid-cols-12 bg-white text-slate-900 rounded-3xl shadow-2xl overflow-hidden border border-slate-800">
          
          {/* Left Hero Brand Panel */}
          <div className="lg:col-span-5 bg-gradient-to-br from-blue-950 via-slate-900 to-blue-900 p-8 text-white flex flex-col justify-between">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-400/20 text-amber-300 rounded-full text-xs font-semibold mb-6 border border-amber-400/30">
                <ShieldAlert className="w-3.5 h-3.5" /> Statutory Workflow Automation
              </div>
              <h2 className="text-2xl font-black tracking-tight leading-tight mb-3">
                AICTE Approval & Compliance Monitoring Portal
              </h2>
              <p className="text-xs text-slate-300 leading-relaxed">
                Automated workflow progression, statutory timeline monitoring, and multi-tier escalation management for technical institutions nationwide.
              </p>
            </div>

            <div className="my-8 space-y-3 text-xs text-slate-300 border-l-2 border-blue-500 pl-4">
              <div>
                <strong className="text-white block font-bold">Configurable Rule Engine:</strong>
                Scrutiny, EVC, SAC/SHC & custom combinations.
              </div>
              <div>
                <strong className="text-white block font-bold">Strict Role Separation:</strong>
                Tailored dashboards for all 5 statutory roles.
              </div>
              <div>
                <strong className="text-white block font-bold">Virtual Clock Simulation:</strong>
                Live demo testing of SLA breach & alert escalations.
              </div>
            </div>

            <div className="text-[11px] text-slate-400">
              Session 2026–2027 • AICTE New Delhi
            </div>
          </div>

          {/* Right Login & Quick Switch Panel */}
          <div className="lg:col-span-7 p-8 flex flex-col justify-between bg-slate-50">
            <div>
              <div className="mb-6">
                <h3 className="text-xl font-bold text-slate-900">Sign In to Your Statutory Desk</h3>
                <p className="text-xs text-slate-500 mt-1">Select your authorized role to access tailored workflow dashboards.</p>
              </div>

              {error && (
                <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
                  {error}
                </div>
              )}

              {/* Quick Switch Demo Buttons */}
              <div className="mb-6">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center gap-1.5">
                  <UserCheck className="w-4 h-4 text-blue-600" />
                  Instant Quick-Switch Demo Logins
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {quickRoles.map((r) => (
                    <button
                      key={r.role}
                      type="button"
                      onClick={() => handleQuickLogin(r.email)}
                      className="p-2.5 text-left rounded-xl border border-slate-200 bg-white hover:border-blue-600 hover:shadow-xs transition-all group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-slate-800 group-hover:text-blue-700">{r.role}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 transition-transform group-hover:translate-x-0.5" />
                      </div>
                      <div className="text-[10px] text-slate-500 truncate mt-0.5">{r.email}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="relative my-4 text-center">
                <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
                <span className="relative bg-slate-50 px-3 text-[11px] font-semibold uppercase text-slate-400">or enter credentials manually</span>
              </div>

              {/* Standard Form */}
              <form onSubmit={handleSubmit} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Official Email Address</label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="e.g. ro.north@aicte.gov.in"
                      className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-hidden bg-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Password</label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-9 pr-3 py-2 text-xs border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:outline-hidden bg-white"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-bold text-xs rounded-xl shadow-md transition-colors flex items-center justify-center gap-2 mt-2"
                >
                  {loading ? 'Authenticating...' : 'Sign In to Portal'}
                </button>
              </form>
            </div>

            <div className="mt-6 text-center text-[11px] text-slate-400">
              Demo Universal Password: <code className="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-slate-700 font-bold">Aicte@123</code>
            </div>
          </div>
        </div>
      </div>

      <footer className="py-2 text-center text-[11px] text-slate-400">
        © 2026 All India Council for Technical Education (AICTE), Ministry of Education, Govt. of India.
      </footer>
    </div>
  );
}
