import { getCommand } from '../../../data/commandLibraries.js';

export const getActionType = (action) => {
  const method = action?.login_method?.type;
  switch (method) {
    case 'ping':
      return 'ping_scan';
    case 'snmp':
      return 'snmp_scan';
    case 'ssh_port':
      return 'ssh_scan';
    case 'rdp_port':
      return 'rdp_scan';
    case 'ssh_command':
      return 'ssh_command';
    case 'http_request':
      return 'http_check';
    case 'custom':
      return 'custom_scan';
    default:
      return action?.type || 'unknown_scan';
  }
};

export const getActionDisplayName = (action) => {
  if (!action) return 'UNKNOWN ACTION';

  if (action.login_method?.command_id) {
    const command = getCommand(action.login_method.platform || 'ubuntu-20.04', action.login_method.command_id);
    if (command?.name) {
      return command.name;
    }
    return action.login_method.command_id.toUpperCase();
  }

  return getActionType(action).toUpperCase();
};
