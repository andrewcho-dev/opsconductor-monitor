/**
 * Credential Vault Constants
 * 
 * Shared constants for credential types and status colors.
 */

import { Terminal, Shield, Server, Key, KeyRound, FileKey } from 'lucide-react';

export const CREDENTIAL_TYPES = {
  ssh: { label: 'SSH', icon: Terminal, color: 'bg-blue-100 text-blue-700 border-blue-200' },
  winrm: { label: 'WinRM', icon: Shield, color: 'bg-cyan-100 text-cyan-700 border-cyan-200' },
  snmp: { label: 'SNMP', icon: Server, color: 'bg-green-100 text-green-700 border-green-200' },
  api_key: { label: 'API Key', icon: Key, color: 'bg-purple-100 text-purple-700 border-purple-200' },
  password: { label: 'Password', icon: KeyRound, color: 'bg-orange-100 text-orange-700 border-orange-200' },
  certificate: { label: 'Certificate', icon: FileKey, color: 'bg-pink-100 text-pink-700 border-pink-200' },
  pki: { label: 'PKI', icon: FileKey, color: 'bg-rose-100 text-rose-700 border-rose-200' },
  ldap: { label: 'LDAP', icon: Server, color: 'bg-indigo-100 text-indigo-700 border-indigo-200' },
  active_directory: { label: 'Active Directory', icon: Shield, color: 'bg-sky-100 text-sky-700 border-sky-200' },
  tacacs: { label: 'TACACS+', icon: Shield, color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  radius: { label: 'RADIUS', icon: Server, color: 'bg-teal-100 text-teal-700 border-teal-200' },
};

export const STATUS_COLORS = {
  active: 'bg-green-100 text-green-700',
  disabled: 'bg-gray-100 text-gray-600',
  expired: 'bg-red-100 text-red-700',
  expiring_soon: 'bg-amber-100 text-amber-700',
  revoked: 'bg-red-100 text-red-700',
};

export const AUTH_TYPE_LABELS = {
  tacacs: { label: 'TACACS+', color: 'bg-emerald-100 text-emerald-700', icon: Shield },
  radius: { label: 'RADIUS', color: 'bg-teal-100 text-teal-700', icon: Server },
  ldap: { label: 'LDAP', color: 'bg-indigo-100 text-indigo-700', icon: Server },
  active_directory: { label: 'Active Directory', color: 'bg-sky-100 text-sky-700', icon: Shield },
};
