#!/usr/bin/env python3
"""
VAST 3.0 Validator - Строгая проверка соответствия спецификации VAST 3.0
"""

import re
from typing import List, Tuple
from xml.etree import ElementTree as ET


class VAST3Validator:
    """Строгий валидатор VAST 3.0 документов."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate(self, vast_xml: str) -> Tuple[List[str], List[str]]:
        """
        Строго валидирует VAST документ на соответствие спецификации VAST 3.0.
        
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
            
            # Проверяем корневой элемент
            if root.tag != 'VAST':
                self.errors.append("Корневой элемент должен быть 'VAST'")
                return self.errors, self.warnings
            
            # КРИТИЧНО: Проверяем версию VAST 3.0
            version = root.get('version')
            if version != '3.0':
                self.errors.append(
                    f"КРИТИЧНО: Версия VAST указана как '{version}', "
                    "но требуется строго '3.0' для соответствия спецификации VAST 3.0"
                )
            
            # Ищем Ad элементы
            ads = root.findall('Ad')
            if not ads:
                self.errors.append("VAST документ должен содержать хотя бы один элемент <Ad>")
            
            for ad in ads:
                self._validate_ad(ad)
            
        except ET.ParseError as e:
            self.errors.append(f"Ошибка парсинга XML: {e}")
        except Exception as e:
            self.errors.append(f"Неожиданная ошибка: {e}")
        
        return self.errors, self.warnings
    
    def _validate_ad(self, ad_element):
        """Валидирует элемент Ad для VAST 3.0."""
        # Проверяем наличие id
        ad_id = ad_element.get('id')
        if not ad_id:
            self.warnings.append("Элемент <Ad> должен иметь атрибут 'id' (рекомендуется)")
        
        inline = ad_element.find('InLine')
        wrapper = ad_element.find('Wrapper')
        
        if inline is None and wrapper is None:
            self.errors.append(
                f"Ad (id={ad_id or 'unknown'}): "
                "Должен содержать либо <InLine>, либо <Wrapper>"
            )
            return
        
        if inline is not None:
            self._validate_inline(inline, ad_id)
    
    def _validate_inline(self, inline_element, ad_id):
        """Валидирует элемент InLine для VAST 3.0."""
        # Обязательные элементы в InLine
        ad_system = inline_element.find('AdSystem')
        if ad_system is None:
            self.errors.append(
                f"InLine (Ad id={ad_id or 'unknown'}): "
                "Отсутствует обязательный элемент <AdSystem>"
            )
        elif not (ad_system.text or '').strip():
            self.errors.append(
                f"InLine (Ad id={ad_id or 'unknown'}): "
                "Элемент <AdSystem> не может быть пустым"
            )
        
        ad_title = inline_element.find('AdTitle')
        if ad_title is None:
            self.errors.append(
                f"InLine (Ad id={ad_id or 'unknown'}): "
                "Отсутствует обязательный элемент <AdTitle>"
            )
        elif not (ad_title.text or '').strip():
            self.errors.append(
                f"InLine (Ad id={ad_id or 'unknown'}): "
                "Элемент <AdTitle> не может быть пустым"
            )
        
        # Проверяем Creatives
        creatives = inline_element.find('Creatives')
        if creatives is None:
            self.errors.append(
                f"InLine (Ad id={ad_id or 'unknown'}): "
                "Отсутствует обязательный элемент <Creatives>"
            )
        else:
            creative_list = creatives.findall('Creative')
            if not creative_list:
                self.errors.append(
                    f"InLine (Ad id={ad_id or 'unknown'}): "
                    "Элемент <Creatives> должен содержать хотя бы один <Creative>"
                )
            
            for creative in creative_list:
                self._validate_creative(creative, ad_id)
    
    def _validate_creative(self, creative_element, ad_id):
        """Валидирует элемент Creative для VAST 3.0."""
        creative_id = creative_element.get('id')
        
        # Creative должен содержать Linear, NonLinear или CompanionAds
        linear = creative_element.find('Linear')
        non_linear = creative_element.find('NonLinearAds')
        companion = creative_element.find('CompanionAds')
        
        if not (linear or non_linear or companion):
            self.errors.append(
                f"Creative (id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                "Должен содержать <Linear>, <NonLinearAds> или <CompanionAds>"
            )
        
        if linear is not None:
            self._validate_linear(linear, creative_id, ad_id)
    
    def _validate_linear(self, linear_element, creative_id, ad_id):
        """Валидирует элемент Linear для VAST 3.0."""
        # Обязательный элемент Duration
        duration = linear_element.find('Duration')
        if duration is None:
            self.errors.append(
                f"Linear (Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                "Отсутствует обязательный элемент <Duration>"
            )
        else:
            duration_text = (duration.text or '').strip()
            if not duration_text:
                self.errors.append(
                    f"Linear (Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                    "Элемент <Duration> не может быть пустым"
                )
            else:
                # Проверяем формат Duration (HH:MM:SS.mmm или HH:MM:SS)
                if not re.match(r'^\d{2}:\d{2}:\d{2}(\.\d{1,3})?$', duration_text):
                    self.warnings.append(
                        f"Linear (Creative id={creative_id or 'unknown'}): "
                        f"Формат Duration '{duration_text}' может быть некорректным. "
                        "Ожидается HH:MM:SS или HH:MM:SS.mmm"
                    )
        
        # Проверяем skipoffset формат
        skipoffset = linear_element.get('skipoffset')
        if skipoffset:
            # Может быть HH:MM:SS или процент (например, 15%)
            if not (re.match(r'^\d{2}:\d{2}:\d{2}(\.\d{1,3})?$', skipoffset) or 
                    re.match(r'^\d+%$', skipoffset)):
                self.warnings.append(
                    f"Linear (Creative id={creative_id or 'unknown'}): "
                    f"Формат skipoffset '{skipoffset}' может быть некорректным. "
                    "Ожидается HH:MM:SS или процент (например, 15%)"
                )
        
        # Проверяем VideoClicks
        video_clicks = linear_element.find('VideoClicks')
        if video_clicks is not None:
            click_through = video_clicks.find('ClickThrough')
            if click_through is not None:
                text = (click_through.text or '').strip()
                if not text:
                    self.errors.append(
                        f"VideoClicks (Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                        "Элемент <ClickThrough> пустой. "
                        "В VAST 3.0 должен содержать URL или быть удален."
                    )
        
        # Обязательный элемент MediaFiles
        media_files = linear_element.find('MediaFiles')
        if media_files is None:
            self.errors.append(
                f"Linear (Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                "Отсутствует обязательный элемент <MediaFiles>"
            )
        else:
            media_file_list = media_files.findall('MediaFile')
            if not media_file_list:
                self.errors.append(
                    f"MediaFiles (Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                    "Должен содержать хотя бы один элемент <MediaFile>"
                )
            
            for media_file in media_file_list:
                self._validate_media_file_v3(media_file, creative_id, ad_id)
    
    def _validate_media_file_v3(self, media_file, creative_id, ad_id):
        """Валидирует элемент MediaFile для VAST 3.0."""
        media_id = media_file.get('id')
        
        # Обязательные атрибуты в VAST 3.0
        required_attrs = ['delivery', 'type']
        for attr in required_attrs:
            if attr not in media_file.attrib:
                self.errors.append(
                    f"MediaFile (id={media_id or 'unknown'}, Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                    f"Отсутствует обязательный атрибут '{attr}'"
                )
        
        # Проверяем неверные атрибуты (VAST 3.0 использует те же, что и 2.0)
        if 'isScalable' in media_file.attrib:
            self.errors.append(
                f"MediaFile (id={media_id or 'unknown'}, Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                "КРИТИЧНО: Неверный атрибут 'isScalable'. "
                "В VAST 3.0 должен быть 'scalable' (boolean)"
            )
        
        if 'keepAspectRatio' in media_file.attrib:
            self.errors.append(
                f"MediaFile (id={media_id or 'unknown'}, Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                "КРИТИЧНО: Неверный атрибут 'keepAspectRatio'. "
                "В VAST 3.0 должен быть 'maintainAspectRatio' (boolean)"
            )
        
        # Проверяем правильные атрибуты
        if 'scalable' in media_file.attrib:
            scalable_value = media_file.get('scalable')
            if scalable_value not in ['true', 'false']:
                self.warnings.append(
                    f"MediaFile (id={media_id or 'unknown'}): "
                    f"Атрибут 'scalable' должен быть 'true' или 'false', получено: '{scalable_value}'"
                )
        
        if 'maintainAspectRatio' in media_file.attrib:
            maintain_value = media_file.get('maintainAspectRatio')
            if maintain_value not in ['true', 'false']:
                self.warnings.append(
                    f"MediaFile (id={media_id or 'unknown'}): "
                    f"Атрибут 'maintainAspectRatio' должен быть 'true' или 'false', получено: '{maintain_value}'"
                )
        
        # Проверяем наличие URL
        text = (media_file.text or '').strip()
        if not text:
            self.errors.append(
                f"MediaFile (id={media_id or 'unknown'}, Creative id={creative_id or 'unknown'}, Ad id={ad_id or 'unknown'}): "
                "Отсутствует URL медиафайла (обязательно)"
            )
        
        # Проверяем тип delivery
        delivery = media_file.get('delivery')
        if delivery and delivery not in ['progressive', 'streaming']:
            self.warnings.append(
                f"MediaFile (id={media_id or 'unknown'}): "
                f"Атрибут 'delivery' должен быть 'progressive' или 'streaming', получено: '{delivery}'"
            )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        with open(filename, 'r', encoding='utf-8') as f:
            vast_xml = f.read()
    else:
        print("Использование: python3 vast3_validator.py <vast_file.xml>")
        sys.exit(1)
    
    validator = VAST3Validator()
    errors, warnings = validator.validate(vast_xml)
    
    print("=" * 80)
    print("ВАЛИДАЦИЯ VAST 3.0 - СТРОГАЯ ПРОВЕРКА")
    print("=" * 80)
    
    print(f"\n🔴 КРИТИЧЕСКИЕ ОШИБКИ ({len(errors)}):")
    if errors:
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
    else:
        print("  ✓ Критических ошибок не обнаружено")
    
    print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(warnings)}):")
    if warnings:
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    else:
        print("  ✓ Предупреждений нет")
    
    print("\n" + "=" * 80)
    if not errors:
        print("✅ Документ соответствует спецификации VAST 3.0!")
    else:
        print("❌ Документ НЕ соответствует спецификации VAST 3.0")
        print("   Исправьте указанные ошибки для полного соответствия.")
    print("=" * 80)
