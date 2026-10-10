import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileCheck,
  Download,
  RefreshCw,
  AlertCircle,
  Table as TableIcon,
  Sliders
} from 'lucide-react';
import { useData } from '../../context/DataContext';
import { exportToCSV, generateSampleDataset } from '../../utils/csvParser';
import { ColumnMapping } from '../../types/dashboard';

export const UploadView: React.FC = () => {
  const {
    metadata,
    records,
    isLoading,
    error,
    handleFileUpload,
    handleLoadDemoData,
    handleResetData,
    updateColumnMappingAndReprocess
  } = useData();

  const [dragActive, setDragActive] = useState(false);
  const [editingMapping, setEditingMapping] = useState<ColumnMapping | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.csv')) {
        handleFileUpload(file);
      } else {
        alert('Please select a valid .csv file');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleDownloadSample = () => {
    const { records: sampleRecords } = generateSampleDataset();
    const rows = sampleRecords.map(r => ({
      date: r.date,
      campaign: r.campaign,
      spend: r.spend,
      conversions: r.conversions,
      impressions: r.impressions,
      clicks: r.clicks,
      is_incident: r.is_incident !== undefined ? (r.is_incident ? 1 : 0) : '',
      incident_type: r.incident_type || ''
    }));
    exportToCSV('sample_campaign_data.csv', rows);
  };

  const previewRows = records.slice(0, 10);

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900 tracking-tight">Dataset Ingestion</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload custom campaign metrics in CSV format. Auto-detects columns and computes rolling baselines.
          </p>
        </div>
        <button
          onClick={handleDownloadSample}
          className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 font-medium text-xs rounded-lg transition-colors flex items-center space-x-1.5"
        >
          <Download className="w-3.5 h-3.5 text-slate-500" />
          <span>Sample Template</span>
        </button>
      </div>

      {/* Upload Dropzone */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-sm">
        <div
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all flex flex-col items-center justify-center ${
            dragActive
              ? 'border-indigo-600 bg-indigo-50/50'
              : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50/50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
            <UploadCloud className="w-6 h-6" />
          </div>

          <h3 className="text-sm font-bold text-slate-800">
            {isLoading ? 'Processing Dataset...' : 'Drag & Drop CSV file here'}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5 max-w-sm">
            Standard columns: <code className="text-indigo-600 font-mono font-medium">date</code>, <code className="text-indigo-600 font-mono font-medium">campaign</code>, <code className="text-indigo-600 font-mono font-medium">spend</code>, <code className="text-indigo-600 font-mono font-medium">conversions</code>.
          </p>

          <button
            type="button"
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg shadow-xs transition-colors"
          >
            Browse File
          </button>
        </div>

        {error && (
          <div className="mt-3 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start space-x-2">
            <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-900">Ingestion Warning</p>
              <p className="mt-0.5 text-[11px]">{error}</p>
            </div>
          </div>
        )}
      </div>

      {/* Active Dataset Inspector */}
      {metadata && (
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-3.5 border-b border-slate-200 gap-3">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-lg">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-bold text-slate-900 text-sm">{metadata.filename}</h3>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                    Active
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5 font-mono">
                  {metadata.rowCount.toLocaleString()} rows • {metadata.campaignCount} campaigns ({metadata.minDate} to {metadata.maxDate})
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleLoadDemoData}
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-xs rounded-lg transition-colors flex items-center space-x-1.5"
              >
                <RefreshCw className="w-3 h-3 text-slate-500" />
                <span>Reload Data</span>
              </button>
              <button
                onClick={handleResetData}
                className="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 font-medium text-xs rounded-lg transition-colors"
              >
                Reset
              </button>
            </div>
          </div>

          {/* Mapped Column Headers Grid */}
          <div>
            <h4 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2.5 flex items-center space-x-1.5">
              <Sliders className="w-3.5 h-3.5 text-indigo-600" />
              <span>Resolved Field Mappings</span>
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-xs">
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-400 text-[10px] font-medium">Date Field:</span>
                <p className="font-mono font-semibold text-indigo-600 mt-0.5">{metadata.mappedColumns.dateField || 'Not Mapped'}</p>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-400 text-[10px] font-medium">Campaign Field:</span>
                <p className="font-mono font-semibold text-indigo-600 mt-0.5">{metadata.mappedColumns.campaignField || 'Not Mapped'}</p>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-400 text-[10px] font-medium">Spend Field:</span>
                <p className="font-mono font-semibold text-indigo-600 mt-0.5">{metadata.mappedColumns.spendField || 'Not Mapped'}</p>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-slate-400 text-[10px] font-medium">Conversions Field:</span>
                <p className="font-mono font-semibold text-indigo-600 mt-0.5">{metadata.mappedColumns.conversionsField || 'Not Mapped'}</p>
              </div>
            </div>
          </div>

          {/* First 10 Rows Preview Table */}
          <div>
            <h4 className="text-[11px] font-bold text-slate-900 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <TableIcon className="w-3.5 h-3.5 text-indigo-600" />
              <span>Data Preview ({previewRows.length} of {records.length.toLocaleString()} rows)</span>
            </h4>
            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-700 font-semibold border-b border-slate-200 uppercase text-[11px]">
                  <tr>
                    <th className="py-2 px-3">Date</th>
                    <th className="py-2 px-3">Campaign</th>
                    <th className="py-2 px-3">Spend (₹)</th>
                    <th className="py-2 px-3">Conversions</th>
                    <th className="py-2 px-3">CPA (₹)</th>
                    <th className="py-2 px-3">Label</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-slate-700 font-mono text-[11px]">
                  {previewRows.map((r, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="py-2 px-3">{r.date}</td>
                      <td className="py-2 px-3 font-sans font-medium text-slate-900 max-w-xs truncate">{r.campaign}</td>
                      <td className="py-2 px-3">₹{r.spend.toFixed(2)}</td>
                      <td className="py-2 px-3">{r.conversions}</td>
                      <td className="py-2 px-3">₹{r.cpa.toFixed(2)}</td>
                      <td className="py-2 px-3">
                        {r.is_incident !== undefined ? (
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            r.is_incident ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'
                          }`}>
                            {r.is_incident ? `INCIDENT (${r.incident_type || 'YES'})` : 'NORMAL'}
                          </span>
                        ) : (
                          <span className="text-slate-400 font-sans italic text-[10px]">Unlabeled</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
