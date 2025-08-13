#!/usr/bin/env python3
"""
Script de lancement intelligent pour AI-Trader-v2
Avec vérifications préalables et gestion d'erreurs
"""

import sys
import os
import subprocess
import importlib
import argparse
from pathlib import Path

def verify_dependencies():
    """Vérifier les dépendances avant le lancement"""
    required_modules = ['pandas', 'flask', 'yaml', 'requests', 'ccxt']
    
    missing = []
    for module in required_modules:
        try:
            if module == 'yaml':
                importlib.import_module('yaml')
            else:
                importlib.import_module(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print(f"❌ Modules manquants: {', '.join(missing)}")
        print("💡 Lancez d'abord: python3 install_dependencies.py")
        return False
    
    print("✅ Toutes les dépendances sont disponibles")
    return True

def check_agent_structure():
    """Vérifier que l'agent peut être lancé"""
    if not os.path.exists('ai_trader'):
        print("❌ Dossier ai_trader non trouvé")
        print("💡 Assurez-vous d'être dans le bon répertoire")
        return False
    
    if not os.path.exists('ai_trader/main.py'):
        print("❌ ai_trader/main.py non trouvé")
        return False
    
    if not os.path.exists('ai_trader/__init__.py'):
        print("❌ ai_trader/__init__.py non trouvé")
        return False
    
    print("✅ Structure de l'agent correcte")
    return True

def start_agent(enable_dashboard: bool = False) -> bool:
    """Lancer l'agent AI-Trader."""
    print("🚀 LANCEMENT AI-TRADER-V2")
    print("=" * 40)

    if not verify_dependencies():
        return False

    if not check_agent_structure():
        return False

    print("🎯 Démarrage de l'agent...")
    try:
        cmd = [sys.executable, '-m', 'ai_trader.main']
        print(f"Commande: {' '.join(cmd)}")

        env = os.environ.copy()
        if enable_dashboard:
            env["ENABLE_DASHBOARD"] = "true"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env,
        )

        print("✅ Agent démarré !")
        if enable_dashboard:
            port = env.get("DASHBOARD_PORT", "5000")
            print(f"📊 Dashboard disponible sur: http://localhost:{port}")
        print("📱 Contrôle Telegram actif")
        print("⏹️ Appuyez sur Ctrl+C pour arrêter")
        print("-" * 40)

        for line in process.stdout:
            print(line.rstrip())

        return_code = process.wait()

        if return_code == 0:
            print("✅ Agent arrêté proprement")
        else:
            print(f"⚠️ Agent arrêté avec code {return_code}")

        return return_code == 0

    except KeyboardInterrupt:
        print("\n⏹️ Arrêt demandé par l'utilisateur")
        if 'process' in locals():
            process.terminate()
        return True
    except Exception as e:
        print(f"❌ Erreur lors du lancement: {e}")
        print("🔄 Tentative avec méthode alternative...")
        try:
            os.chdir('ai_trader')
            cmd = [sys.executable, 'main.py']
            subprocess.run(cmd)
            return True
        except Exception as e2:
            print(f"❌ Méthode alternative échouée: {e2}")
            return False

def main() -> None:
    """Point d'entrée"""
    parser = argparse.ArgumentParser(description="Lance AI-Trader-v2")
    parser.add_argument(
        "--enable-dashboard",
        action="store_true",
        help="Démarrer le dashboard web",
    )
    args = parser.parse_args()
    success = start_agent(enable_dashboard=args.enable_dashboard)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
