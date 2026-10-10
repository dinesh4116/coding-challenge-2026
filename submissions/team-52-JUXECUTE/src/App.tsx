import React, { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ToastProvider } from './components/ui/ToastContext'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './components/layout/AppShell'
import { LoginPage } from './pages/LoginPage'
import { OverviewPage } from './pages/OverviewPage'
import { CampaignsPage } from './pages/CampaignsPage'
import { CampaignDetailPage } from './pages/CampaignDetailPage'
import { AlertsPage } from './pages/AlertsPage'
import { AlertDetailPage } from './pages/AlertDetailPage'
import { IncidentsPage } from './pages/IncidentsPage'
import { EvaluationPage } from './pages/EvaluationPage'
import { ReportsPage } from './pages/ReportsPage'
import { SettingsPage } from './pages/SettingsPage'
import { NotFoundPage } from './pages/NotFoundPage'

export function App() {
  const [dateRange, setDateRange] = useState<string>('180d')

  return (
    <ToastProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public authentication route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected dashboard application routes */}
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<AppShell dateRange={dateRange} setDateRange={setDateRange} />}>
                <Route index element={<OverviewPage />} />
                <Route path="campaigns" element={<CampaignsPage />} />
                <Route path="campaigns/:campaignId" element={<CampaignDetailPage />} />
                <Route path="alerts" element={<AlertsPage />} />
                <Route path="alerts/:alertId" element={<AlertDetailPage />} />
                <Route path="incidents" element={<IncidentsPage />} />
                <Route path="evaluation" element={<EvaluationPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ToastProvider>
  )
}

export default App
