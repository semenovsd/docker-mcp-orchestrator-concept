"""Script to validate VAST 3.0 document and check against XSD schema."""

import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple
import re


def validate_vast_3_0(xml_content: str) -> Dict[str, List[str]]:
    """Validate VAST document against VAST 3.0 specification."""
    
    errors = []
    warnings = []
    
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return {
            "errors": [f"XML Parse Error: {str(e)}"],
            "warnings": []
        }
    
    # Check VAST root element
    if root.tag != "VAST":
        errors.append("Root element must be 'VAST'")
    else:
        version = root.get("version")
        if version != "3.0":
            errors.append(f"VAST version must be '3.0', found: '{version}'")
    
    # Check namespace
    if "xmlns:xsi" not in root.attrib:
        errors.append("Missing xmlns:xsi namespace declaration")
    
    # Find Ad element
    ad = root.find("Ad")
    if ad is None:
        errors.append("Missing required element: <Ad>")
        return {"errors": errors, "warnings": warnings}
    
    # Check Ad id
    ad_id = ad.get("id")
    if not ad_id:
        warnings.append("Element <Ad> should have 'id' attribute")
    
    # Find InLine
    inline = ad.find("InLine")
    if inline is None:
        errors.append("Missing required element: <InLine>")
        return {"errors": errors, "warnings": warnings}
    
    # Check AdSystem (REQUIRED in VAST 3.0)
    ad_system = inline.find("AdSystem")
    if ad_system is None:
        errors.append("Missing required element: <AdSystem>")
    else:
        ad_system_version = ad_system.get("version")
        if not ad_system_version:
            errors.append("Element <AdSystem> must have 'version' attribute in VAST 3.0")
        if not ad_system.text or not ad_system.text.strip():
            errors.append("Element <AdSystem> must have text content")
    
    # Check AdTitle (REQUIRED)
    ad_title = inline.find("AdTitle")
    if ad_title is None:
        errors.append("Missing required element: <AdTitle>")
    elif not ad_title.text or not ad_title.text.strip():
        errors.append("Element <AdTitle> must have text content")
    
    # Check Description (optional but present)
    description = inline.find("Description")
    if description is not None and (not description.text or not description.text.strip()):
        warnings.append("Element <Description> is present but empty")
    
    # Check Error (optional)
    error = inline.find("Error")
    if error is not None:
        error_text = error.text if error.text else ""
        if "[ERRORCODE]" not in error_text:
            warnings.append("Element <Error> should contain [ERRORCODE] macro")
    
    # Check Impression (REQUIRED, at least one)
    impressions = inline.findall("Impression")
    if len(impressions) == 0:
        errors.append("Missing required element: <Impression> (at least one required)")
    else:
        for imp in impressions:
            if not imp.text or not imp.text.strip():
                errors.append("Element <Impression> must have URL content")
    
    # Check Creatives (REQUIRED)
    creatives = inline.find("Creatives")
    if creatives is None:
        errors.append("Missing required element: <Creatives>")
        return {"errors": errors, "warnings": warnings}
    
    # Check Creative (REQUIRED, at least one)
    creative_list = creatives.findall("Creative")
    if len(creative_list) == 0:
        errors.append("Missing required element: <Creative> (at least one required)")
        return {"errors": errors, "warnings": warnings}
    
    for creative in creative_list:
        creative_id = creative.get("id")
        if not creative_id:
            warnings.append("Element <Creative> should have 'id' attribute")
        
        # Check Linear
        linear = creative.find("Linear")
        if linear is None:
            errors.append("Missing required element: <Linear> in <Creative>")
            continue
        
        # Check Duration (REQUIRED)
        duration = linear.find("Duration")
        if duration is None:
            errors.append("Missing required element: <Duration> in <Linear>")
        else:
            duration_text = duration.text if duration.text else ""
            # Check format: HH:MM:SS or HH:MM:SS.mmm
            if not re.match(r'^\d{2}:\d{2}:\d{2}(\.\d{1,3})?$', duration_text.strip()):
                errors.append(f"Invalid <Duration> format: '{duration_text}'. Must be HH:MM:SS or HH:MM:SS.mmm")
        
        # Check skipoffset format
        skipoffset = linear.get("skipoffset")
        if skipoffset:
            # Can be time format or percentage
            if not (re.match(r'^\d{2}:\d{2}:\d{2}(\.\d{1,3})?$', skipoffset) or 
                    re.match(r'^\d+%$', skipoffset)):
                errors.append(f"Invalid skipoffset format: '{skipoffset}'. Must be HH:MM:SS, HH:MM:SS.mmm, or percentage")
        
        # Check TrackingEvents (optional)
        tracking_events = linear.find("TrackingEvents")
        if tracking_events is not None:
            tracking_list = tracking_events.findall("Tracking")
            valid_events = [
                "creativeView", "start", "firstQuartile", "midpoint", 
                "thirdQuartile", "complete", "mute", "unmute", "pause", 
                "resume", "rewind", "fullscreen", "exitFullscreen", 
                "expand", "collapse", "acceptInvitation", "close", "skip", "progress"
            ]
            for tracking in tracking_list:
                event = tracking.get("event")
                if not event:
                    errors.append("Element <Tracking> must have 'event' attribute")
                elif event not in valid_events:
                    warnings.append(f"Unknown tracking event: '{event}' (may be custom)")
                if not tracking.text or not tracking.text.strip():
                    errors.append("Element <Tracking> must have URL content")
        
        # Check VideoClicks (optional)
        video_clicks = linear.find("VideoClicks")
        if video_clicks is not None:
            click_through = video_clicks.find("ClickThrough")
            if click_through is not None:
                if not click_through.text or not click_through.text.strip():
                    errors.append("Element <ClickThrough> must have URL content if present")
        
        # Check MediaFiles (REQUIRED)
        media_files = linear.find("MediaFiles")
        if media_files is None:
            errors.append("Missing required element: <MediaFiles> in <Linear>")
        else:
            media_file_list = media_files.findall("MediaFile")
            if len(media_file_list) == 0:
                errors.append("Missing required element: <MediaFile> (at least one required)")
            else:
                for media_file in media_file_list:
                    # Required attributes
                    required_attrs = ["delivery", "type", "width", "height"]
                    for attr in required_attrs:
                        if not media_file.get(attr):
                            errors.append(f"Element <MediaFile> must have '{attr}' attribute")
                    
                    # Check delivery value
                    delivery = media_file.get("delivery")
                    if delivery and delivery not in ["progressive", "streaming"]:
                        errors.append(f"Invalid 'delivery' value: '{delivery}'. Must be 'progressive' or 'streaming'")
                    
                    # Check type format
                    media_type = media_file.get("type")
                    if media_type and not re.match(r'^(video|audio)/.+', media_type):
                        warnings.append(f"Media type should start with 'video/' or 'audio/': '{media_type}'")
                    
                    # Check numeric attributes
                    for attr in ["width", "height", "bitrate"]:
                        value = media_file.get(attr)
                        if value:
                            try:
                                int(value)
                            except ValueError:
                                errors.append(f"Attribute '{attr}' must be a number, found: '{value}'")
                    
                    # Check boolean attributes
                    for attr in ["isScalable", "keepAspectRatio"]:
                        value = media_file.get(attr)
                        if value and value not in ["true", "false"]:
                            errors.append(f"Attribute '{attr}' must be 'true' or 'false', found: '{value}'")
                    
                    # Check MediaFile content
                    if not media_file.text or not media_file.text.strip():
                        errors.append("Element <MediaFile> must have URL content")
    
    return {"errors": errors, "warnings": warnings}


