import React from 'react';
import { ActionCard } from '../actions/ActionCard';

export const ActionsList = ({
  actions,
  onAddAction,
  updateAction,
  deleteAction,
  moveAction,
  onOpenTargetsModal,
  onAddPattern,
  onUpdatePattern,
  onRemovePattern
}) => (
  <section className="bg-white rounded shadow p-3 mb-2 space-y-3">
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <h2 className="text-lg font-bold">
        Actions ({actions.length})
        <span className="ml-2 text-xs font-normal text-gray-600">
          Define individual steps this job will execute
        </span>
      </h2>
      <button
        type="button"
        onClick={onAddAction}
        className="self-start sm:self-auto rounded bg-green-500 px-3 py-1 text-sm font-semibold text-white hover:bg-green-600"
      >
        Add Action
      </button>
    </div>

    <div className="space-y-3">
      {actions.map((action, index) => (
        <ActionCard
          key={index}
          action={action}
          index={index}
          totalActions={actions.length}
          updateAction={updateAction}
          deleteAction={deleteAction}
          moveAction={moveAction}
          onOpenTargetModal={onOpenTargetsModal}
          onAddPattern={onAddPattern}
          onUpdatePattern={onUpdatePattern}
          onRemovePattern={onRemovePattern}
        />
      ))}
    </div>
  </section>
);
