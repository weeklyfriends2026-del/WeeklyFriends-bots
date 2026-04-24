# WeeklyFriends Bot 🎮

Bot Discord pour le serveur **Weekly Friends** — suivi de progression Minecraft et alertes de mises à jour modpacks.

## Fonctionnalités

- 📊 Suivi des quêtes FTB Quests (via FTP)
- ⏱️ Suivi du playtime (via RCON)
- 🆕 Alertes de mises à jour CurseForge
- 3 serveurs Minecraft simultanés

## Commandes

| Commande | Description |
|----------|-------------|
| `/link <pseudo>` | Lier son pseudo Minecraft |
| `/progression` | Voir sa progression |
| `/init` | (Admin) Initialiser la BDD |
| `/sync-now` | (Admin) Forcer une sync |

## Installation

1. Copier `.env.example` en `.env` et remplir les valeurs
2. Installer les dépendances : `pip install -r requirements.txt`
3. Lancer : `python bot.py`

## Variables d'environnement

Voir `.env.example` pour la liste complète.
