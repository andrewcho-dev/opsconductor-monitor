import { useCallback, useEffect, useState } from 'react';

const FALLBACK_TARGETS = {
  network_ranges: [],
  custom_groups: [],
  network_groups: []
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
