#!/usr/bin/env python3
"""
Database utility module for PostgreSQL connection
"""
import psycopg2
import psycopg2.extras
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.host = os.getenv('PG_HOST', 'localhost')
        self.port = os.getenv('PG_PORT', '5432')
        self.database = os.getenv('PG_DATABASE', 'network_scan')
        self.user = os.getenv('PG_USER', 'postgres')
        self.password = os.getenv('PG_PASSWORD', 'postgres')
        self.conn = None
        self.cur = None
    
    def get_connection(self):
        """Get a fresh PostgreSQL database connection"""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password
        )
    
    def execute_query(self, query, params=None, fetch=True):
        """Execute a query with error handling"""
        conn = None
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query, params or ())
            if fetch:
                result = cur.fetchall()
                conn.commit()  # Commit even when fetching (for INSERT with RETURNING)
                conn.close()
                return result
            else:
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"Database error: {e}")
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except:
                    pass
            if fetch:
                return []
            else:
                return None
    
    def create_tables(self):
        """Create the scan_results table and interface_scans table"""
        create_scan_results_table = """
        CREATE TABLE IF NOT EXISTS scan_results (
            id SERIAL PRIMARY KEY,
            ip_address INET NOT NULL UNIQUE,
            network_range VARCHAR(50),
            ping_status VARCHAR(20),
            snmp_status VARCHAR(20),
            ssh_status VARCHAR(20),
            rdp_status VARCHAR(20),
            scan_timestamp TIMESTAMP,
            snmp_description TEXT,
            snmp_hostname TEXT,
            snmp_location TEXT,
            snmp_contact TEXT,
            snmp_uptime TEXT,
            snmp_vendor_oid TEXT,
            snmp_vendor_name TEXT,
            snmp_model TEXT,
            snmp_chassis_mac TEXT,
            snmp_serial TEXT
        )
        """
        
        create_interface_scans_table = """
        CREATE TABLE IF NOT EXISTS interface_scans (
            id SERIAL PRIMARY KEY,
            ip_address INET NOT NULL,
            scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interface_index INTEGER NOT NULL,
            interface_name VARCHAR(100),
            interface_type INTEGER,
            interface_type_name VARCHAR(50),
            interface_speed BIGINT,
            interface_status INTEGER,
            physical_address VARCHAR(20),
            rx_bytes BIGINT,
            tx_bytes BIGINT
        )
        """
        
        create_ssh_cli_scans_table = """
        CREATE TABLE IF NOT EXISTS ssh_cli_scans (
            id SERIAL PRIMARY KEY,
            ip_address INET NOT NULL,
            scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interface_index INTEGER NOT NULL,
            interface_name VARCHAR(100),
            cli_port INTEGER,
            is_optical BOOLEAN,
            medium VARCHAR(100),
            connector VARCHAR(50),
            speed VARCHAR(20),
            tx_power VARCHAR(20),
            rx_power VARCHAR(20),
            temperature VARCHAR(20),
            status VARCHAR(20),
            raw_output TEXT,
            lldp_remote_port VARCHAR(50),
            lldp_remote_mgmt_addr VARCHAR(50),
            lldp_remote_chassis_id VARCHAR(64),
            lldp_remote_system_name TEXT,
            lldp_raw_info TEXT,
            UNIQUE(ip_address, interface_index)
        )
        """
        
        create_optical_power_history_table = """
        CREATE TABLE IF NOT EXISTS optical_power_history (
            id SERIAL PRIMARY KEY,
            ip_address INET NOT NULL,
            interface_index INTEGER NOT NULL,
            interface_name VARCHAR(100),
            cli_port INTEGER,
            measurement_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tx_power DECIMAL(8,2),
            rx_power DECIMAL(8,2),
            tx_power_unit VARCHAR(10) DEFAULT 'dBm',
            rx_power_unit VARCHAR(10) DEFAULT 'dBm',
            temperature DECIMAL(8,2),
            temperature_unit VARCHAR(10) DEFAULT 'C'
        )
        """
        
        # Create indexes for performance
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_scan_results_ip ON scan_results(ip_address)",
            "CREATE INDEX IF NOT EXISTS idx_scan_results_timestamp ON scan_results(scan_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_interface_scans_ip_time ON interface_scans(ip_address, scan_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_interface_scans_interface ON interface_scans(interface_index, scan_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_ssh_cli_scans_ip_time ON ssh_cli_scans(ip_address, scan_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_ssh_cli_scans_interface ON ssh_cli_scans(interface_index, scan_timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_optical_power_ip_interface ON optical_power_history(ip_address, interface_index)",
            "CREATE INDEX IF NOT EXISTS idx_optical_power_measurement_time ON optical_power_history(measurement_timestamp)"
        ]
        
        # Add temperature column to existing ssh_cli_scans table if it doesn't exist
        add_temperature_column = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'ssh_cli_scans' AND column_name = 'temperature'
            ) THEN
                ALTER TABLE ssh_cli_scans ADD COLUMN temperature VARCHAR(20);
            END IF;
        END $$;
        """
        
        # Create poller configurations table
        create_poller_configs_table = """
        CREATE TABLE IF NOT EXISTS poller_configs (
            id SERIAL PRIMARY KEY,
            poller_type VARCHAR(50) NOT NULL UNIQUE,
            enabled BOOLEAN DEFAULT false,
            interval_seconds INTEGER DEFAULT 3600,
            config_data TEXT
        )
        """
        
        # Create device groups table
        create_device_groups_table = """
        CREATE TABLE IF NOT EXISTS device_groups (
            id SERIAL PRIMARY KEY,
            group_name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
        
        # Create group devices table
        create_group_devices_table = """
        CREATE TABLE IF NOT EXISTS group_devices (
            id SERIAL PRIMARY KEY,
            group_id INTEGER REFERENCES device_groups(id) ON DELETE CASCADE,
            ip_address VARCHAR(45) NOT NULL,
            added_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(group_id, ip_address)
        )
        """
        
        # Create poller status table
        create_poller_status_table = """
        CREATE TABLE IF NOT EXISTS poller_status (
            id SERIAL PRIMARY KEY,
            poller_type VARCHAR(50) NOT NULL UNIQUE,
            running BOOLEAN DEFAULT false,
            last_run TIMESTAMP,
            next_run TIMESTAMP,
            total_runs INTEGER DEFAULT 0,
            successful_runs INTEGER DEFAULT 0,
            failed_runs INTEGER DEFAULT 0,
            last_error TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Create poller logs table
        create_poller_logs_table = """
        CREATE TABLE IF NOT EXISTS poller_logs (
            id SERIAL PRIMARY KEY,
            poller_type VARCHAR(50) NOT NULL,
            level VARCHAR(20) NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details JSONB
        )
        """

        # Generic scheduler jobs table for Celery-based scheduling
        create_scheduler_jobs_table = """
        CREATE TABLE IF NOT EXISTS scheduler_jobs (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            task_name VARCHAR(200) NOT NULL,
            config JSONB,
            enabled BOOLEAN DEFAULT FALSE,
            -- "interval" (every N seconds) or "cron" (cron_expression)
            schedule_type VARCHAR(20) DEFAULT 'interval',
            interval_seconds INTEGER,
            cron_expression VARCHAR(200),
            start_at TIMESTAMP,
            end_at TIMESTAMP,
            max_runs INTEGER,
            run_count INTEGER DEFAULT 0,
            last_run_at TIMESTAMP,
            next_run_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Execution history for scheduler jobs
        create_scheduler_job_executions_table = """
        CREATE TABLE IF NOT EXISTS scheduler_job_executions (
            id SERIAL PRIMARY KEY,
            job_name VARCHAR(100) NOT NULL,
            task_name VARCHAR(200) NOT NULL,
            task_id VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            error_message TEXT,
            result JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        self.execute_query(create_scan_results_table, fetch=False)
        self.execute_query(create_interface_scans_table, fetch=False)
        self.execute_query(create_ssh_cli_scans_table, fetch=False)
        self.execute_query(create_optical_power_history_table, fetch=False)
        self.execute_query(add_temperature_column, fetch=False)
        self.execute_query(create_poller_configs_table, fetch=False)
        self.execute_query(create_device_groups_table, fetch=False)
        self.execute_query(create_group_devices_table, fetch=False)
        self.execute_query(create_poller_status_table, fetch=False)
        self.execute_query(create_poller_logs_table, fetch=False)
        self.execute_query(create_scheduler_jobs_table, fetch=False)
        self.execute_query(create_scheduler_job_executions_table, fetch=False)

        # Ensure new scheduler_jobs columns exist on older databases
        try:
            self.execute_query("ALTER TABLE scheduler_jobs ADD COLUMN schedule_type VARCHAR(20) DEFAULT 'interval'", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE scheduler_jobs ADD COLUMN cron_expression VARCHAR(200)", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE scheduler_jobs ADD COLUMN start_at TIMESTAMP", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE scheduler_jobs ADD COLUMN end_at TIMESTAMP", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE scheduler_jobs ADD COLUMN max_runs INTEGER", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE scheduler_jobs ADD COLUMN run_count INTEGER DEFAULT 0", fetch=False)
        except:
            pass
        
        # Add RDP column if it doesn't exist
        try:
            self.execute_query("ALTER TABLE scan_results ADD COLUMN rdp_status VARCHAR(20)", fetch=False)
        except:
            pass  # Column already exists
        
        # Add network_range column if it doesn't exist
        try:
            self.execute_query("ALTER TABLE scan_results ADD COLUMN network_range VARCHAR(50)", fetch=False)
        except:
            pass  # Column already exists
        
        try:
            self.execute_query("ALTER TABLE scan_results ADD COLUMN snmp_vendor_name TEXT", fetch=False)
        except:
            pass
        
        try:
            self.execute_query("ALTER TABLE scan_results ADD COLUMN snmp_model TEXT", fetch=False)
        except:
            pass
        
        try:
            self.execute_query("ALTER TABLE scan_results ADD COLUMN snmp_chassis_mac TEXT", fetch=False)
        except:
            pass
        
        try:
            self.execute_query("ALTER TABLE scan_results ADD COLUMN snmp_serial TEXT", fetch=False)
        except:
            pass

        # Ensure ip_address is stored as INET for proper numeric ordering.
        # Older databases may have ip_address as VARCHAR.
        try:
            self.execute_query(
                "ALTER TABLE scan_results "
                "ALTER COLUMN ip_address TYPE inet USING ip_address::inet",
                fetch=False,
            )
        except:
            pass

        # Ensure LLDP columns exist on ssh_cli_scans for neighbor info
        try:
            self.execute_query("ALTER TABLE ssh_cli_scans ADD COLUMN lldp_remote_port VARCHAR(50)", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE ssh_cli_scans ADD COLUMN lldp_remote_mgmt_addr VARCHAR(50)", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE ssh_cli_scans ADD COLUMN lldp_remote_chassis_id VARCHAR(64)", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE ssh_cli_scans ADD COLUMN lldp_remote_system_name TEXT", fetch=False)
        except:
            pass
        try:
            self.execute_query("ALTER TABLE ssh_cli_scans ADD COLUMN lldp_raw_info TEXT", fetch=False)
        except:
            pass

        # Ensure a unique constraint exists for (ip_address, interface_index)
        # Older databases may have been created without it.
        try:
            self.execute_query(
                "ALTER TABLE ssh_cli_scans ADD CONSTRAINT ssh_cli_scans_ip_iface_uniq "
                "UNIQUE (ip_address, interface_index)",
                fetch=False,
            )
        except:
            pass
        
        for index_query in create_indexes:
            self.execute_query(index_query, fetch=False)

    def upsert_scheduler_job(self, name, task_name, config, interval_seconds=None,
                             enabled=True, next_run_at=None, schedule_type='interval',
                             cron_expression=None, start_at=None, end_at=None,
                             max_runs=None):
        """Create or update a scheduler job by name.

        Returns the row (as a DictRow) for convenience.
        """
        query = """
            INSERT INTO scheduler_jobs (
                name, task_name, config, enabled,
                schedule_type, interval_seconds, cron_expression,
                start_at, end_at, max_runs,
                last_run_at, next_run_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)
            ON CONFLICT (name)
            DO UPDATE SET
                task_name = EXCLUDED.task_name,
                config = EXCLUDED.config,
                enabled = EXCLUDED.enabled,
                schedule_type = EXCLUDED.schedule_type,
                interval_seconds = EXCLUDED.interval_seconds,
                cron_expression = EXCLUDED.cron_expression,
                start_at = EXCLUDED.start_at,
                end_at = EXCLUDED.end_at,
                max_runs = EXCLUDED.max_runs,
                next_run_at = EXCLUDED.next_run_at,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """

        params = (
            name,
            task_name,
            json.dumps(config) if config is not None else None,
            enabled,
            schedule_type,
            interval_seconds,
            cron_expression,
            start_at,
            end_at,
            max_runs,
            next_run_at,
        )
        rows = self.execute_query(query, params)
        return rows[0] if rows else None

    def get_scheduler_jobs(self, enabled=None):
        """Return all scheduler jobs, optionally filtered by enabled flag."""
        query = "SELECT * FROM scheduler_jobs"
        params = []
        if enabled is not None:
            query += " WHERE enabled = %s"
            params.append(enabled)
        query += " ORDER BY name"

        rows = self.execute_query(query, tuple(params))
        # Parse JSON config if stored as text
        for row in rows:
            cfg = row.get("config")
            if isinstance(cfg, str):
                try:
                    row["config"] = json.loads(cfg)
                except Exception:
                    row["config"] = None
        return rows

    def get_scheduler_job_by_name(self, name):
        """Return a single scheduler job by name, or None if not found."""
        query = "SELECT * FROM scheduler_jobs WHERE name = %s"
        rows = self.execute_query(query, (name,))
        if not rows:
            return None
        row = rows[0]
        cfg = row.get("config")
        if isinstance(cfg, str):
            try:
                row["config"] = json.loads(cfg)
            except Exception:
                row["config"] = None
        return row

    def get_due_scheduler_jobs(self, now):
        """Return enabled scheduler jobs whose next_run_at is due (<= now or NULL)."""
        query = """\
            SELECT * FROM scheduler_jobs
            WHERE enabled = TRUE
              AND (start_at IS NULL OR start_at <= %s)
              AND (end_at IS NULL OR end_at >= %s)
              AND (max_runs IS NULL OR COALESCE(run_count, 0) < max_runs)
              AND (next_run_at IS NULL OR next_run_at <= %s)
            ORDER BY next_run_at NULLS FIRST
        """
        rows = self.execute_query(query, (now, now, now))
        for row in rows:
            cfg = row.get("config")
            if isinstance(cfg, str):
                try:
                    row["config"] = json.loads(cfg)
                except Exception:
                    row["config"] = None
        return rows

    def mark_scheduler_job_run(self, name, last_run_at, next_run_at):
        """Update last/next run timestamps for a scheduler job."""
        query = """\
            UPDATE scheduler_jobs
            SET last_run_at = %s,
                next_run_at = %s,
                run_count = COALESCE(run_count, 0) + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE name = %s
        """
        return self.execute_query(query, (last_run_at, next_run_at, name), fetch=False)
    
    def create_scheduler_job_execution(self, job_name, task_name, task_id, status,
                                       started_at=None, error_message=None, result=None):
        """Insert a new scheduler job execution record."""
        query = """
            INSERT INTO scheduler_job_executions
                (job_name, task_name, task_id, status, started_at, error_message, result)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        payload = json.dumps(result) if result is not None else None
        return self.execute_query(
            query,
            (job_name, task_name, task_id, status, started_at, error_message, payload),
            fetch=False,
        )

    def update_scheduler_job_execution(self, task_id, status,
                                       finished_at=None, error_message=None, result=None):
        """Update status and optional fields for an existing execution by task_id."""
        query = """
            UPDATE scheduler_job_executions
            SET status = %s,
                finished_at = COALESCE(%s, finished_at),
                error_message = COALESCE(%s, error_message),
                result = COALESCE(%s, result)
            WHERE task_id = %s
        """
        payload = json.dumps(result) if result is not None else None
        return self.execute_query(
            query,
            (status, finished_at, error_message, payload, task_id),
            fetch=False,
        )

    def get_scheduler_job_executions(self, job_name=None, limit=100):
        """Return recent scheduler job executions, optionally filtered by job_name."""
        query = "SELECT * FROM scheduler_job_executions"
        params = []
        if job_name:
            query += " WHERE job_name = %s"
            params.append(job_name)
        query += " ORDER BY started_at DESC LIMIT %s"
        params.append(limit)

        rows = self.execute_query(query, tuple(params))
        # Parse result JSON if stored as text
        for row in rows:
            res = row.get("result")
            if isinstance(res, str):
                try:
                    row["result"] = json.loads(res)
                except Exception:
                    row["result"] = None
        return rows

    def clear_scheduler_job_executions(self, job_name=None, status=None):
        """Delete scheduler job executions, optionally filtered by job_name and status."""
        query = "DELETE FROM scheduler_job_executions"
        clauses = []
        params = []
        if job_name:
            clauses.append("job_name = %s")
            params.append(job_name)
        if status:
            clauses.append("status = %s")
            params.append(status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        return self.execute_query(query, tuple(params), fetch=False)
    
    def mark_stale_scheduler_executions(self, timeout_seconds=600):
        """Mark queued/running executions older than timeout_seconds as 'timeout'.

        Returns the rows that were updated for visibility/metrics.
        """
        query = """
            UPDATE scheduler_job_executions
            SET status = 'timeout',
                finished_at = COALESCE(finished_at, NOW()),
                error_message = COALESCE(error_message, 'Timed out without completion')
            WHERE status IN ('queued', 'running')
              AND started_at < NOW() - (%s * INTERVAL '1 second')
            RETURNING id, job_name, task_id
        """
        return self.execute_query(query, (timeout_seconds,))
    
    def get_scan_results(self):
        """Get all scan results (raw rows)"""
        query = 'SELECT ip_address, network_range, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status, snmp_hostname, snmp_description, snmp_contact, snmp_location, snmp_uptime, snmp_vendor_oid FROM scan_results ORDER BY network_range, ip_address::inet'
        return self.execute_query(query)
    
    def get_all_devices(self):
        """Get all devices as list of dicts for JSON response"""
        query = '''
            SELECT ip_address, network_range, ping_status, scan_timestamp, 
                   snmp_status, snmp_hostname, snmp_description, snmp_contact, 
                   snmp_location, snmp_uptime, snmp_vendor_oid, ssh_status, rdp_status,
                   snmp_vendor_name, snmp_model, snmp_chassis_mac, snmp_serial
            FROM scan_results 
            ORDER BY ip_address::inet
        '''
        rows = self.execute_query(query)
        devices = []
        for row in rows:
            if len(row) >= 17:
                devices.append({
                    'ip_address': str(row[0]) if row[0] else '',
                    'network_range': row[1] or '',
                    'ping_status': row[2] or 'offline',
                    'scan_timestamp': row[3].isoformat() if row[3] else '',
                    'snmp_status': row[4] or 'UNKNOWN',
                    'snmp_hostname': row[5] or '',
                    'snmp_description': row[6] or '',
                    'snmp_contact': row[7] or '',
                    'snmp_location': row[8] or '',
                    'snmp_uptime': row[9] or '',
                    'snmp_vendor_oid': row[10] or '',
                    'ssh_status': row[11] or 'NO',
                    'rdp_status': row[12] or 'NO',
                    'snmp_vendor_name': row[13] or '',
                    'snmp_model': row[14] or '',
                    'snmp_chassis_mac': row[15] or '',
                    'snmp_serial': row[16] or ''
                })
        print(f"DEBUG: Retrieved {len(devices)} devices from database")
        return devices
    
    def delete_device(self, ip_address):
        """Delete a device by IP address. Returns True if deleted, False if not found."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM scan_results WHERE ip_address = %s', (ip_address,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def insert_scan_result(self, ip_address, ping_status, scan_timestamp, network_range=None, snmp_status=None, ssh_status=None, rdp_status=None):
        """Insert a new scan result (DEPRECATED - use upsert_scan_result instead)"""
        if snmp_status or ssh_status or rdp_status:
            query = """
            INSERT INTO scan_results (ip_address, network_range, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ip_address) DO UPDATE SET
                network_range = COALESCE(EXCLUDED.network_range, scan_results.network_range),
                ping_status = EXCLUDED.ping_status,
                scan_timestamp = COALESCE(EXCLUDED.scan_timestamp, scan_results.scan_timestamp),
                snmp_status = EXCLUDED.snmp_status,
                ssh_status = EXCLUDED.ssh_status,
                rdp_status = EXCLUDED.rdp_status
            """
            return self.execute_query(query, (ip_address, network_range, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status), fetch=False)
        else:
            query = """
            INSERT INTO scan_results (ip_address, network_range, ping_status, scan_timestamp)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (ip_address) DO UPDATE SET
                network_range = COALESCE(EXCLUDED.network_range, scan_results.network_range),
                ping_status = EXCLUDED.ping_status,
                scan_timestamp = COALESCE(EXCLUDED.scan_timestamp, scan_results.scan_timestamp)
            """
            return self.execute_query(query, (ip_address, network_range, ping_status, scan_timestamp), fetch=False)
    
    def upsert_scan_result(self, ip_address, ping_status, scan_timestamp, network_range=None, 
                          snmp_status=None, ssh_status=None, rdp_status=None, snmp_hostname=None):
        """Insert or update a scan result - uses UPSERT to prevent duplicates"""
        query = """
        INSERT INTO scan_results 
            (ip_address, network_range, ping_status, scan_timestamp, snmp_status, ssh_status, rdp_status, snmp_hostname)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ip_address) DO UPDATE SET
            network_range = COALESCE(EXCLUDED.network_range, scan_results.network_range),
            ping_status = EXCLUDED.ping_status,
            scan_timestamp = COALESCE(EXCLUDED.scan_timestamp, scan_results.scan_timestamp),
            snmp_status = COALESCE(EXCLUDED.snmp_status, scan_results.snmp_status),
            ssh_status = COALESCE(EXCLUDED.ssh_status, scan_results.ssh_status),
            rdp_status = COALESCE(EXCLUDED.rdp_status, scan_results.rdp_status),
            snmp_hostname = COALESCE(EXCLUDED.snmp_hostname, scan_results.snmp_hostname)
        """
        return self.execute_query(query, (ip_address, network_range, ping_status, scan_timestamp, 
                                         snmp_status, ssh_status, rdp_status, snmp_hostname), fetch=False)
    
    def insert_interface_scan(self, ip_address, interface_index, interface_name, interface_type, 
                             interface_type_name, interface_speed, interface_status, physical_address,
                             rx_bytes, tx_bytes):
        """Insert a new interface scan result"""
        query = """
        INSERT INTO interface_scans (ip_address, interface_index, interface_name, interface_type,
                                   interface_type_name, interface_speed, interface_status, physical_address,
                                   rx_bytes, tx_bytes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (ip_address, interface_index, interface_name, interface_type,
                                        interface_type_name, interface_speed, interface_status, 
                                        physical_address, rx_bytes, tx_bytes), fetch=False)
    
    def get_interface_scans(self, ip_address=None, limit=100):
        """Get interface scan results, optionally filtered by IP"""
        if ip_address:
            query = """
            SELECT * FROM interface_scans 
            WHERE ip_address = %s 
            ORDER BY scan_timestamp DESC, interface_index 
            LIMIT %s
            """
            return self.execute_query(query, (ip_address, limit))
        else:
            query = """
            SELECT * FROM interface_scans 
            ORDER BY scan_timestamp DESC, interface_index 
            LIMIT %s
            """
            return self.execute_query(query, (limit,))
    
    def get_interface_history(self, ip_address, interface_index, hours=24):
        """Get historical data for a specific interface"""
        query = """
        SELECT * FROM interface_scans 
        WHERE ip_address = %s AND interface_index = %s 
        AND scan_timestamp >= NOW() - INTERVAL '%s hours'
        ORDER BY scan_timestamp DESC
        """
        return self.execute_query(query, (ip_address, interface_index, hours))
    
    def insert_ssh_cli_scan(self, ip_address, interface_index, interface_name, cli_port,
                           is_optical, medium, connector, speed, tx_power, rx_power, temperature, status, raw_output,
                           lldp_remote_port=None, lldp_remote_mgmt_addr=None,
                           lldp_remote_chassis_id=None, lldp_remote_system_name=None,
                           lldp_raw_info=None):
        """Insert or update SSH/CLI scan result"""
        query = """
        INSERT INTO ssh_cli_scans (ip_address, interface_index, interface_name, cli_port,
                                  is_optical, medium, connector, speed, tx_power, rx_power, temperature,
                                  status, raw_output,
                                  lldp_remote_port, lldp_remote_mgmt_addr,
                                  lldp_remote_chassis_id, lldp_remote_system_name,
                                  lldp_raw_info)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ip_address, interface_index) 
        DO UPDATE SET 
            interface_name = EXCLUDED.interface_name,
            cli_port = EXCLUDED.cli_port,
            is_optical = EXCLUDED.is_optical,
            medium = EXCLUDED.medium,
            connector = EXCLUDED.connector,
            speed = EXCLUDED.speed,
            tx_power = EXCLUDED.tx_power,
            rx_power = EXCLUDED.rx_power,
            temperature = EXCLUDED.temperature,
            status = EXCLUDED.status,
            raw_output = EXCLUDED.raw_output,
            lldp_remote_port = EXCLUDED.lldp_remote_port,
            lldp_remote_mgmt_addr = EXCLUDED.lldp_remote_mgmt_addr,
            lldp_remote_chassis_id = EXCLUDED.lldp_remote_chassis_id,
            lldp_remote_system_name = EXCLUDED.lldp_remote_system_name,
            lldp_raw_info = EXCLUDED.lldp_raw_info,
            scan_timestamp = CURRENT_TIMESTAMP
        """
        return self.execute_query(query, (ip_address, interface_index, interface_name, cli_port,
                                        is_optical, medium, connector, speed, tx_power, rx_power, temperature,
                                        status, raw_output,
                                        lldp_remote_port, lldp_remote_mgmt_addr,
                                        lldp_remote_chassis_id, lldp_remote_system_name,
                                        lldp_raw_info), fetch=False)
    
    def get_ssh_cli_scans(self, ip_address=None, limit=100):
        """Get SSH/CLI scan results, optionally filtered by IP"""
        if ip_address:
            query = """
            SELECT * FROM ssh_cli_scans 
            WHERE ip_address = %s 
            ORDER BY scan_timestamp DESC, interface_index 
            LIMIT %s
            """
            return self.execute_query(query, (ip_address, limit))
        else:
            query = """
            SELECT * FROM ssh_cli_scans 
            ORDER BY scan_timestamp DESC, interface_index 
            LIMIT %s
            """
            return self.execute_query(query, (limit,))
    
    def insert_optical_power_history(self, ip_address, interface_index, interface_name, cli_port,
                                     tx_power=None, rx_power=None, temperature=None):
        """Insert optical power reading with timestamp"""
        query = """
        INSERT INTO optical_power_history (ip_address, interface_index, interface_name, cli_port,
                                          tx_power, rx_power, temperature)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (ip_address, interface_index, interface_name, cli_port,
                                          tx_power, rx_power, temperature), fetch=False)
    
    def get_optical_power_history(self, ip_address, interface_index=None, hours=24):
        """Get optical power history for a device/interface"""
        query = """
            SELECT ip_address, interface_index, interface_name, cli_port,
                   tx_power, rx_power, temperature, temperature_unit,
                   measurement_timestamp
            FROM optical_power_history 
            WHERE ip_address = %s 
            AND measurement_timestamp >= NOW() - INTERVAL '%s hours'
        """
        params = [ip_address, hours]
        
        if interface_index:
            query += " AND interface_index = %s"
            params.append(interface_index)
            
        query += " ORDER BY measurement_timestamp DESC"
        
        return self.execute_query(query, tuple(params))

    # Poller management methods
    def get_poller_config(self, poller_type):
        """Get configuration for a specific poller"""
        query = "SELECT * FROM poller_configs WHERE poller_type = %s"
        result = self.execute_query(query, (poller_type,))
        return result[0] if result else None

    def set_poller_config(self, poller_type, enabled, interval_seconds, config_data):
        """Set configuration for a specific poller"""
        query = """
            INSERT INTO poller_configs (poller_type, enabled, interval_seconds, config_data, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (poller_type) 
            DO UPDATE SET 
                enabled = EXCLUDED.enabled,
                interval_seconds = EXCLUDED.interval_seconds,
                config_data = EXCLUDED.config_data,
                updated_at = CURRENT_TIMESTAMP
        """
        return self.execute_query(query, (poller_type, enabled, interval_seconds, json.dumps(config_data)), fetch=False)

    def get_all_poller_configs(self):
        """Get all poller configurations"""
        query = "SELECT * FROM poller_configs ORDER BY poller_type"
        return self.execute_query(query)

    def get_poller_status(self, poller_type):
        """Get status for a specific poller"""
        query = """
            SELECT id, poller_type, running, last_run, next_run, 
                   total_runs, successful_runs, failed_runs, last_error, updated_at
            FROM poller_status 
            WHERE poller_type = %s
        """
        result = self.execute_query(query, (poller_type,))
        return result[0] if result else None

    def set_poller_status(self, poller_type, running, last_run=None, next_run=None, 
                         total_runs=None, successful_runs=None, failed_runs=None, last_error=None):
        """Set status for a specific poller"""
        query = """
            INSERT INTO poller_status (poller_type, running, last_run, next_run, 
                                     total_runs, successful_runs, failed_runs, last_error, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (poller_type) 
            DO UPDATE SET 
                running = EXCLUDED.running,
                last_run = COALESCE(EXCLUDED.last_run, poller_status.last_run),
                next_run = COALESCE(EXCLUDED.next_run, poller_status.next_run),
                total_runs = COALESCE(EXCLUDED.total_runs, poller_status.total_runs),
                successful_runs = COALESCE(EXCLUDED.successful_runs, poller_status.successful_runs),
                failed_runs = COALESCE(EXCLUDED.failed_runs, poller_status.failed_runs),
                last_error = COALESCE(EXCLUDED.last_error, poller_status.last_error),
                updated_at = CURRENT_TIMESTAMP
        """
        return self.execute_query(query, (poller_type, running, last_run, next_run, 
                                        total_runs, successful_runs, failed_runs, last_error), fetch=False)

    def get_all_poller_status(self):
        """Get status for all pollers"""
        query = "SELECT * FROM poller_status ORDER BY poller_type"
        return self.execute_query(query)

    def add_poller_log(self, poller_type, level, message, details=None):
        """Add a log entry for a poller"""
        query = """
            INSERT INTO poller_logs (poller_type, level, message, details)
            VALUES (%s, %s, %s, %s)
        """
        return self.execute_query(query, (poller_type, level, message, json.dumps(details) if details else None), fetch=False)

    def get_poller_logs(self, poller_type=None, limit=100):
        """Get recent poller logs"""
        query = "SELECT * FROM poller_logs"
        params = []
        
        if poller_type:
            query += " WHERE poller_type = %s"
            params.append(poller_type)
            
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(query, tuple(params))

    def clear_poller_logs(self, poller_type=None):
        """Clear poller logs"""
        if poller_type:
            query = "DELETE FROM poller_logs WHERE poller_type = %s"
            return self.execute_query(query, (poller_type,), fetch=False)
        else:
            query = "DELETE FROM poller_logs"
            return self.execute_query(query, fetch=False)

    def get_poller_stats(self):
        """Get overall poller statistics"""
        query = """
            SELECT 
                COUNT(*) as total_logs_today,
                MAX(timestamp) as last_log
            FROM poller_logs 
            WHERE timestamp >= CURRENT_DATE
        """
        result = self.execute_query(query)
        return result[0] if result else {'total_logs_today': 0, 'last_log': None}
    
    def get_optical_power_trends(self, ip_address, interface_index, days=7):
        """Get aggregated power trends for a specific interface over days"""
        query = """
        SELECT 
            DATE_TRUNC('hour', measurement_timestamp) as hour_bucket,
            AVG(tx_power) as avg_tx_power,
            MIN(tx_power) as min_tx_power,
            MAX(tx_power) as max_tx_power,
            AVG(rx_power) as avg_rx_power,
            MIN(rx_power) as min_rx_power,
            MAX(rx_power) as max_rx_power,
            COUNT(*) as sample_count
        FROM optical_power_history 
        WHERE ip_address = %s 
        AND interface_index = %s 
        AND measurement_timestamp >= NOW() - INTERVAL '%s days'
        GROUP BY hour_bucket
        ORDER BY hour_bucket ASC
        """
        return self.execute_query(query, (ip_address, interface_index, days))
    
    # Device Groups CRUD Operations
    def create_device_group(self, group_name, description=None):
        """Create a new device group"""
        query = """
        INSERT INTO device_groups (group_name, description, updated_at)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        RETURNING id, group_name, description, created_at, updated_at
        """
        return self.execute_query(query, (group_name, description))
    
    def get_all_device_groups(self):
        """Get all device groups with device counts"""
        query = """
        SELECT g.id, g.group_name, g.description, g.created_at, g.updated_at,
               COUNT(gd.ip_address) as device_count
        FROM device_groups g
        LEFT JOIN group_devices gd ON g.id = gd.group_id
        GROUP BY g.id, g.group_name, g.description, g.created_at, g.updated_at
        ORDER BY g.group_name
        """
        return self.execute_query(query)
    
    def get_device_group(self, group_id):
        """Get a specific device group with its devices"""
        # Get group info
        group_query = "SELECT id, group_name, description, created_at, updated_at FROM device_groups WHERE id = %s"
        group_info = self.execute_query(group_query, (group_id,))
        
        if not group_info:
            return None
            
        # Get group devices
        devices_query = """
        SELECT ip_address, added_at 
        FROM group_devices 
        WHERE group_id = %s 
        ORDER BY added_at
        """
        devices = self.execute_query(devices_query, (group_id,))
        
        return {
            'group_info': group_info[0],
            'devices': devices
        }
    
    def update_device_group(self, group_id, group_name=None, description=None):
        """Update a device group"""
        updates = []
        params = []
        
        if group_name is not None:
            updates.append("group_name = %s")
            params.append(group_name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        
        if not updates:
            return False
            
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(group_id)
        
        query = f"UPDATE device_groups SET {', '.join(updates)} WHERE id = %s"
        return self.execute_query(query, params, fetch=False)
    
    def delete_device_group(self, group_id):
        """Delete a device group and all its devices"""
        # First delete all devices from the group
        query1 = "DELETE FROM group_devices WHERE group_id = %s"
        self.execute_query(query1, (group_id,), fetch=False)
        
        # Then delete the group itself
        query2 = "DELETE FROM device_groups WHERE id = %s"
        result = self.execute_query(query2, (group_id,), fetch=False)
        return result is not None
    
    def add_device_to_group(self, group_id, ip_address):
        """Add a device to a group"""
        query = """
        INSERT INTO group_devices (group_id, ip_address)
        VALUES (%s, %s)
        ON CONFLICT (group_id, ip_address) DO NOTHING
        """
        try:
            self.execute_query(query, (group_id, ip_address), fetch=False)
            return True
        except Exception:
            return False
    
    def remove_device_from_group(self, group_id, ip_address):
        """Remove a device from a group"""
        query = "DELETE FROM group_devices WHERE group_id = %s AND ip_address = %s"
        return self.execute_query(query, (group_id, ip_address), fetch=False)
    
    def get_group_devices(self, group_id):
        """Get all devices in a group"""
        query = """
        SELECT ip_address, added_at 
        FROM group_devices 
        WHERE group_id = %s 
        ORDER BY added_at
        """
        return self.execute_query(query, (group_id,))
    
    def get_groups_for_device(self, ip_address):
        """Get all groups that contain a specific device"""
        query = """
        SELECT g.id, g.group_name, g.description
        FROM device_groups g
        JOIN group_devices gd ON g.id = gd.group_id
        WHERE gd.ip_address = %s
        ORDER BY g.group_name
        """
        return self.execute_query(query, (ip_address,))

# Global database manager instance
db = DatabaseManager()
