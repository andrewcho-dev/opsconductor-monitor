export { GeneralSettings } from './GeneralSettings';
export { DatabaseSettings } from './DatabaseSettings';
export { PasswordPolicySettings } from './PasswordPolicySettings';
export { LoggingSettings } from './LoggingSettings';
export { NetBoxSettings } from './NetBoxSettings';
export { default as PRTGSettings } from './PRTGSettings';

// SecuritySettings now uses PasswordPolicySettings
export { PasswordPolicySettings as SecuritySettings } from './PasswordPolicySettings';

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
