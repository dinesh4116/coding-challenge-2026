import React from 'react';
import { DataProvider, useData } from './context/DataContext';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { OverviewView } from './components/views/OverviewView';
import { UploadView } from './components/views/UploadView';
import { AlertsView } from './components/views/AlertsView';
import { AnomalyAnalysisView } from './components/views/AnomalyAnalysisView';
import { ReportsView } from './components/views/ReportsView';
import { SettingsView } from './components/views/SettingsView';

const MainContent: React.FC = () => {
  const { activeTab, isLoading } = useData();

  return (
    <main className="flex-1 overflow-y-auto bg-slate-50 p-6">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
          <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="font-semibold text-slate-700 text-sm">Processing Dataset & Computing Rolling Baselines...</p>
        </div>
      ) : (
        <>
          {activeTab === 'overview' && <OverviewView />}
          {activeTab === 'campaigns' && <UploadView />}
          {activeTab === 'alerts' && <AlertsView />}
          {activeTab === 'analysis' && <AnomalyAnalysisView />}
          {activeTab === 'reports' && <ReportsView />}
          {activeTab === 'settings' && <SettingsView />}
        </>
      )}
    </main>
  );
};

export function App() {
  return (
    <DataProvider>
      <div className="flex h-screen bg-slate-50 overflow-hidden font-sans antialiased text-slate-900">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <Header />
          <MainContent />
        </div>
      </div>
    </DataProvider>
  );
}

export default App;
