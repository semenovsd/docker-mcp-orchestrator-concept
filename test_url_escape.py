#!/usr/bin/env python3
"""
Test script for URL escaping function.
Demonstrates how to escape URLs before inserting them into VAST XML documents.
"""

from src.orchestrator.utils import escape_url_for_xml


def test_url_escaping():
    """Test various URL formats that appear in VAST documents."""
    
    test_cases = [
        # Basic query parameters
        (
            "https://example.com?param1=value1&param2=value2",
            "https://example.com?param1=value1&amp;param2=value2"
        ),
        # URL with multiple parameters (like AdServing impression)
        (
            "https://bs.serving-sys.ru/Serving/adServer.bs?cn=display&c=25&pli=1087731545&adid=1087731546&ord=01924353-367a-71c4-b2a8-b43c9bb85e8f&puid=12e12ee&psid=2512041114019ae86d-19de-7b82-b3fc-336cb5eef8d0",
            "https://bs.serving-sys.ru/Serving/adServer.bs?cn=display&amp;c=25&amp;pli=1087731545&amp;adid=1087731546&amp;ord=01924353-367a-71c4-b2a8-b43c9bb85e8f&amp;puid=12e12ee&amp;psid=2512041114019ae86d-19de-7b82-b3fc-336cb5eef8d0"
        ),
        # URL starting with & (like mhverifier)
        (
            "https://px385.mhverifier.ru/s.gif?&mh_camp=01924353-367a-71c4-b2a8-b43c9bb85e8f&puid=12e12ee&event=start",
            "https://px385.mhverifier.ru/s.gif?&amp;mh_camp=01924353-367a-71c4-b2a8-b43c9bb85e8f&amp;puid=12e12ee&amp;event=start"
        ),
        # URL with encoded parameters (interactionsStr)
        (
            "https://bs.serving-sys.ru/Serving/adServer.bs?cn=isi&iv=2&interactionsStr=1087731546%7E%7E%7E0%7E%7E%7E%5EebVideoStarted%7E0%7E0%7E01010&ord=01924353-367a-71c4-b2a8-b43c9bb85e8f&puid=12e12ee&psid=2512041114019ae86d-19de-7b82-b3fc-336cb5eef8d0",
            "https://bs.serving-sys.ru/Serving/adServer.bs?cn=isi&amp;iv=2&amp;interactionsStr=1087731546%7E%7E%7E0%7E%7E%7E%5EebVideoStarted%7E0%7E0%7E01010&amp;ord=01924353-367a-71c4-b2a8-b43c9bb85e8f&amp;puid=12e12ee&amp;psid=2512041114019ae86d-19de-7b82-b3fc-336cb5eef8d0"
        ),
        # URL without parameters (should remain unchanged)
        (
            "https://example.com/path/to/resource",
            "https://example.com/path/to/resource"
        ),
        # URL with already escaped entities (should not double-escape)
        (
            "https://example.com?text=Hello&amp;World",
            "https://example.com?text=Hello&amp;World"
        ),
        # Empty string
        (
            "",
            ""
        ),
    ]
    
    print("Testing URL escaping for XML/VAST documents:\n")
    print("=" * 80)
    
    all_passed = True
    for i, (input_url, expected) in enumerate(test_cases, 1):
        result = escape_url_for_xml(input_url)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\nTest {i}: {status}")
        print(f"Input:    {input_url[:70]}..." if len(input_url) > 70 else f"Input:    {input_url}")
        print(f"Expected: {expected[:70]}..." if len(expected) > 70 else f"Expected: {expected}")
        print(f"Got:      {result[:70]}..." if len(result) > 70 else f"Got:      {result}")
        
        if not passed:
            print(f"❌ MISMATCH!")
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed!")
    
    return all_passed


def example_usage():
    """Show example of how to use the function when building VAST XML."""
    
    print("\n" + "=" * 80)
    print("EXAMPLE: Using escape_url_for_xml() when building VAST XML")
    print("=" * 80)
    
    # Original URLs (as they come from your system)
    impression_url = "https://bs.serving-sys.ru/Serving/adServer.bs?cn=display&c=25&pli=1087731545&adid=1087731546&ord=01924353-367a-71c4-b2a8-b43c9bb85e8f&puid=12e12ee&psid=2512041114019ae86d-19de-7b82-b3fc-336cb5eef8d0"
    tracking_url = "https://px385.mhverifier.ru/s.gif?&mh_camp=01924353-367a-71c4-b2a8-b43c9bb85e8f&puid=12e12ee&event=start"
    
    # Escape URLs before inserting into XML
    escaped_impression = escape_url_for_xml(impression_url)
    escaped_tracking = escape_url_for_xml(tracking_url)
    
    # Now you can safely use them in XML
    vast_xml = f'''<VAST version="3.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Ad id="test-ad">
    <InLine>
      <Impression id="AdServing">
{escaped_impression}
      </Impression>
      <Creatives>
        <Creative>
          <Linear>
            <TrackingEvents>
              <Tracking event="start">
{escaped_tracking}
              </Tracking>
            </TrackingEvents>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>'''
    
    print("\nBefore escaping:")
    print(f"Impression URL: {impression_url[:60]}...")
    print(f"Tracking URL:   {tracking_url[:60]}...")
    
    print("\nAfter escaping:")
    print(f"Impression URL: {escaped_impression[:60]}...")
    print(f"Tracking URL:   {escaped_tracking[:60]}...")
    
    print("\nGenerated VAST XML snippet:")
    print(vast_xml)


if __name__ == "__main__":
    test_url_escaping()
    example_usage()
