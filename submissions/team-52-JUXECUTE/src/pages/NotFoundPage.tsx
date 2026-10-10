import React from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldAlert, Home } from 'lucide-react'
import { Button } from '../components/ui/Button'

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6 space-y-4">
      <div className="w-16 h-16 rounded-2xl bg-blue-50 text-[#3867F5] flex items-center justify-center border border-blue-200">
        <ShieldAlert className="w-8 h-8" />
      </div>
      <h2 className="text-2xl font-bold text-[#172033]">404 — Page Not Found</h2>
      <p className="text-xs text-[#697586] max-w-sm">
        The requested telemetry view or campaign resource could not be found. Return to the main CampaignGuard dashboard.
      </p>
      <Button
        variant="primary"
        size="md"
        onClick={() => navigate('/')}
        icon={<Home className="w-4 h-4" />}
      >
        Back to Overview
      </Button>
    </div>
  )
}
