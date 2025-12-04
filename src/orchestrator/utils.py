"""Utility functions for VAST document processing."""

import re
from typing import Optional
from xml.sax.saxutils import escape


def escape_xml_url(url: str) -> str:
    """
    Escape special XML characters in URL for safe inclusion in VAST document.
    
    This function properly escapes XML special characters, especially '&' which
    must be escaped as '&amp;' to avoid XML parser errors like:
    "The reference to entity 'c' must end with the ';' delimiter."
    
    Args:
        url: URL string that may contain unescaped XML characters
        
    Returns:
        URL with properly escaped XML characters
        
    Examples:
        >>> escape_xml_url("https://example.com?param1=value1&param2=value2")
        'https://example.com?param1=value1&amp;param2=value2'
        
        >>> escape_xml_url("https://example.com?query=test&id=123")
        'https://example.com?query=test&amp;id=123'
    """
    if not url:
        return url
    
    # Escape XML special characters: &, <, >
    # xml.sax.saxutils.escape() escapes &, <, > by default
    # Don't pass entities dict - escape() handles &, <, > automatically
    escaped = escape(url)
    
    return escaped


def escape_xml_url_advanced(url: str, escape_quotes: bool = False) -> str:
    """
    Advanced URL escaping with optional quote escaping.
    
    Use this if URLs are placed in XML attributes that use quotes.
    
    Args:
        url: URL string to escape
        escape_quotes: If True, also escape single and double quotes
        
    Returns:
        Properly escaped URL
        
    Examples:
        >>> escape_xml_url_advanced("https://example.com?q=test&id=1")
        'https://example.com?q=test&amp;id=1'
        
        >>> escape_xml_url_advanced("https://example.com?q='test'", escape_quotes=True)
        "https://example.com?q=&apos;test&apos;"
    """
    if not url:
        return url
    
    # escape() handles &, <, > by default
    # Only add quote escaping if needed
    entities = {}
    
    if escape_quotes:
        entities["'"] = '&apos;'
        entities['"'] = '&quot;'
    
    if entities:
        return escape(url, entities=entities)
    else:
        return escape(url)


def escape_vast_url(url: str) -> str:
    """
    Escape URL specifically for VAST document text content.
    
    This is an alias for escape_xml_url() with a more descriptive name
    for VAST-specific use cases.
    
    Args:
        url: URL to escape for VAST document
        
    Returns:
        Escaped URL safe for VAST XML
    """
    return escape_xml_url(url)


def validate_and_escape_vast_url(url: Optional[str]) -> Optional[str]:
    """
    Validate URL and escape it for VAST document.
    
    Returns None if URL is empty/None, otherwise returns escaped URL.
    
    Args:
        url: URL string or None
        
    Returns:
        Escaped URL or None if input was empty/None
    """
    if not url or not url.strip():
        return None
    
    return escape_vast_url(url.strip())
