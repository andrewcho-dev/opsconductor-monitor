/**
 * WorkflowToolbar Component
 * 
 * Top toolbar for the workflow builder with actions like save, run, undo/redo.
 */

import React, { useState, useRef, useEffect } from 'react';
import { 
  Save, 
  Play, 
  Undo2, 
  Redo2, 
  Trash2, 
  Copy, 
  LayoutGrid,
  Settings,
  ChevronLeft,
  TestTube,
  Clock,
  Pencil,
} from 'lucide-react';
import { cn } from '../../../lib/utils';

const WorkflowToolbar = ({
  workflowName,
  onNameChange,
  isDirty,
  canUndo,
  canRedo,
  hasSelection,
  onBack,
  onSave,
  onRun,
  onTest,
  onUndo,
  onRedo,
  onDelete,
  onDuplicate,
  onAutoLayout,
  onOpenSettings,
  onOpenSchedule,
  isSaving,
  isRunning,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(workflowName || '');
  const inputRef = useRef(null);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  useEffect(() => {
    setEditValue(workflowName || '');
  }, [workflowName]);

  const handleStartEdit = () => {
    setEditValue(workflowName || '');
    setIsEditing(true);
  };

  const handleSave = () => {
    const trimmed = editValue.trim();
    if (trimmed && onNameChange) {
      onNameChange(trimmed);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      setEditValue(workflowName || '');
      setIsEditing(false);
    }
  };

  return (
    <div className="h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-2">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md"
        title="Back to Jobs"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>

      {/* Workflow Name */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleSave}
            onKeyDown={handleKeyDown}
            className="text-lg font-semibold text-gray-900 bg-transparent border-b-2 border-blue-500 outline-none px-1 min-w-[200px]"
            placeholder="Workflow name..."
          />
        ) : (
          <button
            onClick={handleStartEdit}
            className="flex items-center gap-2 text-lg font-semibold text-gray-900 hover:text-blue-600 group"
            title="Click to rename workflow"
          >
            <span className="truncate">{workflowName || 'Untitled Workflow'}</span>
            <Pencil className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400" />
          </button>
        )}
        {isDirty && (
          <span className="text-xs text-orange-500 font-medium">
            (unsaved)
          </span>
        )}
      </div>

      {/* Divider */}
      <div className="h-6 w-px bg-gray-200" />

      {/* Undo/Redo */}
      <div className="flex items-center gap-1">
        <button
          onClick={onUndo}
          disabled={!canUndo}
          className={cn(
            'p-2 rounded-md transition-colors',
            canUndo 
              ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100' 
              : 'text-gray-300 cursor-not-allowed'
          )}
          title="Undo (Ctrl+Z)"
        >
          <Undo2 className="w-4 h-4" />
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          className={cn(
            'p-2 rounded-md transition-colors',
            canRedo 
              ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100' 
              : 'text-gray-300 cursor-not-allowed'
          )}
          title="Redo (Ctrl+Y)"
        >
          <Redo2 className="w-4 h-4" />
        </button>
      </div>

      {/* Divider */}
      <div className="h-6 w-px bg-gray-200" />

      {/* Selection Actions */}
      <div className="flex items-center gap-1">
        <button
          onClick={onDuplicate}
          disabled={!hasSelection}
          className={cn(
            'p-2 rounded-md transition-colors',
            hasSelection 
              ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100' 
              : 'text-gray-300 cursor-not-allowed'
          )}
          title="Duplicate (Ctrl+D)"
        >
          <Copy className="w-4 h-4" />
        </button>
        <button
          onClick={onDelete}
          disabled={!hasSelection}
          className={cn(
            'p-2 rounded-md transition-colors',
            hasSelection 
              ? 'text-gray-600 hover:text-red-600 hover:bg-red-50' 
              : 'text-gray-300 cursor-not-allowed'
          )}
          title="Delete (Delete)"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Divider */}
      <div className="h-6 w-px bg-gray-200" />

      {/* Layout */}
      <button
        onClick={onAutoLayout}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
        title="Auto Layout"
      >
        <LayoutGrid className="w-4 h-4" />
      </button>

      {/* Schedule */}
      <button
        onClick={onOpenSchedule}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
        title="Schedule"
      >
        <Clock className="w-4 h-4" />
      </button>

      {/* Settings */}
      <button
        onClick={onOpenSettings}
        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
        title="Workflow Settings"
      >
        <Settings className="w-4 h-4" />
      </button>

      {/* Divider */}
      <div className="h-6 w-px bg-gray-200" />

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        {/* Test Button */}
        <button
          onClick={onTest}
          disabled={isRunning}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
            'border border-gray-300 text-gray-700 hover:bg-gray-50',
            isRunning && 'opacity-50 cursor-not-allowed'
          )}
        >
          <TestTube className="w-4 h-4" />
          Test
        </button>

        {/* Save Button */}
        <button
          onClick={onSave}
          disabled={isSaving || !isDirty}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
            'border border-gray-300 text-gray-700 hover:bg-gray-50',
            (isSaving || !isDirty) && 'opacity-50 cursor-not-allowed'
          )}
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Saving...' : 'Save'}
        </button>

        {/* Run Button */}
        <button
          onClick={onRun}
          disabled={isRunning || isDirty}
          className={cn(
            'flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-colors',
            'bg-green-600 text-white hover:bg-green-700',
            (isRunning || isDirty) && 'opacity-50 cursor-not-allowed'
          )}
          title={isDirty ? 'Save before running' : 'Run workflow'}
        >
          <Play className="w-4 h-4" />
          {isRunning ? 'Running...' : 'Run'}
        </button>
      </div>
    </div>
  );
};

export default WorkflowToolbar;
