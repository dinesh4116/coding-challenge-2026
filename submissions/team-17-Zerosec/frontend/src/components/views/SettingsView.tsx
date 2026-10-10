import React from 'react';
import {
  Sliders
} from 'lucide-react';
import { useData } from '../../context/DataContext';

export const SettingsView: React.FC = () => {
  const { config, updateConfig } = useData();

  return (
    <div className="space-y-5 max-w-3xl mx-auto">
      {/* Header */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm">
        <h2 className="text-base font-bold text-slate-900 tracking-tight">Detection Parameters</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure per-campaign rolling baselines, sensitivity multipliers, and cooldown periods.
        </p>
      </div>

      {/* Engine Threshold Parameters */}
      <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm space-y-5">
        <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center space-x-1.5 border-b border-slate-200 pb-2.5">
          <Sliders className="w-3.5 h-3.5 text-indigo-600" />
          <span>Baseline & Threshold Tuning</span>
        </h3>

        <div className="space-y-5">
          {/* Baseline Window Size Slider */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-slate-800">Rolling Baseline Window</label>
              <span className="font-mono text-xs font-bold text-indigo-600 px-2 py-0.5 bg-indigo-50 rounded">
                {config.baselineWindow} Days
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mb-2">
              Historical days used to compute rolling median baseline.
            </p>
            <input
              type="range"
              min={7}
              max={30}
              value={config.baselineWindow}
              onChange={e => updateConfig({ baselineWindow: Number(e.target.value) })}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          {/* Sensitivity Z-Score Threshold Slider */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-slate-800">Sensitivity Multiplier</label>
              <span className="font-mono text-xs font-bold text-indigo-600 px-2 py-0.5 bg-indigo-50 rounded">
                {config.zScoreThreshold} σ
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mb-2">
              Tolerance band multiplier. Higher values suppress minor fluctuations and noise.
            </p>
            <input
              type="range"
              min={1.5}
              max={4.0}
              step={0.1}
              value={config.zScoreThreshold}
              onChange={e => updateConfig({ zScoreThreshold: Number(e.target.value) })}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          {/* Cooldown Period Slider */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs font-semibold text-slate-800">Cooldown Suppression Window</label>
              <span className="font-mono text-xs font-bold text-indigo-600 px-2 py-0.5 bg-indigo-50 rounded">
                {config.cooldownPeriodDays} Days
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mb-2">
              Days without repetition before a repeated incident triggers a new notification.
            </p>
            <input
              type="range"
              min={1}
              max={7}
              value={config.cooldownPeriodDays}
              onChange={e => updateConfig({ cooldownPeriodDays: Number(e.target.value) })}
              className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          {/* Min Spend Threshold */}
          <div>
            <label className="text-xs font-semibold text-slate-800 block mb-1">Minimum Daily Spend Floor</label>
            <p className="text-[11px] text-slate-500 mb-1.5">Filters out noisy ratio swings on paused or zero-spend campaigns.</p>
            <div className="flex items-center max-w-xs">
              <span className="px-2.5 py-1.5 bg-slate-100 border border-r-0 border-slate-300 rounded-l-lg text-xs text-slate-500 font-semibold">₹</span>
              <input
                type="number"
                value={config.minSpendThreshold}
                onChange={e => updateConfig({ minSpendThreshold: Number(e.target.value) })}
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-300 rounded-r-lg text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
