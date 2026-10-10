import React, { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopNavbar } from './TopNavbar'

interface AppShellProps {
  dateRange: string
  setDateRange: (range: string) => void
}

export const AppShell: React.FC<AppShellProps> = ({ dateRange, setDateRange }) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#F5F7FB] flex text-[#172033] antialiased">
      {/* Left Sidebar */}
      <Sidebar
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        isMobileOpen={isMobileSidebarOpen}
        setIsMobileOpen={setIsMobileSidebarOpen}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNavbar
          onMobileMenuToggle={() => setIsMobileSidebarOpen(true)}
          selectedDateRange={dateRange}
          onDateRangeChange={setDateRange}
        />

        <main className="flex-1 p-4 md:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet context={{ dateRange }} />
        </main>
      </div>
    </div>
  )
}
