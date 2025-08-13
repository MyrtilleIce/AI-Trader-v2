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
   d'environnement suivantes contrôlent la sécurité et les options temps réel :

   | Variable | Par défaut | Description |
   | --- | --- | --- |
   | `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` | `admin` / `change_me` | Identifiants si `DASHBOARD_AUTH=basic` |
   | `DASHBOARD_TOKEN` | vide | Jeton Bearer si `DASHBOARD_AUTH=token` |
   | `DASHBOARD_AUTH` | `disabled` | Mode d'authentification (`disabled`, `basic`, `token`) |
   | `DASHBOARD_PORT` | `5000` | Port HTTP du dashboard |

   Le dashboard supporte WebSocket (`flask_socketio`) ou, en repli, Server Sent
   Events. Aucune dépendance n'est obligatoire ; en cas d'absence les fonctions
   se dégradent proprement.

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
