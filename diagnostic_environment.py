#!/usr/bin/env python3
"""
Diagnostic complet de l'environnement AI-Trader-v2
"""

import sys
import os
import platform
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Vérifier la version Python"""
    print("🐍 DIAGNOSTIC PYTHON")
    print("-" * 30)
    
    version = sys.version_info
    print(f"Version: {version.major}.{version.minor}.{version.micro}")
    print(f"Exécutable: {sys.executable}")
    print(f"Platform: {platform.platform()}")
    
    if version.major != 3:
        print("❌ Python 3 requis")
        return False
    
    if version.minor >= 13:
        print("✅ Python 3.13+ détecté - Vérification compatibilité packages")
    
    return True

def check_pip():
    """Vérifier pip"""
    print("\n📦 DIAGNOSTIC PIP")
    print("-" * 30)
    
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ pip disponible: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Erreur pip: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ pip non trouvé: {e}")
        return False

def check_project_structure():
    """Vérifier la structure du projet"""
    print("\n📁 DIAGNOSTIC STRUCTURE PROJET")
    print("-" * 30)
    
    required_items = [
        ('ai_trader/', 'Dossier principal'),
        ('ai_trader/__init__.py', 'Package Python'),
        ('ai_trader/main.py', "Point d'entrée"),
        ('config.yaml', 'Configuration'),
        ('requirements.txt', 'Dépendances')
    ]
    
    missing_items = []
    
    for item, description in required_items:
        if os.path.exists(item):
            print(f"✅ {item} - {description}")
        else:
            print(f"❌ {item} - {description} MANQUANT")
            missing_items.append(item)
    
    return len(missing_items) == 0

def check_dependencies():
    """Vérifier les dépendances critiques"""
    print("\n🔍 DIAGNOSTIC DÉPENDANCES")
    print("-" * 30)
    
    critical_deps = [
        'pandas', 'numpy', 'flask', 'requests', 
        'yaml', 'plotly', 'ccxt', 'websocket'
    ]
    
    missing_deps = []
    
    for dep in critical_deps:
        try:
            if dep == 'yaml':
                importlib.import_module('yaml')
                print(f"✅ PyYAML disponible")
            elif dep == 'websocket':
                importlib.import_module('websocket')
                print(f"✅ websocket-client disponible")
            else:
                mod = importlib.import_module(dep)
                version = getattr(mod, '__version__', 'inconnue')
                print(f"✅ {dep} {version}")
        except ImportError:
            print(f"❌ {dep} manquant")
            missing_deps.append(dep)
    
    return len(missing_deps) == 0

def main():
    """Diagnostic complet"""
    print("🔍 DIAGNOSTIC COMPLET AI-TRADER-V2")
    print("=" * 50)
    
    checks = [
        check_python_version,
        check_pip,
        check_project_structure,
        check_dependencies
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"💥 Erreur lors du diagnostic: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DIAGNOSTIC")
    print("=" * 50)
    
    all_good = all(results)
    
    if all_good:
        print("🎉 ENVIRONNEMENT PRÊT !")
        print("🚀 Lancez votre agent avec: python3 -m ai_trader.main")
    else:
        print("⚠️ PROBLÈMES DÉTECTÉS")
        print("💡 Solutions recommandées:")
        print("   1. Lancez: python3 install_dependencies.py")
        print("   2. Vérifiez la structure du projet")
        print("   3. Installez les dépendances manquantes")
    
    return all_good

if __name__ == "__main__":
    main()
