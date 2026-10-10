import React from 'react'

export interface BadgeProps {
  children: React.ReactNode
  variant?: 'primary' | 'critical' | 'warning' | 'healthy' | 'neutral' | 'outline' | 'purple'
  size?: 'sm' | 'md'
  className?: string
  dot?: boolean
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
  dot = false,
}) => {
  const variantStyles = {
    primary: 'bg-blue-50 text-[#3867F5] border-blue-200',
    critical: 'bg-rose-50 text-[#DC3545] border-rose-200 font-semibold',
    warning: 'bg-amber-50 text-[#D97706] border-amber-200 font-medium',
    healthy: 'bg-emerald-50 text-[#16A36A] border-emerald-200 font-medium',
    neutral: 'bg-slate-100 text-[#475569] border-slate-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    outline: 'bg-transparent text-slate-700 border-slate-300',
  }

  const dotColors = {
    primary: 'bg-[#3867F5]',
    critical: 'bg-[#DC3545]',
    warning: 'bg-[#F59E0B]',
    healthy: 'bg-[#16A36A]',
    neutral: 'bg-slate-400',
    purple: 'bg-purple-600',
    outline: 'bg-slate-400',
  }

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5 rounded-md',
    md: 'text-xs px-2.5 py-1 rounded-md',
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 border leading-none font-medium ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  )
}
