#!/usr/bin/env python3
"""
XSD Schema Validator - Проверка XML документа по XSD схеме
"""

import sys
import urllib.request
from xml.etree import ElementTree as ET
from io import BytesIO

try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    HAS_LXML = False
    print("⚠️  lxml не установлен. Установите: pip install lxml")
    print("   Будет использована базовая проверка XML структуры.")


def validate_xsd(xml_file, xsd_url):
    """
    Валидирует XML файл по XSD схеме.
    
    Args:
        xml_file: Путь к XML файлу
        xsd_url: URL XSD схемы
        
    Returns:
        Tuple (is_valid, errors)
    """
    if not HAS_LXML:
        return False, ["lxml не установлен. Установите: pip install lxml"]
    
    try:
        # Загружаем XML файл
        with open(xml_file, 'rb') as f:
            xml_doc = f.read()
        
        # Загружаем XSD схему
        try:
            with urllib.request.urlopen(xsd_url, timeout=10) as response:
                xsd_doc = response.read()
        except Exception as e:
            return False, [f"Не удалось загрузить XSD схему: {e}"]
        
        # Парсим XSD схему
        xsd_root = etree.XML(xsd_doc)
        schema = etree.XMLSchema(xsd_root)
        
        # Парсим XML документ
        xml_root = etree.XML(xml_doc)
        
        # Валидируем
        is_valid = schema.validate(xml_root)
        
        if is_valid:
            return True, []
        else:
            errors = []
            for error in schema.error_log:
                errors.append(f"Line {error.line}: {error.message}")
            return False, errors
            
    except etree.XMLSyntaxError as e:
        return False, [f"Ошибка синтаксиса XML: {e}"]
    except etree.XMLSchemaParseError as e:
        return False, [f"Ошибка парсинга XSD схемы: {e}"]
    except Exception as e:
        return False, [f"Неожиданная ошибка: {e}"]


def basic_xml_check(xml_file):
    """
    Базовая проверка XML структуры без XSD схемы.
    """
    errors = []
    warnings = []
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        if root.tag != 'VAST':
            errors.append(f"Корневой элемент должен быть 'VAST', получен '{root.tag}'")
        
        # Проверяем базовую структуру
        ads = root.findall('Ad')
        if not ads:
            errors.append("Документ должен содержать хотя бы один элемент <Ad>")
        
        return errors, warnings
        
    except ET.ParseError as e:
        return [f"Ошибка парсинга XML: {e}"], []


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 xsd_validator.py <xml_file> [xsd_url]")
        print("Пример: python3 xsd_validator.py test.xml http://specs.adfox.ru/uploads/vast.xsd")
        sys.exit(1)
    
    xml_file = sys.argv[1]
    xsd_url = sys.argv[2] if len(sys.argv) > 2 else "http://specs.adfox.ru/uploads/vast.xsd"
    
    print("=" * 80)
    print("ВАЛИДАЦИЯ ПО XSD СХЕМЕ")
    print("=" * 80)
    print(f"\nXML файл: {xml_file}")
    print(f"XSD схема: {xsd_url}\n")
    
    if HAS_LXML:
        is_valid, errors = validate_xsd(xml_file, xsd_url)
        
        if is_valid:
            print("✅ Документ соответствует XSD схеме!")
        else:
            print("❌ Документ НЕ соответствует XSD схеме:")
            print("\nОшибки валидации:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
    else:
        print("⚠️  lxml не установлен. Выполняется базовая проверка XML...")
        errors, warnings = basic_xml_check(xml_file)
        
        if not errors:
            print("✅ Базовая структура XML корректна")
        else:
            print("❌ Обнаружены ошибки:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
        
        if warnings:
            print("\nПредупреждения:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
    
    print("\n" + "=" * 80)
