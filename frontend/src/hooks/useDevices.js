import { useState, useEffect, useCallback } from "react";
import { fetchApi } from "../lib/utils";

export function useDevices() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDevices = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchApi("/data");
      setDevices(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  return { devices, loading, error, refetch: fetchDevices };
}

export function useGroups() {
  const [groups, setGroups] = useState({ network: [], custom: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchGroups = useCallback(async () => {
    try {
      setLoading(true);
      
      // Fetch both custom groups and network groups in parallel
      const [customData, networkData] = await Promise.all([
        fetchApi("/device_groups?" + Date.now()),
        fetchApi("/network_groups?" + Date.now())
      ]);
      
      setGroups({
        custom: customData || [],
        network: networkData || []
      });
      setError(null);
    } catch (err) {
      console.error("Error fetching groups:", err);
      setError("Failed to load groups");
      setGroups({ network: [], custom: [] });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGroups();
  }, [fetchGroups]);

  const createGroup = async (groupData) => {
    // First create the group
    const groupResponse = await fetchApi("/device_groups", {
      method: "POST",
      body: JSON.stringify({
        group_name: groupData.name,
        description: groupData.description,
      }),
    });
    
    // Then add devices to the group if any
    if (groupData.devices && groupData.devices.length > 0) {
      const groupId = groupResponse.id || groupResponse.group_id;
      if (groupId) {
        await fetchApi(`/device_groups/${groupId}/devices`, {
          method: "POST",
          body: JSON.stringify({
            ip_addresses: groupData.devices,
          }),
        });
      }
    }
    
    await fetchGroups();
  };

  const updateGroup = async (id, groupData) => {
    await fetchApi(`/device_groups/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        group_name: groupData.name,
        description: groupData.description,
      }),
    });
    
    // TODO: Handle device updates for groups - might need to sync devices
    
    await fetchGroups();
  };

  const deleteGroup = async (id) => {
    await fetchApi(`/device_groups/${id}`, {
      method: "DELETE",
    });
    await fetchGroups();
  };

  return {
    groups,
    loading,
    error,
    refetch: fetchGroups,
    createGroup,
    updateGroup,
    deleteGroup,
  };
}

export function useScanProgress() {
  const [progress, setProgress] = useState({
    scanned: 0,
    total: 0,
    online: 0,
    status: "idle",
  });

  useEffect(() => {
    let errorCount = 0;
    let intervalId = null;

    const poll = async () => {
      try {
        const data = await fetchApi("/progress");
        setProgress(data);
        errorCount = 0; // reset on success
      } catch (err) {
        errorCount++;
        // Stop polling after 3 consecutive failures to avoid spamming
        if (errorCount >= 3 && intervalId) {
          clearInterval(intervalId);
          intervalId = null;
          console.warn("Progress polling stopped after repeated failures");
        }
      }
    };

    // Poll every 5 seconds instead of 1 second
    intervalId = setInterval(poll, 5000);
    // Initial fetch
    poll();

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, []);

  const startScan = async () => {
    await fetchApi("/scan", { method: "POST" });
  };

  return { progress, startScan };
}
