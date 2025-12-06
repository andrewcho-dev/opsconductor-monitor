import React from 'react';
import IntelligentCommandBuilder from '../../IntelligentCommandBuilder';
import { ActionTargetsSection } from './ActionTargetsSection';
import { ActionResultsSection } from './ActionResultsSection';
import { ActionAdvancedSection } from './ActionAdvancedSection';
import { getActionDisplayName } from '../utils/actionHelpers';

const SummaryBadge = ({ children, muted = false }) => (
  <span
    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] tracking-wide ${
      muted ? 'bg-gray-200 text-gray-600' : 'bg-blue-100 text-blue-700'
    }`}
  >
    {children}
  </span>
);

export const ActionCard = ({
  action,
  index,
  totalActions,
  updateAction,
  deleteAction,
  moveAction,
  onOpenTargetModal,
  onSourceChange,
  onAddPattern,
  onUpdatePattern,
  onRemovePattern
}) => (
  <details className="rounded border border-gray-200 bg-white shadow-sm" open={index === 0}>
    <summary
      className={`cursor-pointer select-none border-b px-3 py-2 text-sm font-semibold flex flex-col gap-2 md:flex-row md:items-center md:justify-between ${
        action.enabled ? 'bg-gray-50 hover:bg-gray-100' : 'bg-red-50 hover:bg-red-100'
      }`}
    >
      <div className="flex flex-col gap-1">
        <span>
          Action {index + 1}: {getActionDisplayName(action)}
        </span>
        <div className="flex flex-wrap gap-2 text-[10px] font-medium text-gray-600 uppercase">
          <SummaryBadge>{action.login_method?.platform || 'ubuntu-20.04'}</SummaryBadge>
          <SummaryBadge>{action.login_method?.command_id || action.login_method?.type || 'unknown'}</SummaryBadge>
          <SummaryBadge>{action.targeting?.source || 'no-targets'}</SummaryBadge>
          <SummaryBadge muted>{action.database?.table || 'no-table'}</SummaryBadge>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            moveAction(index, 'up');
          }}
          disabled={index === 0}
          className="rounded border border-gray-300 px-2 py-1 disabled:opacity-40 disabled:cursor-not-allowed"
          title="Move action up"
        >
          ↑
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            moveAction(index, 'down');
          }}
          disabled={index === totalActions - 1}
          className="rounded border border-gray-300 px-2 py-1 disabled:opacity-40 disabled:cursor-not-allowed"
          title="Move action down"
        >
          ↓
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            updateAction(index, 'enabled', !action.enabled);
          }}
          className={`rounded px-2 py-1 font-semibold ${
            action.enabled ? 'bg-green-500 text-white hover:bg-green-600' : 'bg-red-500 text-white hover:bg-red-600'
          }`}
        >
          {action.enabled ? 'ON' : 'OFF'}
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            deleteAction(index);
          }}
          className="rounded bg-red-100 px-2 py-1 font-semibold text-red-700 hover:bg-red-200"
        >
          Delete
        </button>
      </div>
    </summary>

    <div className="space-y-4 p-3 text-sm">
      <section className="space-y-2">
        <h4 className="text-xs font-bold uppercase tracking-wide text-gray-600">Command</h4>
        <IntelligentCommandBuilder action={action} actionIndex={index} updateAction={updateAction} />
      </section>

      <ActionTargetsSection
        action={action}
        actionIndex={index}
        updateAction={updateAction}
        onSourceChange={onSourceChange}
        onOpenModal={onOpenTargetModal}
      />

      <ActionResultsSection action={action} actionIndex={index} updateAction={updateAction} />

      <ActionAdvancedSection
        action={action}
        onUpdateAction={(path, value) => updateAction(index, path, value)}
        onAddPattern={() => onAddPattern(index)}
        onUpdatePattern={(patternIndex, field, value) => onUpdatePattern(index, patternIndex, field, value)}
        onRemovePattern={(patternIndex) => onRemovePattern(index, patternIndex)}
      />
    </div>
  </details>
);
