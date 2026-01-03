/**
 * TemplateModal Component
 * 
 * Modal for creating and editing notification templates.
 */

import React, { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { fetchApi } from '../../../lib/utils';

export function TemplateModal({ template, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: template?.name || '',
    description: template?.description || '',
    template_type: template?.template_type || 'system',
    title_template: template?.title_template || '',
    body_template: template?.body_template || '',
    available_variables: template?.available_variables || []
  });
  const [saving, setSaving] = useState(false);

  const systemVariables = [
    'alert.title', 'alert.message', 'alert.severity', 'alert.category', 'alert.triggered_at', 'alert.details'
  ];
  const jobVariables = [
    'job.name', 'job.id', 'job.status', 'job.duration', 'job.started_at', 'job.finished_at', 
    'job.error', 'job.summary', 'job.results', 'workflow.name', 'workflow.variables'
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (template) {
        await fetchApi(`/api/notifications/templates/${template.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      } else {
        await fetchApi('/api/notifications/templates', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      }
      onSave();
    } catch (err) {
      alert('Error saving template: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const insertVariable = (variable) => {
    const textarea = document.getElementById('body-template');
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = formData.body_template;
      const newText = text.substring(0, start) + `{{${variable}}}` + text.substring(end);
      setFormData(prev => ({ ...prev, body_template: newText }));
    } else {
      setFormData(prev => ({ ...prev, body_template: prev.body_template + `{{${variable}}}` }));
    }
  };

  const suggestedVariables = formData.template_type === 'system' ? systemVariables : jobVariables;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b sticky top-0 bg-white">
          <h2 className="text-lg font-semibold">{template ? 'Edit Template' : 'Add Template'}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                placeholder="My Template"
                required
                disabled={template?.is_default}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={formData.template_type}
                onChange={(e) => setFormData(prev => ({ ...prev, template_type: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg"
                disabled={template?.is_default}
              >
                <option value="system">System (Alerts)</option>
                <option value="job">Job (Workflows)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="Optional description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title Template</label>
            <input
              type="text"
              value={formData.title_template}
              onChange={(e) => setFormData(prev => ({ ...prev, title_template: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm"
              placeholder="[{{alert.severity}}] {{alert.title}}"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Body Template</label>
            <textarea
              id="body-template"
              value={formData.body_template}
              onChange={(e) => setFormData(prev => ({ ...prev, body_template: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg font-mono text-sm h-40"
              placeholder="{{alert.message}}&#10;&#10;Severity: {{alert.severity}}"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Available Variables (click to insert)</label>
            <div className="flex gap-1 flex-wrap">
              {suggestedVariables.map((variable) => (
                <button
                  key={variable}
                  type="button"
                  onClick={() => insertVariable(variable)}
                  className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded font-mono"
                >
                  {`{{${variable}}}`}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {template ? 'Save Changes' : 'Create Template'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
