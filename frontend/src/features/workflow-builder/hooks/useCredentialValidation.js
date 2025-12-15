/**
 * useCredentialValidation Hook
 * 
 * Provides design-time validation for workflow nodes that require credentials.
 * Checks if required credentials are configured in the credential vault.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchApi } from '../../../lib/api';

// Credential type mapping from node requirements to vault types
const CREDENTIAL_TYPE_MAP = {
  'ssh_credentials': 'ssh',
  'ciena_credentials': 'ssh',
  'axis_credentials': 'password',
  'snmp_credentials': 'snmp',
  'database_credentials': 'password',
  'smtp_credentials': 'password',
  'slack_credentials': 'api_key',
  'aws_credentials': 'api_key',
  'ftp_credentials': 'password',
};

export function useCredentialValidation() {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch credentials from the vault
  const fetchCredentials = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetchApi('/api/credentials');
      if (response.success && response.data?.credentials) {
        setCredentials(response.data.credentials);
      }
      setError(null);
    } catch (err) {
      console.error('Failed to fetch credentials:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCredentials();
  }, [fetchCredentials]);

  // Get credentials by type
  const getCredentialsByType = useCallback((type) => {
    const vaultType = CREDENTIAL_TYPE_MAP[type] || type;
    return credentials.filter(c => c.credential_type === vaultType);
  }, [credentials]);

  // Check if a specific credential type is available
  const hasCredentialType = useCallback((type) => {
    return getCredentialsByType(type).length > 0;
  }, [getCredentialsByType]);

  // Validate a node's credential requirements
  const validateNodeCredentials = useCallback((node) => {
    const requirements = node.execution?.requirements;
    if (!requirements?.credentials || requirements.credentials.length === 0) {
      return { valid: true, missing: [], available: [] };
    }

    const missing = [];
    const available = [];

    for (const credType of requirements.credentials) {
      const creds = getCredentialsByType(credType);
      if (creds.length === 0) {
        missing.push({
          type: credType,
          vaultType: CREDENTIAL_TYPE_MAP[credType] || credType,
          label: getCredentialLabel(credType),
        });
      } else {
        available.push({
          type: credType,
          vaultType: CREDENTIAL_TYPE_MAP[credType] || credType,
          label: getCredentialLabel(credType),
          count: creds.length,
          credentials: creds,
        });
      }
    }

    return {
      valid: missing.length === 0,
      missing,
      available,
    };
  }, [getCredentialsByType]);

  // Validate all nodes in a workflow
  const validateWorkflowCredentials = useCallback((nodes) => {
    const results = {
      valid: true,
      nodeResults: {},
      missingCredentials: new Set(),
    };

    for (const node of nodes) {
      const nodeValidation = validateNodeCredentials(node);
      results.nodeResults[node.id] = nodeValidation;
      
      if (!nodeValidation.valid) {
        results.valid = false;
        nodeValidation.missing.forEach(m => results.missingCredentials.add(m.type));
      }
    }

    results.missingCredentials = Array.from(results.missingCredentials);
    return results;
  }, [validateNodeCredentials]);

  // Get human-readable label for credential type
  const getCredentialLabel = (type) => {
    const labels = {
      'ssh_credentials': 'SSH Credentials',
      'ciena_credentials': 'Ciena Device Credentials',
      'snmp_credentials': 'SNMP Credentials',
      'database_credentials': 'Database Credentials',
      'smtp_credentials': 'SMTP/Email Credentials',
      'slack_credentials': 'Slack API Credentials',
      'aws_credentials': 'AWS Credentials',
      'ftp_credentials': 'FTP Credentials',
    };
    return labels[type] || type;
  };

  // Summary of available credentials
  const credentialSummary = useMemo(() => {
    const summary = {};
    for (const [reqType, vaultType] of Object.entries(CREDENTIAL_TYPE_MAP)) {
      const creds = credentials.filter(c => c.credential_type === vaultType);
      summary[reqType] = {
        available: creds.length > 0,
        count: creds.length,
        credentials: creds,
      };
    }
    return summary;
  }, [credentials]);

  return {
    credentials,
    loading,
    error,
    refresh: fetchCredentials,
    hasCredentialType,
    getCredentialsByType,
    validateNodeCredentials,
    validateWorkflowCredentials,
    credentialSummary,
    getCredentialLabel,
  };
}

export default useCredentialValidation;
