/**
 * Scheduling Package
 * 
 * Nodes for scheduling and timing:
 * - Cron Trigger
 * - Interval Trigger
 * - Schedule Trigger
 */

export default {
  id: 'scheduling',
  name: 'Scheduling',
  description: 'Schedule workflows with cron, intervals, and time-based triggers',
  version: '1.0.0',
  icon: '⏰',
  color: '#10B981',
  
  nodes: {
    'schedule:cron': {
      name: 'Cron Trigger',
      description: 'Trigger workflow on a cron schedule',
      category: 'triggers',
      icon: '📅',
      color: '#10B981',
      
      inputs: [],
      outputs: [
        { id: 'output', type: 'trigger', label: 'On Schedule' },
      ],
      
      parameters: [
        {
          id: 'mode',
          type: 'select',
          label: 'Mode',
          default: 'preset',
          options: [
            { value: 'preset', label: 'Use Preset' },
            { value: 'custom', label: 'Custom Cron Expression' },
          ],
        },
        {
          id: 'preset',
          type: 'select',
          label: 'Schedule',
          default: 'every_hour',
          options: [
            { value: 'every_minute', label: 'Every Minute' },
            { value: 'every_5_minutes', label: 'Every 5 Minutes' },
            { value: 'every_15_minutes', label: 'Every 15 Minutes' },
            { value: 'every_30_minutes', label: 'Every 30 Minutes' },
            { value: 'every_hour', label: 'Every Hour' },
            { value: 'every_day_midnight', label: 'Every Day at Midnight' },
            { value: 'every_day_6am', label: 'Every Day at 6 AM' },
            { value: 'every_day_noon', label: 'Every Day at Noon' },
            { value: 'every_week_monday', label: 'Every Monday at Midnight' },
            { value: 'every_month_first', label: 'First Day of Month' },
          ],
          showIf: { field: 'mode', value: 'preset' },
        },
        {
          id: 'cron_expression',
          type: 'text',
          label: 'Cron Expression',
          default: '0 * * * *',
          showIf: { field: 'mode', value: 'custom' },
          help: 'Format: minute hour day-of-month month day-of-week',
        },
        {
          id: 'timezone',
          type: 'select',
          label: 'Timezone',
          default: 'UTC',
          options: [
            { value: 'UTC', label: 'UTC' },
            { value: 'America/New_York', label: 'Eastern Time' },
            { value: 'America/Chicago', label: 'Central Time' },
            { value: 'America/Denver', label: 'Mountain Time' },
            { value: 'America/Los_Angeles', label: 'Pacific Time' },
            { value: 'Europe/London', label: 'London' },
            { value: 'Europe/Paris', label: 'Paris' },
            { value: 'Asia/Tokyo', label: 'Tokyo' },
          ],
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'cron_trigger',
        context: 'local',
        platform: 'any',
        requirements: {},
      },
    },

    'schedule:interval': {
      name: 'Interval Trigger',
      description: 'Trigger workflow at regular intervals',
      category: 'triggers',
      icon: '🔁',
      color: '#10B981',
      
      inputs: [],
      outputs: [
        { id: 'output', type: 'trigger', label: 'On Interval' },
      ],
      
      parameters: [
        {
          id: 'interval',
          type: 'number',
          label: 'Interval',
          default: 5,
          min: 1,
          required: true,
        },
        {
          id: 'unit',
          type: 'select',
          label: 'Unit',
          default: 'minutes',
          options: [
            { value: 'seconds', label: 'Seconds' },
            { value: 'minutes', label: 'Minutes' },
            { value: 'hours', label: 'Hours' },
          ],
        },
        {
          id: 'run_immediately',
          type: 'checkbox',
          label: 'Run Immediately on Start',
          default: true,
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'interval_trigger',
        context: 'local',
        platform: 'any',
        requirements: {},
      },
    },

    'schedule:time-trigger': {
      name: 'Time Trigger',
      description: 'Trigger workflow at specific times',
      category: 'triggers',
      icon: '🕐',
      color: '#10B981',
      
      inputs: [],
      outputs: [
        { id: 'output', type: 'trigger', label: 'On Time' },
      ],
      
      parameters: [
        {
          id: 'times',
          type: 'time-list',
          label: 'Times',
          default: ['09:00'],
          help: 'Times to trigger (24-hour format)',
        },
        {
          id: 'days',
          type: 'multi-select',
          label: 'Days',
          default: ['mon', 'tue', 'wed', 'thu', 'fri'],
          options: [
            { value: 'sun', label: 'Sunday' },
            { value: 'mon', label: 'Monday' },
            { value: 'tue', label: 'Tuesday' },
            { value: 'wed', label: 'Wednesday' },
            { value: 'thu', label: 'Thursday' },
            { value: 'fri', label: 'Friday' },
            { value: 'sat', label: 'Saturday' },
          ],
        },
        {
          id: 'timezone',
          type: 'select',
          label: 'Timezone',
          default: 'UTC',
          options: [
            { value: 'UTC', label: 'UTC' },
            { value: 'America/New_York', label: 'Eastern Time' },
            { value: 'America/Chicago', label: 'Central Time' },
            { value: 'America/Denver', label: 'Mountain Time' },
            { value: 'America/Los_Angeles', label: 'Pacific Time' },
            { value: 'Europe/London', label: 'London' },
            { value: 'Europe/Paris', label: 'Paris' },
            { value: 'Asia/Tokyo', label: 'Tokyo' },
          ],
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'time_trigger',
        context: 'local',
        platform: 'any',
        requirements: {},
      },
    },

    'schedule:date-trigger': {
      name: 'Date Trigger',
      description: 'Trigger workflow on specific dates',
      category: 'triggers',
      icon: '📆',
      color: '#10B981',
      
      inputs: [],
      outputs: [
        { id: 'output', type: 'trigger', label: 'On Date' },
      ],
      
      parameters: [
        {
          id: 'dates',
          type: 'date-list',
          label: 'Dates',
          default: [],
          help: 'Specific dates to trigger',
        },
        {
          id: 'time',
          type: 'text',
          label: 'Time',
          default: '09:00',
          help: 'Time to trigger (24-hour format)',
        },
        {
          id: 'timezone',
          type: 'select',
          label: 'Timezone',
          default: 'UTC',
          options: [
            { value: 'UTC', label: 'UTC' },
            { value: 'America/New_York', label: 'Eastern Time' },
            { value: 'America/Los_Angeles', label: 'Pacific Time' },
          ],
        },
        {
          id: 'repeat_yearly',
          type: 'checkbox',
          label: 'Repeat Yearly',
          default: false,
        },
      ],
      
      execution: {
        type: 'trigger',
        executor: 'date_trigger',
        context: 'local',
        platform: 'any',
        requirements: {},
      },
    },
  },
};
