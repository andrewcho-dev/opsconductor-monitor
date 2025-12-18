/**
 * StatCard Component
 * 
 * Displays a statistic with icon and color.
 */

import React from 'react';
import { cn } from '../../../lib/utils';

const colors = {
  blue: 'bg-blue-50 text-blue-600 border-blue-200',
  green: 'bg-green-50 text-green-600 border-green-200',
  amber: 'bg-amber-50 text-amber-600 border-amber-200',
  red: 'bg-red-50 text-red-600 border-red-200',
  purple: 'bg-purple-50 text-purple-600 border-purple-200',
  gray: 'bg-gray-50 text-gray-600 border-gray-200',
};

export function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className={cn("p-4 rounded-lg border", colors[color])}>
      <div className="flex items-center justify-between">
        <Icon className="w-5 h-5 opacity-70" />
        <span className="text-2xl font-bold">{value}</span>
      </div>
      <p className="text-sm mt-1 opacity-80">{label}</p>
    </div>
  );
}
