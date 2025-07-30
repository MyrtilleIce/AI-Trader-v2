#!/usr/bin/env python3
"""
Script d'installation robuste pour AI-Trader-v2
Compatible Python 3.13 avec gestion d'erreurs avancée
"""

import sys
import subprocess
import importlib
import os
import platform
from pathlib import Path

class DependencyInstaller:
    def __init__(self):
        self.python_version = sys.version_info
        self.platform_system = platform.system()
        self.platform_machine = platform.machine()
        self.failed_packages = []
        self.success_packages = []
        self.pip_cmd = self._get_pip_command()
        
        print(f"🐍 Python Version: {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        print(f"💻 Platform: {self.platform_system} {self.platform_machine}")
        print(f"📦 Pip Command: {' '.join(self.pip_cmd)}")
        
    def _get_pip_command(self):
        """Détecter la meilleure commande pip"""
        pip_commands = [
            [sys.executable, '-m', 'pip'],
            ['pip3'],
            ['pip']
        ]
        
        for cmd in pip_commands:
            try:
                result = subprocess.run(cmd + ['--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return cmd
            except:
                continue
        
        raise RuntimeError("❌ Aucune commande pip fonctionnelle trouvée")
    
    def upgrade_pip(self):
        """Mettre à jour pip"""
        print("🔄 Mise à jour de pip...")
        try:
            cmd = self.pip_cmd + ['install', '--upgrade', 'pip', 'setuptools', 'wheel']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                print("✅ pip mis à jour avec succès")
                return True
            else:
                print(f"⚠️ Avertissement pip: {result.stderr}")
                return True
        except Exception as e:
            print(f"⚠️ Impossible de mettre à jour pip: {e}")
            return True
    
    def install_package(self, package, alternatives=None):
        """Installer un package avec alternatives"""
        packages_to_try = [package] + (alternatives or [])
        
        for pkg in packages_to_try:
            print(f"📦 Installation de {pkg}...")
            try:
                cmd = self.pip_cmd + ['install', '--upgrade', pkg]
                
                if 'pandas' in pkg.lower():
                    cmd.extend(['--only-binary=pandas', '--no-cache-dir'])
                elif 'numpy' in pkg.lower():
                    cmd.extend(['--only-binary=numpy'])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print(f"✅ {pkg} installé avec succès")
                    self.success_packages.append(pkg)
                    return True
                else:
                    print(f"❌ Échec installation {pkg}: {result.stderr[:200]}...")
                    continue
                    
            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout lors de l'installation de {pkg}")
                continue
            except Exception as e:
                print(f"💥 Erreur inattendue {pkg}: {e}")
                continue
        
        self.failed_packages.append(package)
        return False
    
    def install_core_dependencies(self):
        """Installer les dépendances critiques avec alternatives"""
        print("\n🚀 INSTALLATION DES DÉPENDANCES CRITIQUES")
        print("=" * 50)
        
        critical_packages = [
            ('pandas>=2.2.3', ['pandas>=2.3.0', 'pandas==2.2.3']),
            ('numpy>=1.24.0', ['numpy>=1.26.0', 'numpy==1.24.3']),
            ('pyyaml>=6.0.0', ['pyyaml>=6.0.1', 'pyyaml==6.0']),
            ('flask>=2.3.0', ['flask>=3.0.0', 'flask==2.3.3']),
            ('requests>=2.31.0', ['requests>=2.32.0']),
            ('plotly>=5.15.0', ['plotly>=5.17.0']),
            ('ccxt>=4.0.0', ['ccxt>=4.2.0']),
            ('websocket-client>=1.6.0', ['websocket-client>=1.8.0']),
            ('aiohttp>=3.8.0', ['aiohttp>=3.9.0']),
            ('python-dateutil>=2.8.0', []),
            ('cryptography>=41.0.0', ['cryptography>=42.0.0']),
        ]
        
        for package, alternatives in critical_packages:
            success = self.install_package(package, alternatives)
            if not success:
                print(f"⚠️ Package critique {package} non installé")
    
    def install_optional_dependencies(self):
        """Installer les dépendances optionnelles"""
        print("\n📋 INSTALLATION DES DÉPENDANCES OPTIONNELLES")
        print("=" * 50)
        
        optional_packages = [
            'python-dotenv>=1.0.0',
            'schedule>=1.2.0',
            'pytest>=7.4.0',
            'matplotlib>=3.7.0',
            'scipy>=1.11.0'
        ]
        
        for package in optional_packages:
            self.install_package(package)
    
    def verify_installation(self):
        """Vérifier que les modules critiques s'importent"""
        print("\n🔍 VÉRIFICATION DE L'INSTALLATION")
        print("=" * 50)
        
        critical_modules = [
            ('pandas', 'pd'),
            ('numpy', 'np'),
            ('yaml', None),
            ('flask', None),
            ('requests', None),
            ('plotly', None),
            ('ccxt', None),
            ('websocket', None),
            ('aiohttp', None),
            ('cryptography', None)
        ]
        
        verification_failed = []
        
        for module_name, alias in critical_modules:
            try:
                if alias:
                    exec(f"import {module_name} as {alias}")
                    try:
                        version = eval(f"{alias}.__version__")
                        print(f"✅ {module_name} {version}")
                    except:
                        print(f"✅ {module_name} (version inconnue)")
                else:
                    importlib.import_module(module_name)
                    try:
                        mod = importlib.import_module(module_name)
                        version = getattr(mod, '__version__', 'version inconnue')
                        print(f"✅ {module_name} {version}")
                    except:
                        print(f"✅ {module_name}")
            except ImportError as e:
                print(f"❌ {module_name}: {e}")
                verification_failed.append(module_name)
            except Exception as e:
                print(f"⚠️ {module_name}: Erreur de vérification {e}")
        
        return len(verification_failed) == 0
    
    def create_fixed_requirements(self):
        """Créer un fichier requirements.txt corrigé"""
        requirements_content = """# AI-Trader-v2 Dependencies - Python 3.13 Compatible - Auto-generated
pandas>=2.2.3
numpy>=1.24.0
flask>=2.3.0
requests>=2.31.0
pyyaml>=6.0.0
plotly>=5.15.0
ccxt>=4.0.0
websocket-client>=1.6.0
aiohttp>=3.8.0
python-dateutil>=2.8.0
cryptography>=41.0.0
python-dotenv>=1.0.0
schedule>=1.2.0
pytz>=2023.3
urllib3>=2.0.0
"""
        
        try:
            with open('requirements_fixed.txt', 'w') as f:
                f.write(requirements_content)
            print("✅ Fichier requirements_fixed.txt créé")
            
            if os.path.exists('requirements.txt'):
                os.rename('requirements.txt', 'requirements_old.txt')
                print("📋 Ancien requirements.txt sauvé comme requirements_old.txt")
            
            os.rename('requirements_fixed.txt', 'requirements.txt')
            print("✅ Nouveau requirements.txt créé")
            
        except Exception as e:
            print(f"⚠️ Impossible de créer requirements.txt: {e}")
    
    def install_all(self):
        """Processus d'installation complète"""
        print("🚀 INSTALLATION COMPLÈTE AI-TRADER-V2")
        print("=" * 60)
        
        self.upgrade_pip()
        self.create_fixed_requirements()
        self.install_core_dependencies()
        self.install_optional_dependencies()
        success = self.verify_installation()
        
        print("\n" + "=" * 60)
        print("📊 RAPPORT D'INSTALLATION")
        print("=" * 60)
        
        print(f"✅ Packages installés avec succès: {len(self.success_packages)}")
        for pkg in self.success_packages[:10]:
            print(f"   -  {pkg}")
        if len(self.success_packages) > 10:
            print(f"   -  ... et {len(self.success_packages) - 10} autres")
        
        if self.failed_packages:
            print(f"\n❌ Packages ayant échoué: {len(self.failed_packages)}")
            for pkg in self.failed_packages:
                print(f"   -  {pkg}")
        
        print(f"\n🎯 Vérification des imports: {'✅ SUCCÈS' if success else '❌ ÉCHECS DÉTECTÉS'}")
        
        if success and not self.failed_packages:
            print("\n🎉 INSTALLATION TERMINÉE AVEC SUCCÈS !")
            print("🚀 Vous pouvez maintenant lancer votre agent avec:")
            print("   python3 -m ai_trader.main")
        elif success:
            print("\n⚠️ INSTALLATION PARTIELLEMENT RÉUSSIE")
            print("🚀 Vous pouvez essayer de lancer votre agent avec:")
            print("   python3 -m ai_trader.main")
            print("💡 Certaines fonctionnalités optionnelles pourraient ne pas marcher")
        else:
            print("\n❌ INSTALLATION INCOMPLÈTE")
            print("💡 Essayez les solutions alternatives:")
            print("   1. Installation manuelle: pip3 install pandas>=2.2.3 flask pyyaml requests")
            print("   2. Utilisation d'un environnement virtuel")
            print("   3. Installation via conda: conda install pandas flask pyyaml requests")
        
        return success

def main():
    """Point d'entrée principal"""
    try:
        installer = DependencyInstaller()
        return installer.install_all()
    except KeyboardInterrupt:
        print("\n⏹️ Installation interrompue par l'utilisateur")
        return False
    except Exception as e:
        print(f"\n💥 Erreur critique: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
