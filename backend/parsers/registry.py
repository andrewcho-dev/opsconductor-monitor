"""
Parser registry for managing and accessing output parsers.

The registry provides a centralized way to:
- Register parsers by name
- Retrieve parsers for use in job execution
- List available parsers
"""

from typing import Dict, List, Optional, Type
from .base import BaseParser


class ParserRegistry:
    """
    Singleton registry for output parsers.
    
    Usage:
        # Register a parser
        ParserRegistry.register(MyParser)
        
        # Get a parser by name
        parser = ParserRegistry.get('my_parser')
        result = parser.parse(raw_output)
        
        # Parse directly
        result = ParserRegistry.parse('my_parser', raw_output)
    """
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    _instances: Dict[str, BaseParser] = {}
    
    @classmethod
    def register(cls, parser_class: Type[BaseParser]) -> None:
        """
        Register a parser class.
        
        Args:
            parser_class: Parser class (must inherit from BaseParser)
        
        Raises:
            ValueError: If parser_class is invalid or name already registered
        """
        if not issubclass(parser_class, BaseParser):
            raise ValueError(f'{parser_class} must inherit from BaseParser')
        
        # Create instance to get name
        instance = parser_class()
        name = instance.name
        
        if name in cls._parsers:
            raise ValueError(f'Parser "{name}" is already registered')
        
        cls._parsers[name] = parser_class
        cls._instances[name] = instance
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseParser]:
        """
        Get a parser instance by name.
        
        Args:
            name: Parser name
        
        Returns:
            Parser instance or None if not found
        """
        return cls._instances.get(name)
    
    @classmethod
    def get_or_raise(cls, name: str) -> BaseParser:
        """
        Get a parser instance by name, raising if not found.
        
        Args:
            name: Parser name
        
        Returns:
            Parser instance
        
        Raises:
            ValueError: If parser not found
        """
        parser = cls.get(name)
        if parser is None:
            raise ValueError(f'Unknown parser: {name}. Available: {", ".join(cls.list_names())}')
        return parser
    
    @classmethod
    def parse(cls, name: str, raw_output: str, context: Dict = None) -> List[Dict]:
        """
        Parse output using a named parser.
        
        Args:
            name: Parser name
            raw_output: Raw command output
            context: Optional context
        
        Returns:
            List of parsed records
        
        Raises:
            ValueError: If parser not found
        """
        parser = cls.get_or_raise(name)
        return parser.parse(raw_output, context)
    
    @classmethod
    def safe_parse(cls, name: str, raw_output: str, context: Dict = None) -> Dict:
        """
        Parse output with error handling.
        
        Args:
            name: Parser name
            raw_output: Raw command output
            context: Optional context
        
        Returns:
            Dict with 'success', 'data', and optionally 'error' keys
        """
        parser = cls.get(name)
        if parser is None:
            return {
                'success': False,
                'data': [],
                'error': f'Unknown parser: {name}'
            }
        return parser.safe_parse(raw_output, context)
    
    @classmethod
    def list_names(cls) -> List[str]:
        """
        List all registered parser names.
        
        Returns:
            List of parser names
        """
        return list(cls._parsers.keys())
    
    @classmethod
    def list_parsers(cls) -> List[Dict]:
        """
        List all registered parsers with metadata.
        
        Returns:
            List of parser info dictionaries
        """
        return [
            {
                'name': name,
                'class': parser_class.__name__,
                'module': parser_class.__module__,
            }
            for name, parser_class in cls._parsers.items()
        ]
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a parser is registered.
        
        Args:
            name: Parser name
        
        Returns:
            True if parser is registered
        """
        return name in cls._parsers
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Unregister a parser.
        
        Args:
            name: Parser name
        
        Returns:
            True if parser was unregistered
        """
        if name in cls._parsers:
            del cls._parsers[name]
            del cls._instances[name]
            return True
        return False
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered parsers (mainly for testing)."""
        cls._parsers.clear()
        cls._instances.clear()


def register_parser(parser_class: Type[BaseParser]) -> Type[BaseParser]:
    """
    Decorator to register a parser class.
    
    Usage:
        @register_parser
        class MyParser(BaseParser):
            ...
    """
    ParserRegistry.register(parser_class)
    return parser_class
