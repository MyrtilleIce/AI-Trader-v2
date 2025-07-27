#!/usr/bin/env python3
import os
from pathlib import Path


def find_ai_trader_directory():
    """Search for the AI-Trader-v2 folder on the system."""
    print("🔍 Recherche du dossier AI-Trader-v2...")

    current_dir = os.getcwd()
    print(f"📁 Répertoire courant : {current_dir}")

    print("\n📂 Contenu du répertoire courant :")
    try:
        items = os.listdir('.')
        for item in sorted(items):
            if os.path.isdir(item):
                print(f"   📁 {item}")
            else:
                print(f"   📄 {item}")
        if 'AI-Trader-v2' in items:
            print(f"Le dossier AI-Trader-v2 est dans : {current_dir}")
            return os.path.join(current_dir, 'AI-Trader-v2')
    except PermissionError:
        print("❌ Pas de permission pour lire ce répertoire")

    print("\n🔍 Recherche dans les répertoires parents...")
    parent = Path(current_dir).parent
    for _ in range(3):
        try:
            items = os.listdir(parent)
            if 'AI-Trader-v2' in items:
                found_path = os.path.join(parent, 'AI-Trader-v2')
                print(f"✅ Trouvé dans : {found_path}")
                return found_path
            parent = parent.parent
        except Exception:
            break

    print("\n🔍 Recherche dans les dossiers courants...")
    common_paths = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/"),
    ]

    for path in common_paths:
        try:
            if os.path.exists(path):
                items = os.listdir(path)
                if 'AI-Trader-v2' in items:
                    found_path = os.path.join(path, 'AI-Trader-v2')
                    print(f"✅ Trouvé dans : {found_path}")
                    return found_path
        except Exception:
            continue

    print("❌ Dossier AI-Trader-v2 non trouvé")
    return None


def verify_directory_content(directory_path):
    """Verify that this is the correct AI-Trader-v2 folder."""
    print(f"\n🔍 Vérification du contenu de {directory_path}...")
    try:
        files = os.listdir(directory_path)
        required_files = ['main.py', 'README.md', 'config.yaml']
        ai_trader_folder = 'ai_trader'

        print("📂 Contenu du dossier :")
        for item in sorted(files):
            item_path = os.path.join(directory_path, item)
            if os.path.isdir(item_path):
                print(f"   📁 {item}")
            else:
                print(f"   📄 {item}")

        found_files = [f for f in required_files if f in files]
        print(f"\n✅ Fichiers trouvés : {found_files}")

        has_ai_trader = ai_trader_folder in files
        print(f"✅ Dossier ai_trader : {'Oui' if has_ai_trader else 'Non'}")

        if len(found_files) >= 2 or has_ai_trader:
            print("✅ C'est bien le dossier AI-Trader-v2 !")
            return True
        print("⚠️  Ce n'est peut-être pas le bon dossier")
        return False

    except Exception as e:
        print(f"❌ Erreur lors de la vérification : {e}")
        return False


def create_navigation_commands(directory_path):
    """Print commands to navigate to the folder."""
    print(f"\n📝 Commandes pour naviguer vers le dossier :")
    print(f"cd \"{directory_path}\"")
    print("\nOu en relatif depuis votre position actuelle :")
    current_dir = os.getcwd()
    try:
        rel_path = os.path.relpath(directory_path, current_dir)
        print(f"cd \"{rel_path}\"")
    except Exception:
        print("(chemin relatif non calculable)")


def main():
    print("🚀 DIAGNOSTIC NAVIGATION AI-TRADER-V2")
    print("=" * 50)

    ai_trader_path = find_ai_trader_directory()
    if ai_trader_path:
        if verify_directory_content(ai_trader_path):
            create_navigation_commands(ai_trader_path)

            print(f"\n✅ SOLUTION TROUVÉE !")
            print(f"📁 Votre dossier AI-Trader-v2 se trouve dans :")
            print(f"   {ai_trader_path}")
            print("\n💡 Pour y aller, tapez dans le terminal :")
            print(f"   cd \"{ai_trader_path}\"")
            print("\n🚀 Ensuite vous pourrez lancer :")
            print("   python3 main.py")
        else:
            print("\n⚠️  Dossier trouvé mais contenu suspect")
            print("💡 Vous devriez peut-être re-cloner le dépôt")
    else:
        print("\n❌ DOSSIER NON TROUVÉ")
        print("💡 Solutions :")
        print("   1. Re-cloner le dépôt :")
        print("      git clone https://github.com/MyrtilleIce/AI-Trader-v2.git")
        print("   2. Vérifier dans le Finder/Explorateur de fichiers")
        print("   3. Chercher manuellement le dossier")


if __name__ == "__main__":
    main()
