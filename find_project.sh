#!/bin/bash

echo "🔍 Recherche du dossier AI-Trader-v2..."
echo "📁 Répertoire courant : $(pwd)"
echo ""

echo "📂 Contenu du répertoire courant :"
ls -la

echo ""
echo "🔍 Recherche dans les dossiers parents et courants..."

find_ai_trader() {
    local search_dir="$1"
    if [ -d "$search_dir/AI-Trader-v2" ]; then
        echo "✅ Trouvé dans : $search_dir/AI-Trader-v2"
        echo "💡 Pour y aller : cd '$search_dir/AI-Trader-v2'"
        return 0
    fi
    return 1
}

find_ai_trader "." && exit 0
find_ai_trader ".." && exit 0
find_ai_trader "$HOME/Downloads" && exit 0
find_ai_trader "$HOME/Desktop" && exit 0
find_ai_trader "$HOME/Documents" && exit 0
find_ai_trader "$HOME" && exit 0

echo "❌ Dossier AI-Trader-v2 non trouvé"
echo "💡 Re-clonez le dépôt :"
echo " git clone https://github.com/MyrtilleIce/AI-Trader-v2.git"
echo " cd AI-Trader-v2"