def check_xsd_compliance(xml_content: str) -> List[str]:
    """Check for common XSD compliance issues."""
    
    issues = []
    
    # Check for proper XML declaration
    if not xml_content.strip().startswith('<?xml'):
        issues.append("Missing XML declaration")
    
    # Check encoding
    if 'encoding=' not in xml_content[:200]:
        issues.append("XML declaration should specify encoding")
    
    # Check for CDATA usage (good practice but not XSD requirement)
    # This is just informational
    
    return issues


if __name__ == "__main__":
    # Test with provided XML
    xml_content = """<?xml version='1.0' encoding='utf-8'?>
<VAST xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="3.0" xsi:noNamespaceSchemaLocation="http://specs.adfox.ru/uploads/vast.xsd">
    <Ad id="01958ad3-a77e-74cb-960a-c3d4979157db">
    <InLine>
    <AdSystem>Rollover</AdSystem>
    <AdTitle>Linear Video Ad</AdTitle>
    <Description>Video Ad</Description>
    <Error><![CDATA[https://example.com/error.gif?code=[ERRORCODE]]]></Error>
    <Impression id="Teletarget"><![CDATA[https://example.com/impression.gif]]></Impression>
    <Creatives>
        <Creative id="test">
    <Linear>
        <Duration>00:00:15</Duration>
        <MediaFiles>
            <MediaFile delivery="progressive" type="video/mp4" width="854" height="480"><![CDATA[https://example.com/video.mp4]]></MediaFile>
        </MediaFiles>
    </Linear>
</Creative>
    </Creatives>
    </InLine>
</Ad>
</VAST>"""
    
    result = validate_vast_3_0(xml_content)
    print("Errors:", result["errors"])
    print("Warnings:", result["warnings"])
