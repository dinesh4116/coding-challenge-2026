import React, { useState } from 'react'
import { EvaluationRun } from '../../types/evaluation'
import { formatPercent } from '../../utils/formatters'

interface ConfusionMatrixProps {
  evaluationRun: EvaluationRun
}

export const ConfusionMatrix: React.FC<ConfusionMatrixProps> = ({ evaluationRun }) => {
  const [activeCell, setActiveCell] = useState<string | null>(null)

  const { truePositives, falsePositives, falseNegatives, trueNegatives, totalObservations } =
    evaluationRun

  const tpPct = totalObservations > 0 ? truePositives / totalObservations : 0
  const fpPct = totalObservations > 0 ? falsePositives / totalObservations : 0
  const fnPct = totalObservations > 0 ? falseNegatives / totalObservations : 0
  const tnPct = totalObservations > 0 ? trueNegatives / totalObservations : 0

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h4 className="text-sm font-semibold text-[#172033]">Interactive Confusion Matrix</h4>
          <p className="text-xs text-[#697586]">
            Evaluated on {totalObservations.toLocaleString()} observations • Click any quadrant to inspect details
          </p>
        </div>
      </div>

      <div className="grid grid-cols-[auto_1fr_1fr] gap-2 items-center text-xs">
        {/* Top Header Labels */}
        <div />
        <div className="text-center font-bold text-slate-700 bg-slate-100 py-1.5 rounded-lg border border-slate-200">
          Predicted Anomaly (Alert Fired)
        </div>
        <div className="text-center font-bold text-slate-700 bg-slate-100 py-1.5 rounded-lg border border-slate-200">
          Predicted Normal (No Alert)
        </div>

        {/* Row 1: Actual Ground Truth Anomaly */}
        <div className="font-bold text-slate-700 px-3 py-6 bg-slate-100 rounded-lg border border-slate-200 flex items-center justify-center [writing-mode:vertical-rl] rotate-180">
          Actual Incident
        </div>

        {/* True Positive Cell */}
        <div
          onClick={() => setActiveCell('TP')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            activeCell === 'TP'
              ? 'ring-2 ring-emerald-500 shadow-md'
              : 'hover:shadow-xs'
          } bg-emerald-50/70 border-emerald-200`}
        >
          <div className="flex items-center justify-between text-emerald-900 mb-1">
            <span className="font-bold text-xs uppercase tracking-wider">True Positive (TP)</span>
            <span className="text-[11px] font-semibold bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded">
              {formatPercent(tpPct)}
            </span>
          </div>
          <div className="text-2xl font-black text-emerald-700">
            {truePositives.toLocaleString()}
          </div>
          <p className="text-[11px] text-emerald-800 mt-1">
            Genuine operational incidents accurately flagged and alerted
          </p>
        </div>

        {/* False Negative Cell */}
        <div
          onClick={() => setActiveCell('FN')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            activeCell === 'FN'
              ? 'ring-2 ring-rose-500 shadow-md'
              : 'hover:shadow-xs'
          } bg-rose-50/70 border-rose-200`}
        >
          <div className="flex items-center justify-between text-rose-900 mb-1">
            <span className="font-bold text-xs uppercase tracking-wider">False Negative (FN)</span>
            <span className="text-[11px] font-semibold bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded">
              {formatPercent(fnPct)}
            </span>
          </div>
          <div className="text-2xl font-black text-rose-700">
            {falseNegatives.toLocaleString()}
          </div>
          <p className="text-[11px] text-rose-800 mt-1">
            True incidents that slipped through undetected (Missed alarms)
          </p>
        </div>

        {/* Row 2: Actual Ground Truth Normal */}
        <div className="font-bold text-slate-700 px-3 py-6 bg-slate-100 rounded-lg border border-slate-200 flex items-center justify-center [writing-mode:vertical-rl] rotate-180">
          Actual Normal
        </div>

        {/* False Positive Cell */}
        <div
          onClick={() => setActiveCell('FP')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            activeCell === 'FP'
              ? 'ring-2 ring-amber-500 shadow-md'
              : 'hover:shadow-xs'
          } bg-amber-50/70 border-amber-200`}
        >
          <div className="flex items-center justify-between text-amber-900 mb-1">
            <span className="font-bold text-xs uppercase tracking-wider">False Positive (FP)</span>
            <span className="text-[11px] font-semibold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">
              {formatPercent(fpPct)}
            </span>
          </div>
          <div className="text-2xl font-black text-amber-700">
            {falsePositives.toLocaleString()}
          </div>
          <p className="text-[11px] text-amber-800 mt-1">
            Normal variations wrongly flagged (Primary source of Alert Fatigue)
          </p>
        </div>

        {/* True Negative Cell */}
        <div
          onClick={() => setActiveCell('TN')}
          className={`p-4 rounded-xl border transition-all cursor-pointer ${
            activeCell === 'TN'
              ? 'ring-2 ring-blue-500 shadow-md'
              : 'hover:shadow-xs'
          } bg-blue-50/50 border-blue-200`}
        >
          <div className="flex items-center justify-between text-blue-900 mb-1">
            <span className="font-bold text-xs uppercase tracking-wider">True Negative (TN)</span>
            <span className="text-[11px] font-semibold bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">
              {formatPercent(tnPct)}
            </span>
          </div>
          <div className="text-2xl font-black text-blue-800">
            {trueNegatives.toLocaleString()}
          </div>
          <p className="text-[11px] text-blue-900 mt-1">
            Routine daily operations correctly recognized as normal behavior
          </p>
        </div>
      </div>

      {/* Active Cell Inspector Note */}
      {activeCell && (
        <div className="mt-3 p-3 bg-slate-900 text-white rounded-xl text-xs flex items-center justify-between animate-in fade-in duration-100">
          <div>
            <span className="font-bold text-amber-400">Selected quadrant: {activeCell}</span> —{' '}
            {activeCell === 'TP' && `${truePositives} confirmed real issues alerted to ops.`}
            {activeCell === 'FP' && `${falsePositives} false alarms generating operational noise.`}
            {activeCell === 'FN' && `${falseNegatives} unflagged incidents requiring review.`}
            {activeCell === 'TN' && `${trueNegatives} normal observations quietly suppressed.`}
          </div>
          <button
            onClick={() => setActiveCell(null)}
            className="text-slate-400 hover:text-white text-xs underline ml-2 cursor-pointer"
          >
            Clear selection
          </button>
        </div>
      )}
    </div>
  )
}
