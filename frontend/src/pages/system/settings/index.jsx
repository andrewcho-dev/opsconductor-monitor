export { GeneralSettings } from './GeneralSettings';
export { NetworkSettings } from './NetworkSettings';
export { SSHSettings } from './SSHSettings';
export { DatabaseSettings } from './DatabaseSettings';
export { APISettings } from './APISettings';

// Placeholder components for remaining settings pages
export function SecuritySettings() {
  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Security Settings</h2>
        <p className="text-sm text-gray-500">Authentication, authorization, and security policies.</p>
        <p className="mt-4 text-sm text-gray-400 italic">Coming soon...</p>
      </div>
    </div>
  );
}

export function LoggingSettings() {
  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Logging Settings</h2>
        <p className="text-sm text-gray-500">Configure log levels, retention, and output destinations.</p>
        <p className="mt-4 text-sm text-gray-400 italic">Coming soon...</p>
      </div>
    </div>
  );
}

export function BackupSettings() {
  return (
    <div className="max-w-2xl">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Backup Settings</h2>
        <p className="text-sm text-gray-500">Configure automated backups and restore options.</p>
        <p className="mt-4 text-sm text-gray-400 italic">Coming soon...</p>
      </div>
    </div>
  );
}
