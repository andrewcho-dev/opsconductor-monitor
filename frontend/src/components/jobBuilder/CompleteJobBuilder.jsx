import React, { useEffect, useMemo, useState } from 'react';
import JobBuilderErrorBoundary from './JobBuilderErrorBoundary';
import { DEFAULT_JOB, createEmptyAction } from './defaultJob';
import { useAvailableTargets } from './hooks/useAvailableTargets';
import TargetSelectionModal from './TargetSelectionModal';
import { JobHeader } from './sections/JobHeader';
import { JobInformation } from './sections/JobInformation';
import { ExecutionConfiguration } from './sections/ExecutionConfiguration';
import { ActionsList } from './sections/ActionsList';
import { RawJsonPanel } from './sections/RawJsonPanel';
import { RegexTestingPanel } from './sections/RegexTestingPanel';

const DATABASE_SOURCES = new Set(['network_range', 'custom_groups', 'network_groups']);

const SOURCE_KEY_MAP = {
  network_range: 'network_ranges',
  custom_groups: 'custom_groups',
  network_groups: 'network_groups'
};

const cloneJob = (job) => JSON.parse(JSON.stringify(job));

const CompleteJobBuilderInner = ({ job, onSave, onTest, onBack }) => {
  const initialJob = useMemo(() => cloneJob(job || DEFAULT_JOB), [job]);
  const [currentJob, setCurrentJob] = useState(initialJob);
  const [testMode, setTestMode] = useState(false);
  const [testActionIndex, setTestActionIndex] = useState(0);
  const [testInput, setTestInput] = useState(
    'PING 192.168.1.1 (192.168.1.1): 56 data bytes\n64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=0.123 ms'
  );
  const [testResults, setTestResults] = useState([]);
  const [activeTargetModal, setActiveTargetModal] = useState({ open: false, actionIndex: null, sourceType: null });

  const { availableTargets, targetsLoading, refreshTargets } = useAvailableTargets();

  useEffect(() => {
    setCurrentJob(cloneJob(job || DEFAULT_JOB));
  }, [job]);

  useEffect(() => {
    if (testActionIndex >= currentJob.actions.length) {
      setTestActionIndex(Math.max(0, currentJob.actions.length - 1));
    }
  }, [currentJob.actions.length, testActionIndex]);

  const updateAction = (actionIndex, path, value) => {
    setCurrentJob((prev) => {
      const actions = prev.actions.map((action, idx) => {
        if (idx !== actionIndex) return action;

        const updated = { ...action };
        const keys = path.split('.');
        let cursor = updated;

        for (let i = 0; i < keys.length - 1; i++) {
          const key = keys[i];
          const next = cursor[key];

          if (Array.isArray(next)) {
            cursor[key] = [...next];
          } else if (typeof next === 'object' && next !== null) {
            cursor[key] = { ...next };
          } else {
            cursor[key] = {};
          }

          cursor = cursor[key];
        }

        cursor[keys[keys.length - 1]] = value;
        return updated;
      });

      return { ...prev, actions };
    });
  };

  const addAction = () => {
    setCurrentJob((prev) => ({
      ...prev,
      actions: [...prev.actions, createEmptyAction()]
    }));
  };

  const deleteAction = (actionIndex) => {
    setCurrentJob((prev) => ({
      ...prev,
      actions: prev.actions.filter((_, idx) => idx !== actionIndex)
    }));
  };

  const moveAction = (actionIndex, direction) => {
    setCurrentJob((prev) => {
      const actions = [...prev.actions];
      const targetIndex = direction === 'up' ? actionIndex - 1 : actionIndex + 1;

      if (targetIndex < 0 || targetIndex >= actions.length) {
        return prev;
      }

      [actions[actionIndex], actions[targetIndex]] = [actions[targetIndex], actions[actionIndex]];
      return { ...prev, actions };
    });
  };

  const addParsingPattern = (actionIndex) => {
    setCurrentJob((prev) => {
      const actions = [...prev.actions];
      const action = { ...actions[actionIndex] };
      const resultParsing = { ...(action.result_parsing || {}) };
      const patterns = [...(resultParsing.patterns || [])];

      patterns.push({
        name: 'custom_pattern',
        regex: '(.*)',
        field_mapping: { custom_field: '$1' }
      });

      resultParsing.patterns = patterns;
      action.result_parsing = resultParsing;
      actions[actionIndex] = action;
      return { ...prev, actions };
    });
  };

  const updateParsingPattern = (actionIndex, patternIndex, field, value) => {
    setCurrentJob((prev) => {
      const actions = [...prev.actions];
      const action = { ...actions[actionIndex] };
      const resultParsing = { ...(action.result_parsing || {}) };
      const patterns = [...(resultParsing.patterns || [])];

      patterns[patternIndex] = {
        ...patterns[patternIndex],
        [field]: value
      };

      resultParsing.patterns = patterns;
      action.result_parsing = resultParsing;
      actions[actionIndex] = action;
      return { ...prev, actions };
    });
  };

  const removeParsingPattern = (actionIndex, patternIndex) => {
    setCurrentJob((prev) => {
      const actions = [...prev.actions];
      const action = { ...actions[actionIndex] };
      const resultParsing = { ...(action.result_parsing || {}) };
      const patterns = [...(resultParsing.patterns || [])];

      patterns.splice(patternIndex, 1);

      resultParsing.patterns = patterns;
      action.result_parsing = resultParsing;
      actions[actionIndex] = action;
      return { ...prev, actions };
    });
  };

  const resetTargetingForSource = (actionIndex, source) => {
    updateAction(actionIndex, 'targeting.source', source);

    if (source === 'network_range') {
      updateAction(actionIndex, 'targeting.network_range', '');
    } else if (source === 'custom_groups' || source === 'network_groups') {
      updateAction(actionIndex, `targeting.${source}`, []);
    } else if (source === 'target_list') {
      updateAction(actionIndex, 'targeting.target_list', '');
    } else if (source === 'file') {
      updateAction(actionIndex, 'targeting.file_path', '');
    }
  };

  const handleSourceChange = (actionIndex, source) => {
    resetTargetingForSource(actionIndex, source);

    if (DATABASE_SOURCES.has(source)) {
      setActiveTargetModal({ open: true, actionIndex, sourceType: source });
    }
  };

  const openTargetModal = (actionIndex, sourceType) => {
    setActiveTargetModal({ open: true, actionIndex, sourceType });
  };

  const closeTargetModal = () => {
    setActiveTargetModal({ open: false, actionIndex: null, sourceType: null });
  };

  const handleTargetSelection = (value) => {
    const { actionIndex, sourceType } = activeTargetModal;
    if (actionIndex == null) return;

    if (sourceType === 'network_range') {
      updateAction(actionIndex, 'targeting.network_range', value);
    } else if (sourceType === 'custom_groups' || sourceType === 'network_groups') {
      updateAction(actionIndex, `targeting.${sourceType}`, [value]);
    }

    closeTargetModal();
  };

  const handleCustomTarget = (rawValue) => {
    const { actionIndex, sourceType } = activeTargetModal;
    if (actionIndex == null) return;

    if (sourceType === 'network_range') {
      updateAction(actionIndex, 'targeting.network_range', rawValue.trim());
      closeTargetModal();
      return;
    }

    try {
      const parsed = JSON.parse(rawValue);
      if (Array.isArray(parsed)) {
        updateAction(actionIndex, `targeting.${sourceType}`, parsed);
        closeTargetModal();
        return;
      }
    } catch (err) {
      // fall back to newline-split below
    }

    const list = rawValue
      .split(/\n+/)
      .map((entry) => entry.trim())
      .filter(Boolean);

    updateAction(actionIndex, `targeting.${sourceType}`, list);
    closeTargetModal();
  };

  const runRegexTest = () => {
    if (!testMode) {
      setTestResults([]);
      return;
    }

    const action = currentJob.actions[testActionIndex];
    const patterns = action?.result_parsing?.patterns || [];

    if (!action || patterns.length === 0) {
      setTestResults([]);
      return;
    }

    const results = [];
    const input = testInput;

    patterns.forEach((pattern) => {
      try {
        const regex = new RegExp(pattern.regex, 'g');
        const matches = [];
        let match;

        while ((match = regex.exec(input)) !== null) {
          const mappedFields = {};

          Object.entries(pattern.field_mapping || {}).forEach(([field, mapping]) => {
            if (typeof mapping === 'string' && mapping.startsWith('$')) {
              const index = Number.parseInt(mapping.substring(1), 10);
              mappedFields[field] = match[index] ?? '';
            } else {
              mappedFields[field] = mapping;
            }
          });

          matches.push({
            patternName: pattern.name,
            match: match[0],
            groups: match.slice(1),
            mappedFields
          });
        }

        if (matches.length > 0) {
          results.push({
            patternName: pattern.name,
            regex: pattern.regex,
            matches,
            success: true
          });
        } else {
          results.push({
            patternName: pattern.name,
            regex: pattern.regex,
            matches: [],
            success: false,
            error: 'No matches found'
          });
        }
      } catch (error) {
        results.push({
          patternName: pattern.name,
          regex: pattern.regex,
          matches: [],
          success: false,
          error: error.message
        });
      }
    });

    const aggregated = {
      parsedFields: { ...(action.result_parsing?.default_values || {}) },
      patterns: results
    };

    results
      .filter((result) => result.success)
      .forEach((result) => {
        result.matches.forEach((match) => {
          Object.assign(aggregated.parsedFields, match.mappedFields);
        });
      });

    setTestResults([aggregated]);
  };

  useEffect(() => {
    if (testMode) {
      runRegexTest();
    }
  }, [testMode, testInput, testActionIndex, currentJob.actions]);

  const modalItems = useMemo(() => {
    if (!activeTargetModal.open) return [];
    const sourceKey = SOURCE_KEY_MAP[activeTargetModal.sourceType];
    return sourceKey ? availableTargets[sourceKey] || [] : [];
  }, [activeTargetModal, availableTargets]);

  const modalSelectedValue = useMemo(() => {
    if (!activeTargetModal.open) return null;
    const action = currentJob.actions[activeTargetModal.actionIndex];
    if (!action) return null;

    if (activeTargetModal.sourceType === 'network_range') {
      return action.targeting?.network_range || '';
    }

    if (activeTargetModal.sourceType === 'custom_groups' || activeTargetModal.sourceType === 'network_groups') {
      return action.targeting?.[activeTargetModal.sourceType] || [];
    }

    return null;
  }, [activeTargetModal, currentJob.actions]);

  return (
    <div className="min-h-screen bg-gray-100 p-2">
      <div className="w-full space-y-2">
        <JobHeader
          testMode={testMode}
          onToggleTestMode={setTestMode}
          onBack={onBack}
          onTest={(payload) => onTest?.(payload)}
          onSave={(payload) => onSave?.(payload)}
          currentJob={currentJob}
        />

        <div className="grid grid-cols-1 gap-2 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-2">
            <JobInformation currentJob={currentJob} setCurrentJob={setCurrentJob} />
            <ExecutionConfiguration currentJob={currentJob} setCurrentJob={setCurrentJob} />
            <ActionsList
              actions={currentJob.actions}
              onAddAction={addAction}
              updateAction={updateAction}
              deleteAction={deleteAction}
              moveAction={moveAction}
              onOpenTargetModal={openTargetModal}
              onSourceChange={handleSourceChange}
              onAddPattern={addParsingPattern}
              onUpdatePattern={updateParsingPattern}
              onRemovePattern={removeParsingPattern}
            />
            <RawJsonPanel currentJob={currentJob} />
          </div>

          <div className="lg:col-span-1">
            <RegexTestingPanel
              testMode={testMode}
              setTestMode={setTestMode}
              testActionIndex={testActionIndex}
              setTestActionIndex={setTestActionIndex}
              testInput={testInput}
              setTestInput={setTestInput}
              testResults={testResults}
              actions={currentJob.actions}
            />
          </div>
        </div>
      </div>

      <TargetSelectionModal
        isOpen={activeTargetModal.open}
        sourceType={activeTargetModal.sourceType}
        items={modalItems}
        selectedValue={modalSelectedValue}
        onSelect={handleTargetSelection}
        onCustomSubmit={handleCustomTarget}
        onClose={closeTargetModal}
        loading={targetsLoading}
        onRefresh={refreshTargets}
      />
    </div>
  );
};

const CompleteJobBuilder = (props) => (
  <JobBuilderErrorBoundary>
    <CompleteJobBuilderInner {...props} />
  </JobBuilderErrorBoundary>
);

export default CompleteJobBuilder;
