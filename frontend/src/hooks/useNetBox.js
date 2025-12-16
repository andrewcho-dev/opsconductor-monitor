import { useState, useEffect, useCallback } from "react";
import { fetchApi } from "../lib/utils";

const extractData = (response) => {
  if (response && response.data !== undefined) {
    return response.data;
  }
  return response;
};

/**
 * Hook to check NetBox connection status
 */
export function useNetBoxStatus() {
  const [status, setStatus] = useState({
    configured: false,
    connected: false,
    version: null,
    loading: true,
    error: null,
  });

  const checkStatus = useCallback(async () => {
    try {
      setStatus(prev => ({ ...prev, loading: true }));
      
      // First check if NetBox is configured
      const settingsRes = await fetchApi("/api/netbox/settings");
      const settings = extractData(settingsRes);
      
      if (!settings?.url || !settings?.token_configured) {
        setStatus({
          configured: false,
          connected: false,
          version: null,
          loading: false,
          error: null,
        });
        return;
      }
      
      // Test connection
      const testRes = await fetchApi("/api/netbox/test", { method: "POST" });
      
      if (testRes.success) {
        setStatus({
          configured: true,
          connected: true,
          version: testRes.data?.netbox_version,
          loading: false,
          error: null,
        });
      } else {
        setStatus({
          configured: true,
          connected: false,
          version: null,
          loading: false,
          error: testRes.error?.message || "Connection failed",
        });
      }
    } catch (err) {
      setStatus({
        configured: false,
        connected: false,
        version: null,
        loading: false,
        error: err.message,
      });
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  return { ...status, refresh: checkStatus };
}

/**
 * Hook to fetch devices from NetBox
 */
export function useNetBoxDevices(options = {}) {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({ count: 0, next: null, previous: null });

  const fetchDevices = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      
      const queryParams = new URLSearchParams();
      if (params.site) queryParams.set("site", params.site);
      if (params.role) queryParams.set("role", params.role);
      if (params.status) queryParams.set("status", params.status);
      if (params.search) queryParams.set("q", params.search);
      if (params.limit) queryParams.set("limit", params.limit);
      if (params.offset) queryParams.set("offset", params.offset);
      
      const url = `/api/netbox/devices${queryParams.toString() ? `?${queryParams}` : ""}`;
      const response = await fetchApi(url);
      
      // Transform NetBox device format to match our UI expectations
      const transformedDevices = (response.data || []).map(device => ({
        id: device.id,
        ip_address: device.primary_ip4?.address?.split("/")[0] || device.name,
        hostname: device.name,
        description: device.description || device.device_type?.display,
        vendor: device.device_type?.manufacturer?.name,
        model: device.device_type?.model,
        serial: device.serial,
        status: device.status?.value || "active",
        site: device.site?.name,
        role: device.role?.name,
        // For compatibility with existing UI
        ping_status: device.status?.value === "active" ? "online" : "unknown",
        snmp_status: "unknown",
        network_range: null,
        // Keep original NetBox data
        _netbox: device,
      }));
      
      setDevices(transformedDevices);
      setPagination({
        count: response.count || transformedDevices.length,
        next: response.next,
        previous: response.previous,
      });
      setError(null);
    } catch (err) {
      setError(err.message);
      setDevices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices(options);
  }, []);

  return { 
    devices, 
    loading, 
    error, 
    pagination,
    refetch: fetchDevices,
  };
}

/**
 * Hook to fetch a single device from NetBox
 */
export function useNetBoxDevice(deviceId) {
  const [device, setDevice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDevice = useCallback(async () => {
    if (!deviceId) {
      setDevice(null);
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      const response = await fetchApi(`/api/netbox/devices/${deviceId}`);
      const data = extractData(response);
      
      // Transform to match UI expectations
      setDevice({
        id: data.id,
        ip_address: data.primary_ip4?.address?.split("/")[0] || data.name,
        hostname: data.name,
        description: data.description,
        vendor: data.device_type?.manufacturer?.name,
        model: data.device_type?.model,
        serial: data.serial,
        status: data.status?.value,
        site: data.site?.name,
        role: data.role?.name,
        location: data.location?.name,
        rack: data.rack?.name,
        position: data.position,
        comments: data.comments,
        tags: data.tags?.map(t => t.name) || [],
        created: data.created,
        last_updated: data.last_updated,
        _netbox: data,
      });
      setError(null);
    } catch (err) {
      setError(err.message);
      setDevice(null);
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => {
    fetchDevice();
  }, [fetchDevice]);

  return { device, loading, error, refetch: fetchDevice };
}

/**
 * Hook to fetch NetBox lookup data (sites, roles, etc.)
 */
export function useNetBoxLookups() {
  const [lookups, setLookups] = useState({
    sites: [],
    roles: [],
    deviceTypes: [],
    manufacturers: [],
  });
  const [loading, setLoading] = useState(true);

  const fetchLookups = useCallback(async () => {
    try {
      setLoading(true);
      
      const [sitesRes, rolesRes, typesRes, mfrsRes] = await Promise.all([
        fetchApi("/api/netbox/sites").catch(() => ({ data: [] })),
        fetchApi("/api/netbox/device-roles").catch(() => ({ data: [] })),
        fetchApi("/api/netbox/device-types").catch(() => ({ data: [] })),
        fetchApi("/api/netbox/manufacturers").catch(() => ({ data: [] })),
      ]);
      
      setLookups({
        sites: extractData(sitesRes) || [],
        roles: extractData(rolesRes) || [],
        deviceTypes: extractData(typesRes) || [],
        manufacturers: extractData(mfrsRes) || [],
      });
    } catch (err) {
      console.error("Failed to load NetBox lookups:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLookups();
  }, [fetchLookups]);

  return { lookups, loading, refetch: fetchLookups };
}

export default {
  useNetBoxStatus,
  useNetBoxDevices,
  useNetBoxDevice,
  useNetBoxLookups,
};
