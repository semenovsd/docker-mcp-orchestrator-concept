#!/usr/bin/env python3
"""
VAST 2.0 Validator - Проверка и исправление VAST документов
"""

import re
from typing import List, Tuple
from xml.etree import ElementTree as ET


class VASTValidator:
    """Валидатор VAST 2.0 документов."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate(self, vast_xml: str) -> Tuple[List[str], List[str]]:
        """
        Валидирует VAST документ на соответствие спецификации VAST 2.0.
        
        Args:
            vast_xml: XML строка с VAST документом
            
        Returns:
            Tuple (errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        try:
            # Парсим XML
            root = ET.fromstring(vast_xml)
            
            # Проверяем версию
            if root.tag != 'VAST':
                self.errors.append("Корневой элемент должен быть 'VAST'")
                return self.errors, self.warnings
            
            version = root.get('version')
            if version != '2.0':
                self.warnings.append(f"Версия VAST: {version} (ожидается 2.0)")
            
            # Ищем Ad элементы
            for ad in root.findall('.//Ad'):
                self._validate_ad(ad)
            
        except ET.ParseError as e:
            self.errors.append(f"Ошибка парсинга XML: {e}")
        except Exception as e:
            self.errors.append(f"Неожиданная ошибка: {e}")
        
        return self.errors, self.warnings
    
    def _validate_ad(self, ad_element):
        """Валидирует элемент Ad."""
        inline = ad_element.find('InLine')
        if inline is None:
            return
        
        # Проверяем ClickThrough
        creatives = inline.find('Creatives')
        if creatives is not None:
            for creative in creatives.findall('Creative'):
                linear = creative.find('Linear')
                if linear is not None:
                    video_clicks = linear.find('VideoClicks')
                    if video_clicks is not None:
                        click_through = video_clicks.find('ClickThrough')
                        if click_through is not None:
                            text = (click_through.text or '').strip()
                            if not text:
                                self.errors.append(
                                    "Элемент <ClickThrough> пустой. "
                                    "Должен содержать URL или быть удален."
                                )
        
        # Проверяем MediaFile атрибуты
        for media_file in inline.findall('.//MediaFile'):
            self._validate_media_file(media_file)
    
    def _validate_media_file(self, media_file):
        """Валидирует элемент MediaFile."""
        # Проверяем неверные атрибуты
        if 'isScalable' in media_file.attrib:
            self.errors.append(
                f"MediaFile (id={media_file.get('id', 'unknown')}): "
                "Неверный атрибут 'isScalable'. Должен быть 'scalable'."
            )
        
        if 'keepAspectRatio' in media_file.attrib:
            self.errors.append(
                f"MediaFile (id={media_file.get('id', 'unknown')}): "
                "Неверный атрибут 'keepAspectRatio'. Должен быть 'maintainAspectRatio'."
            )
        
        # Проверяем обязательные атрибуты
        required_attrs = ['delivery', 'type']
        for attr in required_attrs:
            if attr not in media_file.attrib:
                self.errors.append(
                    f"MediaFile (id={media_file.get('id', 'unknown')}): "
                    f"Отсутствует обязательный атрибут '{attr}'."
                )
        
        # Проверяем наличие URL
        text = (media_file.text or '').strip()
        if not text:
            self.errors.append(
                f"MediaFile (id={media_file.get('id', 'unknown')}): "
                "Отсутствует URL медиафайла."
            )


def fix_vast_xml(vast_xml: str) -> str:
    """
    Исправляет известные проблемы в VAST XML.
    
    Args:
        vast_xml: Исходный VAST XML
        
    Returns:
        Исправленный VAST XML
    """
    fixed = vast_xml
    
    # Исправляем атрибуты MediaFile
    fixed = re.sub(
        r'isScalable="([^"]*)"',
        r'scalable="\1"',
        fixed
    )
    fixed = re.sub(
        r'keepAspectRatio="([^"]*)"',
        r'maintainAspectRatio="\1"',
        fixed
    )
    
    # Удаляем пустые ClickThrough
    fixed = re.sub(
        r'<ClickThrough>\s*</ClickThrough>',
        '',
        fixed
    )
    fixed = re.sub(
        r'<ClickThrough>\s*<\!\[CDATA\[\s*\]\]>\s*</ClickThrough>',
        '',
        fixed
    )
    
    return fixed


if __name__ == "__main__":
    # Пример использования
    sample_vast = '''<?xml version='1.0' encoding='utf-8'?>
<VAST xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.0">
    <Ad id="test">
        <InLine>
            <AdSystem>Test</AdSystem>
            <AdTitle>Test Ad</AdTitle>
            <Creatives>
                <Creative>
                    <Linear>
                        <Duration>00:00:15</Duration>
                        <VideoClicks>
                            <ClickThrough></ClickThrough>
                        </VideoClicks>
                        <MediaFiles>
                            <MediaFile delivery="progressive" type="video/mp4" isScalable="true" keepAspectRatio="true">http://example.com/video.mp4</MediaFile>
                        </MediaFiles>
                    </Linear>
                </Creative>
            </Creatives>
        </InLine>
    </Ad>
</VAST>'''
    
    validator = VASTValidator()
    errors, warnings = validator.validate(sample_vast)
    
    print("=== Результаты валидации ===")
    print(f"\nОшибки ({len(errors)}):")
    for error in errors:
        print(f"  ❌ {error}")
    
    print(f"\nПредупреждения ({len(warnings)}):")
    for warning in warnings:
        print(f"  ⚠️  {warning}")
    
    if errors:
        print("\n=== Исправленный XML ===")
        fixed = fix_vast_xml(sample_vast)
        print(fixed)
