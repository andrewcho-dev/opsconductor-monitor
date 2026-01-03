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

  const transformDevice = (device) => ({
    id: device.id,
    ip_address: device.primary_ip4?.address?.split("/")[0] || device.name,
    ip_with_prefix: device.primary_ip4?.address,
    hostname: device.name,
    name: device.name,
    description: device.description || device.device_type?.display,
    vendor: device.device_type?.manufacturer?.name,
    model: device.device_type?.model,
    serial: device.serial,
    status: device.status?.value || "active",
    status_label: device.status?.label || "Active",
    site: device.site?.name,
    site_slug: device.site?.slug,
    role: device.role?.name || device.device_role?.name,
    role_slug: device.role?.slug || device.device_role?.slug,
    platform: device.platform?.name,
    platform_slug: device.platform?.slug,
    device_type: device._type || "device",
    _type: device._type || "device",
    cluster: device.cluster?.name,
    ping_status: device.status?.value === "active" ? "online" : "unknown",
    snmp_status: "unknown",
    network_range: null,
    _netbox: device,
  });

  const fetchDevices = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      
      // Fetch ALL devices by paginating through results
      let allDevices = [];
      let offset = 0;
      const limit = 100; // Fetch 100 at a time
      let totalCount = 0;
      
      while (true) {
        const queryParams = new URLSearchParams();
        if (params.site) queryParams.set("site", params.site);
        if (params.role) queryParams.set("role", params.role);
        if (params.status) queryParams.set("status", params.status);
        if (params.search) queryParams.set("q", params.search);
        queryParams.set("limit", limit);
        queryParams.set("offset", offset);
        
        const url = `/api/netbox/devices?${queryParams}`;
        const response = await fetchApi(url);
        
        const pageDevices = (response.data || []).map(transformDevice);
        allDevices = [...allDevices, ...pageDevices];
        totalCount = response.count || allDevices.length;
        
        // Check if we have more pages
        if (!response.next || pageDevices.length < limit) {
          break;
        }
        
        offset += limit;
      }
      
      setDevices(allDevices);
      setPagination({
        count: totalCount,
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
      const response = await fetchApi("/api/netbox/tags");
      
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
      const response = await fetchApi("/api/netbox/ip-ranges");
      
      const transformedRanges = (response.data || []).map(range => ({
        id: range.id,
        start_address: range.start_address?.split("/")[0],
        end_address: range.end_address?.split("/")[0],
        display: range.display,
        description: range.description,
        status: range.status?.value,
        role: range.role?.name,
        vrf: range.vrf?.name,
        tenant: range.tenant?.name,
        _netbox: range,
      }));
      
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
      const response = await fetchApi("/api/netbox/prefixes");
      
      const transformedPrefixes = (response.data || []).map(prefix => ({
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
