import { useCallback, useEffect, useState } from 'react';

const FALLBACK_TARGETS = {
  network_ranges: ['192.168.1.0/24', '10.0.0.0/16', '172.16.0.0/12', '192.168.10.0/24'],
  custom_groups: ['Production Servers', 'Development Environment', 'Test Network', 'DMZ Servers'],
  network_groups: ['Core Infrastructure', 'Edge Devices', 'Security Appliances', 'Monitoring Systems']
};

export const useAvailableTargets = () => {
  const [availableTargets, setAvailableTargets] = useState({
    network_ranges: [],
    custom_groups: [],
    network_groups: []
  });
  const [targetsLoading, setTargetsLoading] = useState(false);

  const fetchTargets = useCallback(async () => {
    setTargetsLoading(true);
    try {
      const [networkRes, customRes, groupRes] = await Promise.all([
        fetch('/api/network-ranges'),
        fetch('/api/custom-groups'),
        fetch('/api/network-groups')
      ]);

      const [networkData, customData, groupData] = await Promise.all([
        networkRes.json(),
        customRes.json(),
        groupRes.json()
      ]);

      setAvailableTargets({
        network_ranges: networkData.ranges || [],
        custom_groups: customData.groups || [],
        network_groups: groupData.groups || []
      });
    } catch (error) {
      console.error('Failed to fetch available targets:', error);
      setAvailableTargets(FALLBACK_TARGETS);
    } finally {
      setTargetsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTargets();
  }, [fetchTargets]);

  return { availableTargets, targetsLoading, refreshTargets: fetchTargets };
};
