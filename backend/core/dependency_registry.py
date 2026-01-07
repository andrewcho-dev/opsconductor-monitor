"""
OpsConductor Dependency Registry

Manages device dependency relationships for alert correlation.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from utils.db import db_query, db_query_one, db_execute

from .models import Dependency, DependencyType, Alert, AlertStatus

logger = logging.getLogger(__name__)


class DependencyRegistry:
    """
    Device dependency management service.
    
    Manages the graph of device dependencies used for:
    - Alert correlation (suppress downstream alerts)
    - Root cause analysis
    - Impact assessment
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info("DependencyRegistry initialized")
    
    async def add_dependency(
        self,
        device_ip: str,
        depends_on_ip: str,
        dependency_type: DependencyType = DependencyType.NETWORK,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        auto_discovered: bool = False,
        confidence: Optional[float] = None
    ) -> Dependency:
        """
        Create a new dependency relationship.
        
        Args:
            device_ip: IP of the dependent device
            depends_on_ip: IP of the device it depends on
            dependency_type: Type of dependency
            description: Optional description
            created_by: User who created (if manual)
            auto_discovered: True if auto-discovered
            confidence: Confidence score for auto-discovered (0-1)
            
        Returns:
            Created Dependency
        """
        if device_ip == depends_on_ip:
            raise ValueError("Device cannot depend on itself")
        
        dep_id = uuid4()
        now = datetime.utcnow()
        
        try:
            db_execute("""
                INSERT INTO dependencies (
                    id, device_ip, depends_on_ip, dependency_type,
                    description, created_by, auto_discovered, confidence,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
            """, (
                str(dep_id), device_ip, depends_on_ip, dependency_type.value,
                description, created_by, auto_discovered, confidence,
                now, now
            ))
            
            logger.info(f"Created dependency: {device_ip} depends on {depends_on_ip}")
            
            return Dependency(
                id=dep_id,
                device_ip=device_ip,
                depends_on_ip=depends_on_ip,
                dependency_type=dependency_type,
                description=description,
                auto_discovered=auto_discovered,
                confidence=confidence,
                created_at=now,
                created_by=created_by,
                updated_at=now
            )
            
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                raise ValueError(f"Dependency already exists: {device_ip} -> {depends_on_ip}")
            raise
    
    async def remove_dependency(self, dependency_id: UUID) -> bool:
        """
        Remove a dependency.
        
        Returns:
            True if deleted, False if not found
        """
        result = db_execute(
            "DELETE FROM dependencies WHERE id = %s",
            (str(dependency_id),)
        )
        
        if result:
            logger.info(f"Deleted dependency {dependency_id}")
            return True
        return False
    
    async def get_dependency(self, dependency_id: UUID) -> Optional[Dependency]:
        """Get a dependency by ID."""
        row = db_query_one(
            "SELECT * FROM dependencies WHERE id = %s",
            (str(dependency_id),)
        )
        
        if row:
            return self._row_to_dependency(row)
        return None
    
    async def get_upstream(self, device_ip: str) -> List[Dependency]:
        """
        Get all devices that this device depends on (upstream).
        
        Args:
            device_ip: IP of the device
            
        Returns:
            List of dependencies (devices this one depends on)
        """
        rows = db_query("""
            SELECT d.*, dev.name as depends_on_name
            FROM dependencies d
            LEFT JOIN devices dev ON dev.ip_address = d.depends_on_ip
            WHERE d.device_ip = %s
        """, (device_ip,))
        
        return [self._row_to_dependency(row) for row in rows]
    
    async def get_downstream(self, device_ip: str) -> List[Dependency]:
        """
        Get all devices that depend on this device (downstream).
        
        Args:
            device_ip: IP of the device
            
        Returns:
            List of dependencies (devices depending on this one)
        """
        rows = db_query("""
            SELECT d.*, dev.name as device_name
            FROM dependencies d
            LEFT JOIN devices dev ON dev.ip_address = d.device_ip
            WHERE d.depends_on_ip = %s
        """, (device_ip,))
        
        return [self._row_to_dependency(row) for row in rows]
    
    async def get_all_upstream_recursive(
        self,
        device_ip: str,
        visited: Optional[set] = None
    ) -> List[str]:
        """
        Get all upstream devices recursively (full dependency chain).
        
        Args:
            device_ip: Starting device IP
            visited: Set of already visited IPs (for cycle detection)
            
        Returns:
            List of all upstream device IPs
        """
        if visited is None:
            visited = set()
        
        if device_ip in visited:
            return []  # Cycle detected
        
        visited.add(device_ip)
        upstream = []
        
        deps = await self.get_upstream(device_ip)
        for dep in deps:
            upstream.append(dep.depends_on_ip)
            # Recursively get upstream of upstream
            upstream.extend(
                await self.get_all_upstream_recursive(dep.depends_on_ip, visited)
            )
        
        return upstream
    
    async def find_upstream_alert(self, device_ip: str) -> Optional[Alert]:
        """
        Find active alert on any upstream device.
        
        Used for correlation - if an upstream device has an active alert,
        downstream alerts should be suppressed.
        
        Args:
            device_ip: Device IP to check
            
        Returns:
            Active Alert on upstream device, or None
        """
        upstream_ips = await self.get_all_upstream_recursive(device_ip)
        
        if not upstream_ips:
            return None
        
        # Check for active alerts on any upstream device
        placeholders = ",".join(["%s"] * len(upstream_ips))
        row = db_query_one(f"""
            SELECT * FROM alerts
            WHERE device_ip IN ({placeholders})
            AND status IN ('active', 'acknowledged')
            ORDER BY occurred_at DESC
            LIMIT 1
        """, tuple(upstream_ips))
        
        if row:
            from .alert_manager import get_alert_manager
            return get_alert_manager()._row_to_alert(row)
        
        return None
    
    async def get_dependencies(
        self,
        device_ip: Optional[str] = None,
        depends_on_ip: Optional[str] = None,
        dependency_type: Optional[DependencyType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dependency]:
        """
        Query dependencies with filters.
        """
        conditions = []
        params = []
        
        if device_ip:
            conditions.append("d.device_ip = %s")
            params.append(device_ip)
        
        if depends_on_ip:
            conditions.append("d.depends_on_ip = %s")
            params.append(depends_on_ip)
        
        if dependency_type:
            conditions.append("d.dependency_type = %s")
            params.append(dependency_type.value)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        params.extend([limit, offset])
        
        rows = db_query(f"""
            SELECT d.*,
                   dev1.name as device_name,
                   dev2.name as depends_on_name
            FROM dependencies d
            LEFT JOIN devices dev1 ON dev1.ip_address = d.device_ip
            LEFT JOIN devices dev2 ON dev2.ip_address = d.depends_on_ip
            WHERE {where_clause}
            ORDER BY d.created_at DESC
            LIMIT %s OFFSET %s
        """, tuple(params))
        
        return [self._row_to_dependency(row) for row in rows]
    
    async def get_dependency_count(self) -> int:
        """Get total number of dependencies."""
        row = db_query_one("SELECT COUNT(*) as count FROM dependencies")
        return row["count"] if row else 0
    
    async def bulk_add_dependencies(
        self,
        dependencies: List[Dict[str, Any]],
        created_by: Optional[str] = None
    ) -> int:
        """
        Add multiple dependencies at once.
        
        Args:
            dependencies: List of dicts with device_ip, depends_on_ip, type, description
            created_by: User creating the dependencies
            
        Returns:
            Number of dependencies created
        """
        created = 0
        
        for dep_data in dependencies:
            try:
                await self.add_dependency(
                    device_ip=dep_data["device_ip"],
                    depends_on_ip=dep_data["depends_on_ip"],
                    dependency_type=DependencyType(dep_data.get("dependency_type", "network")),
                    description=dep_data.get("description"),
                    created_by=created_by
                )
                created += 1
            except ValueError as e:
                logger.warning(f"Skipping dependency: {e}")
                continue
        
        logger.info(f"Bulk created {created} dependencies")
        return created
    
    async def get_device_summary(self, device_ip: str) -> Dict[str, Any]:
        """
        Get dependency summary for a device.
        
        Returns:
            Dict with upstream, downstream counts and lists
        """
        upstream = await self.get_upstream(device_ip)
        downstream = await self.get_downstream(device_ip)
        
        return {
            "device_ip": device_ip,
            "upstream_count": len(upstream),
            "downstream_count": len(downstream),
            "upstream": [
                {
                    "ip": d.depends_on_ip,
                    "name": d.depends_on_name,
                    "type": d.dependency_type.value
                }
                for d in upstream
            ],
            "downstream": [
                {
                    "ip": d.device_ip,
                    "name": d.device_name,
                    "type": d.dependency_type.value
                }
                for d in downstream
            ]
        }
    
    def _row_to_dependency(self, row: Dict) -> Dependency:
        """Convert database row to Dependency object."""
        return Dependency(
            id=UUID(row["id"]) if isinstance(row["id"], str) else row["id"],
            device_ip=row["device_ip"],
            depends_on_ip=row["depends_on_ip"],
            dependency_type=DependencyType(row["dependency_type"]),
            description=row.get("description"),
            auto_discovered=row.get("auto_discovered", False),
            confidence=row.get("confidence"),
            created_at=row.get("created_at"),
            created_by=row.get("created_by"),
            updated_at=row.get("updated_at"),
            device_name=row.get("device_name"),
            depends_on_name=row.get("depends_on_name"),
        )


# Global instance
_dependency_registry: DependencyRegistry = None


def get_dependency_registry() -> DependencyRegistry:
    """Get the global DependencyRegistry instance."""
    global _dependency_registry
    if _dependency_registry is None:
        _dependency_registry = DependencyRegistry()
    return _dependency_registry
