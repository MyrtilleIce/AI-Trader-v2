# 🚀 Guide d'Installation AI-Trader-v2

## Installation Automatique (Recommandée)

1. **Diagnostic de l'environnement :**
   ```bash
   python3 diagnostic_environment.py
   ```

2. **Installation des dépendances :**
   ```bash
   python3 install_dependencies.py
   ```

3. **Lancement de l'agent :**
   ```bash
   python3 start_agent.py --enable-dashboard  # optionnel
   ```

   Utilisez `--enable-dashboard` pour activer l'interface web. Les variables
   d'environnement `DASHBOARD_USERNAME` et `DASHBOARD_PASSWORD` peuvent être
   définies pour protéger l'accès.

## Vérification Rapide

- **Dashboard Web :** http://localhost:5000 (si activé)
- **Contrôle Telegram :** Commandes /start, /stop, /status
- **Logs :** Affichés dans le terminal

## Solutions aux Problèmes Courants

### Erreur "No module named..."
```bash
python3 install_dependencies.py
```

### Port 5000 occupé
Le script trouve automatiquement un port libre (5001, 5002, etc.)

### Problèmes de compilation pandas
Le script utilise des binaires pré-compilés pour éviter la compilation

## Structure des Fichiers Créés

- `install_dependencies.py` - Installation intelligente
- `diagnostic_environment.py` - Diagnostic complet
- `start_agent.py` - Lancement robuste
- `requirements.txt` - Dépendances mises à jour
- `requirements_old.txt` - Sauvegarde de l'ancien

## Support

En cas de problème, lancez le diagnostic complet :
```bash
python3 diagnostic_environment.py
```
