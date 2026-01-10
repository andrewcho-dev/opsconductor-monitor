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
      const settingsRes = await fetchApi("/integrations/v1/netbox/settings");
      const settings = extractData(settingsRes);
      
      // Check for url and either token_configured flag or actual token
      if (!settings?.url || (!settings?.token_configured && !settings?.token)) {
        setStatus({
          configured: false,
          connected: false,
          version: null,
          loading: false,
          error: null,
        });
        return;
      }
      
      // Test connection - pass empty config to use DB settings
      const testRes = await fetchApi("/integrations/v1/netbox/test", { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });
      
      // Handle both {success: true} and direct response formats
      const testData = testRes?.data || testRes;
      const isConnected = testRes?.success || testData?.success || testData?.connected;
      
      if (isConnected) {
        setStatus({
          configured: true,
          connected: true,
          version: testData?.netbox_version || testData?.version,
          loading: false,
          error: null,
        });
      } else {
        setStatus({
          configured: true,
          connected: false,
          version: null,
          loading: false,
          error: testData?.error?.message || testData?.message || "Connection failed",
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

  const transformDevice = (device) => {
    // Handle both nested NetBox API format and flat cached format
    const ip = device.primary_ip4?.address?.split("/")[0] || 
               (typeof device.primary_ip4 === 'string' ? device.primary_ip4.split("/")[0] : null) ||
               device.ip_address || device.name;
    return {
      id: device.id,
      ip_address: ip,
      ip_with_prefix: device.primary_ip4?.address || device.primary_ip4,
      hostname: device.name,
      name: device.name,
      description: device.description || device.device_type?.display || device.device_type,
      vendor: device.device_type?.manufacturer?.name || device.vendor,
      model: device.device_type?.model || device.model,
      serial: device.serial,
      status: device.status?.value || device.status || "active",
      status_label: device.status?.label || device.status || "Active",
      site: device.site?.name || device.site,
      site_slug: device.site?.slug || device.site_slug,
      role: device.role?.name || device.device_role?.name || device.role,
      role_slug: device.role?.slug || device.device_role?.slug || device.role_slug,
      platform: device.platform?.name || device.platform,
      platform_slug: device.platform?.slug || device.platform_slug,
      device_type: device.device_type?.display || device.device_type || device._type || "device",
      _type: device._type || "device",
      cluster: device.cluster?.name || device.cluster,
      ping_status: (device.status?.value || device.status) === "active" ? "online" : "unknown",
      snmp_status: "unknown",
      network_range: null,
      _netbox: device,
    };
  };

  const fetchDevices = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      
      // Use cached endpoint for fast loading (single query to local DB)
      const queryParams = new URLSearchParams();
      if (params.site) queryParams.set("site", params.site);
      if (params.role) queryParams.set("role", params.role);
      if (params.search) queryParams.set("q", params.search);
      
      const url = `/integrations/v1/netbox/devices${queryParams.toString() ? `?${queryParams}` : ""}`;
      const response = await fetchApi(url);
      
      const allDevices = (response.data || []).map(transformDevice);
      
      setDevices(allDevices);
      setPagination({
        count: response.count || allDevices.length,
        next: null,
        previous: null,
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
      const response = await fetchApi(`/integrations/v1/netbox/devices/${deviceId}`);
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
        fetchApi("/integrations/v1/netbox/sites").catch(() => ({ data: [] })),
        fetchApi("/integrations/v1/netbox/device-roles").catch(() => ({ data: [] })),
        fetchApi("/integrations/v1/netbox/device-types").catch(() => ({ data: [] })),
        fetchApi("/integrations/v1/netbox/manufacturers").catch(() => ({ data: [] })),
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

/**
 * Hook to fetch tags from NetBox
 */
export function useNetBoxTags() {
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTags = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetchApi("/integrations/v1/netbox/tags");
      
      const transformedTags = (extractData(response) || []).map(tag => ({
        id: tag.id,
        name: tag.name,
        slug: tag.slug,
        color: tag.color,
        description: tag.description,
        _netbox: tag,
      }));
      
      setTags(transformedTags);
      setError(null);
    } catch (err) {
      setError(err.message);
      setTags([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  return { tags, loading, error, refetch: fetchTags };
}

/**
 * Hook to fetch IP ranges from NetBox IPAM
 */
export function useNetBoxIPRanges() {
  const [ranges, setRanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRanges = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetchApi("/integrations/v1/netbox/ip-ranges");
      
      // Handle both {data: [...]} and direct array formats
      const rangeData = response?.data || (Array.isArray(response) ? response : []);
      const transformedRanges = rangeData.map(range => {
        const startAddr = range.start_address?.includes('/') ? range.start_address.split("/")[0] : range.start_address;
        const endAddr = range.end_address?.includes('/') ? range.end_address.split("/")[0] : range.end_address;
        return {
          id: range.id,
          start_address: startAddr,
          end_address: endAddr,
          display: range.display || `${startAddr} - ${endAddr}`,
          description: range.description,
          status: range.status?.value,
          role: range.role?.name,
          vrf: range.vrf?.name,
          tenant: range.tenant?.name,
          _netbox: range,
        };
      });
      
      setRanges(transformedRanges);
      setError(null);
    } catch (err) {
      setError(err.message);
      setRanges([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRanges();
  }, [fetchRanges]);

  return { ranges, loading, error, refetch: fetchRanges };
}

/**
 * Hook to fetch IP prefixes from NetBox IPAM
 */
export function useNetBoxPrefixes() {
  const [prefixes, setPrefixes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPrefixes = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetchApi("/integrations/v1/netbox/prefixes");
      
      // Handle both {data: [...]} and direct array formats
      const prefixData = response?.data || (Array.isArray(response) ? response : []);
      const transformedPrefixes = prefixData.map(prefix => ({
        id: prefix.id,
        prefix: prefix.prefix,
        display: prefix.display,
        description: prefix.description,
        status: prefix.status?.value,
        role: prefix.role?.name,
        vrf: prefix.vrf?.name,
        site: prefix.site?.name,
        tenant: prefix.tenant?.name,
        is_pool: prefix.is_pool,
        _netbox: prefix,
      }));
      
      setPrefixes(transformedPrefixes);
      setError(null);
    } catch (err) {
      setError(err.message);
      setPrefixes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrefixes();
  }, [fetchPrefixes]);

  return { prefixes, loading, error, refetch: fetchPrefixes };
}

export default {
  useNetBoxStatus,
  useNetBoxDevices,
  useNetBoxDevice,
  useNetBoxLookups,
  useNetBoxTags,
  useNetBoxIPRanges,
  useNetBoxPrefixes,
};
