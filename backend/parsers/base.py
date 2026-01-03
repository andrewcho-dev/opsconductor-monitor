"""
Base parser interface.

All output parsers should inherit from BaseParser and implement the parse method.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseParser(ABC):
    """
    Abstract base class for output parsers.
    
    Parsers convert raw command output (strings) into structured data (dictionaries).
    Each parser is registered with a unique name in the ParserRegistry.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the unique parser identifier.
        
        This name is used to reference the parser in job definitions.
        Convention: vendor_command_type (e.g., 'ciena_port_xcvr_show')
        """
        pass
    
    @abstractmethod
    def parse(self, raw_output: str, context: Dict = None) -> List[Dict]:
        """
        Parse raw command output into structured data.
        
        Args:
            raw_output: Raw string output from command execution
            context: Optional context (e.g., target IP, interface info)
        
        Returns:
            List of parsed records as dictionaries
        """
        pass
    
    def validate_output(self, raw_output: str) -> bool:
        """
        Validate that the output can be parsed.
        
        Override in subclass for specific validation.
        
        Args:
            raw_output: Raw string output
        
        Returns:
            True if output appears valid for this parser
        """
        return raw_output is not None and len(raw_output.strip()) > 0
    
    def preprocess(self, raw_output: str) -> str:
        """
        Preprocess raw output before parsing.
        
        Override in subclass for specific preprocessing (e.g., removing headers).
        
        Args:
            raw_output: Raw string output
        
        Returns:
            Preprocessed output string
        """
        return raw_output.strip() if raw_output else ''
    
    def postprocess(self, records: List[Dict], context: Dict = None) -> List[Dict]:
        """
        Postprocess parsed records.
        
        Override in subclass to add computed fields, normalize data, etc.
        
        Args:
            records: List of parsed records
            context: Optional context
        
        Returns:
            Postprocessed records
        """
        return records
    
    def safe_parse(self, raw_output: str, context: Dict = None) -> Dict:
        """
        Parse with error handling, returning a result object.
        
        Args:
            raw_output: Raw string output
            context: Optional context
        
        Returns:
            Dict with 'success', 'data', and optionally 'error' keys
        """
        try:
            if not self.validate_output(raw_output):
                return {
                    'success': False,
                    'data': [],
                    'error': 'Invalid or empty output'
                }
            
            preprocessed = self.preprocess(raw_output)
            records = self.parse(preprocessed, context)
            postprocessed = self.postprocess(records, context)
            
            return {
                'success': True,
                'data': postprocessed,
                'count': len(postprocessed)
            }
        except Exception as e:
            return {
                'success': False,
                'data': [],
                'error': str(e)
            }
