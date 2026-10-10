import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  ShieldCheck,
  TrendingDown,
  Sparkles,
  Lock,
  Mail,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  Activity,
  Layers,
  CheckCircle2,
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useToast } from '../components/ui/ToastContext'

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const toast = useToast()
  const { isAuthenticated, loginWithCredentials, loginDemo, isLoading } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [rememberMe, setRememberMe] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [demoSubmitting, setDemoSubmitting] = useState(false)

  // Redirect if already authenticated
  const from = (location.state as any)?.from?.pathname || '/'

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, from])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    if (!email.trim()) {
      setErrorMessage('Please enter your work email address.')
      return
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email.trim())) {
      setErrorMessage('Please enter a valid work email format (e.g. analyst@company.com).')
      return
    }

    if (!password) {
      setErrorMessage('Please enter your password.')
      return
    }

    if (password.length < 6) {
      setErrorMessage('Password must contain at least 6 characters.')
      return
    }

    try {
      setSubmitting(true)
      const res = await loginWithCredentials({
        email: email.trim(),
        password,
        rememberMe,
      })

      if (res.success) {
        toast.success('Signed in successfully!')
        navigate(from, { replace: true })
      } else {
        setErrorMessage(res.error || 'Invalid credentials. Please try again.')
      }
    } catch {
      setErrorMessage('An unexpected error occurred during authentication.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDemoLogin = async () => {
    setErrorMessage(null)
    try {
      setDemoSubmitting(true)
      await loginDemo()
      toast.success('Welcome! Entered Demo Evaluation Dashboard.')
      navigate(from, { replace: true })
    } catch {
      setErrorMessage('Failed to initiate demo session.')
    } finally {
      setDemoSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#F5F7FB] flex flex-col justify-between antialiased">
      <div className="flex-1 flex flex-col lg:flex-row min-h-screen">
        {/* Left Column: Brand & Product Introduction (Desktop) */}
        <div className="lg:w-1/2 bg-gradient-to-br from-[#0A1322] via-[#101D33] to-[#14233B] text-white p-8 sm:p-12 lg:p-16 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-slate-800 relative overflow-hidden">
          {/* Subtle Ambient Glow */}
          <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-80 h-80 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

          {/* Top Brand Logo */}
          <div className="relative z-10">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xl font-black tracking-tight text-white">CampaignGuard</span>
                <span className="ml-1 text-xs font-bold text-blue-400 bg-blue-500/10 border border-blue-400/20 px-1.5 py-0.5 rounded">
                  AI
                </span>
              </div>
            </div>
          </div>

          {/* Center Pitch & Benefits */}
          <div className="my-10 lg:my-0 space-y-8 relative z-10 max-w-lg">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/15 border border-blue-400/30 text-blue-300 text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                <span>PS-04 Challenge Implementation</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
                Detect anomalies.<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-300">
                  Reduce alert fatigue.
                </span>
              </h1>
              <p className="text-sm sm:text-base text-slate-300 leading-relaxed font-normal">
                Monitor multi-channel advertising telemetry, isolate genuine conversion and spend breaks, and keep critical incidents visible with explainable anomaly alerts.
              </p>
            </div>

            {/* Benefit List */}
            <div className="space-y-4 pt-2">
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-emerald-500/15 border border-emerald-400/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-xs font-bold text-slate-100 uppercase tracking-wide">
                    Campaign-Specific Adaptive Thresholds
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                    Dynamic MAD confidence bands derived from historical variance eliminate false alerts on fluctuating campaigns.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-blue-500/15 border border-blue-400/30 flex items-center justify-center text-blue-400 shrink-0 mt-0.5">
                  <Activity className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-xs font-bold text-slate-100 uppercase tracking-wide">
                    Explainable Anomaly Diagnostics
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                    Plain-English triage answers what changed, baseline comparisons, and recommended diagnostic first steps.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-purple-500/15 border border-purple-400/30 flex items-center justify-center text-purple-400 shrink-0 mt-0.5">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-xs font-bold text-slate-100 uppercase tracking-wide">
                    180-Day Chronological Telemetry
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                    Surveillance across 20 campaigns (3,600 daily observations) with multi-day incident grouping and zero data leakage.
                  </p>
                </div>
              </div>
            </div>

            {/* Mini Visual Anomaly Envelope Mock */}
            <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-700/60 shadow-inner">
              <div className="flex items-center justify-between text-[11px] text-slate-400 mb-2">
                <span className="font-semibold text-slate-300">Adaptive Envelope Telemetry (C07 Meta)</span>
                <span className="text-rose-400 font-mono font-bold">Anomaly Detected (-97.8%)</span>
              </div>
              <svg className="w-full h-16 overflow-visible" viewBox="0 0 300 60">
                {/* Upper band */}
                <path
                  d="M0,20 Q75,18 150,22 T300,19"
                  fill="none"
                  stroke="#3867F5"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                  opacity="0.5"
                />
                {/* Lower band */}
                <path
                  d="M0,42 Q75,40 150,44 T300,41"
                  fill="none"
                  stroke="#3867F5"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                  opacity="0.5"
                />
                {/* Baseline envelope fill */}
                <polygon
                  points="0,20 75,18 150,22 300,19 300,41 150,44 75,40 0,42"
                  fill="#3867F5"
                  fillOpacity="0.08"
                />
                {/* Actual metric trajectory */}
                <path
                  d="M0,30 Q75,29 150,31 L200,30 L220,55 L240,54 L260,30 T300,31"
                  fill="none"
                  stroke="#10B981"
                  strokeWidth="2"
                />
                {/* Anomaly marker */}
                <circle cx="220" cy="55" r="4.5" fill="#EF4444" stroke="#FFFFFF" strokeWidth="1.5" />
                <circle cx="220" cy="55" r="8" fill="#EF4444" fillOpacity="0.3" className="animate-ping" />
              </svg>
            </div>
          </div>

          {/* Bottom Footnote */}
          <div className="relative z-10 text-[11px] text-slate-400 flex items-center justify-between pt-6 border-t border-slate-800/80">
            <span>Official Dataset: <strong className="text-slate-300">daily_campaign_metrics.csv</strong></span>
            <span>20 Campaigns • 180 Days</span>
          </div>
        </div>

        {/* Right Column: Authentication Form Panel */}
        <div className="lg:w-1/2 flex items-center justify-center p-6 sm:p-12 lg:p-16 bg-white">
          <div className="w-full max-w-md space-y-6">
            {/* Header */}
            <div>
              <h2 className="text-2xl font-bold text-[#172033] tracking-tight">Welcome back</h2>
              <p className="text-xs sm:text-sm text-[#697586] mt-1">
                Sign in to access your campaign monitoring dashboard.
              </p>
            </div>

            {/* Hackathon Mode B: Prominent Demo Access */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/80 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-blue-950 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" /> Hackathon Evaluator Access
                </span>
                <span className="px-2 py-0.5 rounded-full bg-blue-600 text-white font-mono text-[10px] font-bold">
                  ONE-CLICK
                </span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Evaluators may explore the 180-day challenge dataset, 174 alert events, and Model Evaluation Lab without entering credentials.
              </p>
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={demoSubmitting || submitting}
                className="w-full py-2.5 px-4 rounded-lg bg-[#3867F5] hover:bg-blue-600 text-white text-xs font-semibold shadow-xs hover:shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {demoSubmitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Entering Dashboard...</span>
                  </>
                ) : (
                  <>
                    <span>Enter Demo Dashboard</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </div>

            {/* Divider */}
            <div className="relative flex items-center justify-center">
              <div className="border-t border-[#E4E9F1] w-full" />
              <span className="bg-white px-3 text-[11px] font-bold uppercase tracking-wider text-[#697586] absolute">
                Or Sign In With Email
              </span>
            </div>

            {/* Error Message Alert */}
            {errorMessage && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2 animate-in fade-in duration-150">
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                <div className="flex-1 font-medium">{errorMessage}</div>
              </div>
            )}

            {/* Standard Credentials Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Address */}
              <div>
                <label
                  htmlFor="email-input"
                  className="block text-xs font-semibold text-slate-700 mb-1.5"
                >
                  Work Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="email-input"
                    type="email"
                    name="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="analyst@campaignguard.ai"
                    className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg pl-9 pr-3 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-[#3867F5] focus:bg-white transition-all"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label
                    htmlFor="password-input"
                    className="block text-xs font-semibold text-slate-700"
                  >
                    Password
                  </label>
                  <span
                    className="text-[11px] text-slate-400 cursor-not-allowed"
                    title="Self-service reset requires configured production SMTP server."
                  >
                    Forgot password?
                  </span>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    id="password-input"
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[#F5F7FB] border border-[#E4E9F1] rounded-lg pl-9 pr-9 py-2 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-[#3867F5] focus:bg-white transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Remember Me */}
              <div className="flex items-center justify-between text-xs pt-1">
                <label className="flex items-center gap-2 text-slate-600 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-3.5 h-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                  <span>Remember this browser session</span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={submitting || demoSubmitting}
                className="w-full py-2.5 px-4 rounded-lg bg-[#14233B] hover:bg-[#1e3458] text-white text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>

            {/* Footer */}
            <div className="pt-6 border-t border-slate-100 text-center text-[11px] text-[#697586] space-y-1">
              <p>CampaignGuard AI • PS-04 Anomaly Alerting Without Alert Fatigue</p>
              <p className="text-slate-400">© 2026 CampaignGuard Systems. All rights reserved.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
