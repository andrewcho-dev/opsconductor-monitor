"""
Unit tests for Ciena parsers.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.parsers.ciena import (
    CienaPortXcvrParser,
    CienaPortShowParser,
    CienaPortDiagnosticsParser,
    CienaLldpRemoteParser,
)


class TestCienaPortXcvrParser:
    """Tests for CienaPortXcvrParser."""
    
    def test_parse_valid_output(self, sample_port_xcvr_output):
        """Test parsing valid port xcvr show output."""
        parser = CienaPortXcvrParser()
        results = parser.parse(sample_port_xcvr_output)
        
        # Parser returns a list of parsed results
        assert isinstance(results, list)
    
    def test_parse_empty_output(self):
        """Test parsing empty output."""
        parser = CienaPortXcvrParser()
        results = parser.parse('')
        
        assert results == []
    
    def test_parse_none_output(self):
        """Test parsing None output."""
        parser = CienaPortXcvrParser()
        results = parser.parse(None)
        
        assert results == []


class TestCienaPortShowParser:
    """Tests for CienaPortShowParser."""
    
    def test_parse_valid_output(self, sample_port_show_output):
        """Test parsing valid port show output."""
        parser = CienaPortShowParser()
        results = parser.parse(sample_port_show_output)
        
        # Parser returns a list of parsed results
        assert isinstance(results, list)
    
    def test_parse_empty_output(self):
        """Test parsing empty output."""
        parser = CienaPortShowParser()
        results = parser.parse('')
        
        assert results == []


class TestCienaPortDiagnosticsParser:
    """Tests for CienaPortDiagnosticsParser."""
    
    def test_parse_valid_output(self, sample_diagnostics_output):
        """Test parsing valid diagnostics output."""
        parser = CienaPortDiagnosticsParser()
        results = parser.parse(sample_diagnostics_output)
        
        # Parser returns a list or dict of parsed results
        assert results is not None
    
    def test_parse_empty_output(self):
        """Test parsing empty output."""
        parser = CienaPortDiagnosticsParser()
        results = parser.parse('')
        
        # Parser may return empty list or dict with None values
        assert results is not None


class TestCienaLldpRemoteParser:
    """Tests for CienaLldpRemoteParser."""
    
    def test_parse_valid_output(self, sample_lldp_output):
        """Test parsing valid LLDP output."""
        parser = CienaLldpRemoteParser()
        results = parser.parse(sample_lldp_output)
        
        # Parser returns a list of parsed results
        assert isinstance(results, list)
    
    def test_to_dict(self, sample_lldp_output):
        """Test converting LLDP output to dictionary."""
        parser = CienaLldpRemoteParser()
        result_dict = parser.to_dict(sample_lldp_output)
        
        assert isinstance(result_dict, dict)
    
    def test_parse_empty_output(self):
        """Test parsing empty output."""
        parser = CienaLldpRemoteParser()
        results = parser.parse('')
        
        assert results == []
