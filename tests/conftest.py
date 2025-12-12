"""
Pytest configuration and fixtures.
"""

import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_port_xcvr_output():
    """Sample output from 'port xcvr show' command."""
    return """
+-----+-------+------+--------+------------+----------+----------+---------+
| Port| Admin | Oper | Type   | Vendor     | Part No  | Serial   | Wave    |
+-----+-------+------+--------+------------+----------+----------+---------+
| 1   | Ena   | Up   | SFP+   | FINISAR    | FTLX8574 | ABC123   | 850nm   |
| 2   | Ena   | Down | SFP+   | CISCO      | SFP-10G  | DEF456   | 1310nm  |
| 3   | Dis   | Down | Empty  |            |          |          |         |
+-----+-------+------+--------+------------+----------+----------+---------+
"""


@pytest.fixture
def sample_port_show_output():
    """Sample output from 'port show' command."""
    return """
+------+-------+------+--------+-------+------+
| Port | Admin | Oper | Speed  | Duplex| MTU  |
+------+-------+------+--------+-------+------+
| 1    | Ena   | Up   | 10G    | Full  | 9000 |
| 2    | Ena   | Down | 1G     | Full  | 1500 |
| 3    | Dis   | Down | Auto   | Auto  | 1500 |
+------+-------+------+--------+-------+------+
"""


@pytest.fixture
def sample_lldp_output():
    """Sample output from 'lldp show neighbors' command."""
    return """
Local Port: 1
  Remote Chassis ID: 00:11:22:33:44:55
  Remote Port: Ethernet1/1
  Remote System Name: switch-01.example.com
  Remote Management Address: 192.168.1.10

Local Port: 2
  Remote Chassis ID: 00:11:22:33:44:66
  Remote Port: GigabitEthernet0/1
  Remote System Name: router-01.example.com
  Remote Management Address: 192.168.1.20
"""


@pytest.fixture
def sample_diagnostics_output():
    """Sample output from 'port xcvr show port X diagnostics' command."""
    return """
Port 1 Transceiver Diagnostics:
  Temperature: 35.5 C
  Voltage: 3.30 V
  TX Power: -2.5 dBm
  RX Power: -8.3 dBm
  Bias Current: 6.5 mA
"""


@pytest.fixture
def mock_db():
    """Mock database manager for testing."""
    class MockDB:
        def __init__(self):
            self.queries = []
            self.results = []
        
        def execute_query(self, query, params=None):
            self.queries.append((query, params))
            if self.results:
                return self.results.pop(0)
            return []
        
        def set_results(self, results):
            self.results = list(results)
    
    return MockDB()


@pytest.fixture
def app():
    """Create Flask test application."""
    from backend.app import create_app
    
    app = create_app({'TESTING': True})
    return app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
