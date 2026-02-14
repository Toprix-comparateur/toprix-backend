# Guide de Déploiement — Toprix Backend

---

## Cible de déploiement

| Composant | Plateforme | URL |
|-----------|-----------|-----|
| **Backend API** | **Serv00** | `https://api.toprix.net` |
| **Frontend** | Vercel | `https://toprix.net` |

---

## Structure sur Serv00

```
/home/oven-cleaner/
├── domains/
│   └── api.toprix.net/
│       ├── public_python/       ← Dossier de l'application Python
│       │   ├── (fichiers du projet)
│       │   └── passenger_wsgi.py
│       └── public_html/         ← Dossier public (non utilisé)
```

---

## Déploiement initial sur Serv00

### 1. Cloner le dépôt

```bash
# Sur Serv00 via SSH
ssh oven-cleaner@repo3.serv00.com

cd ~/domains/api.toprix.net/
git clone https://github.com/Toprix-comparateur/toprix-backend.git public_python
cd public_python
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt --user
```

### 3. Créer le fichier `.env`

```bash
cp .env.example .env
nano .env
# Renseigner toutes les variables (MongoDB URIs, SECRET_KEY, etc.)
```

Variables minimales pour la production :
```bash
SECRET_KEY=votre-cle-secrete-longue-et-aleatoire
DEBUG=False
ALLOWED_HOSTS=api.toprix.net,www.api.toprix.net

CORS_ALLOWED_ORIGINS=https://toprix.net,https://www.toprix.net

MONGODB_TUNISIANET_URI=mongodb+srv://...
MONGODB_MYTEK_URI=mongodb+srv://...
MONGODB_SPACENET_URI=mongodb+srv://...
MONGODB_COMPARATIF_URI=mongodb+srv://...

EMAIL_HOST=mail3.serv00.com
EMAIL_HOST_USER=noreply@toprix.net
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=noreply@toprix.net
```

### 4. Migrations et fichiers statiques

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. Créer le superutilisateur admin

```bash
python manage.py createsuperuser
```

### 6. Fichier `passenger_wsgi.py` (Serv00)

Serv00 utilise Phusion Passenger. Créer à la racine du dossier :

```python
# passenger_wsgi.py
import sys
import os

# Ajouter le dossier projet au path
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

from core.wsgi import application
```

---

## Déploiement des mises à jour

```bash
# Sur Serv00
cd ~/domains/api.toprix.net/public_python

# Récupérer les changements
git pull origin main

# Installer les nouvelles dépendances (si requirements.txt a changé)
pip install -r requirements.txt --user

# Appliquer les migrations
python manage.py migrate

# Collecter les statiques
python manage.py collectstatic --noinput

# Redémarrer l'application Passenger
touch tmp/restart.txt
```

---

## Configuration DNS

Pour faire pointer `api.toprix.net` vers Serv00 :

```
CNAME  api  repo3.serv00.com
```

Ou avec un enregistrement A (IP de Serv00).

---

## CORS — Configuration

Le backend autorise les requêtes depuis le frontend dans `.env` :

```bash
CORS_ALLOWED_ORIGINS=https://toprix.net,https://www.toprix.net,http://localhost:3000
```

En production, supprimer `http://localhost:3000`.

---

## Migration du blog depuis l'ancien projet

Pour copier les articles de blog de l'ancien `toprix` vers le nouveau backend :

```bash
# Sur la machine locale
cd /d/github/toprix

# Exporter les données blog
python manage.py dumpdata comparer.BlogPost comparer.BlogSummary comparer.BlogSpecifications comparer.BlogSection --indent 2 > blog_export.json

# Transférer vers Serv00
scp blog_export.json oven-cleaner@repo3.serv00.com:~/domains/api.toprix.net/public_python/

# Sur Serv00 — importer dans le nouveau projet
cd ~/domains/api.toprix.net/public_python
python manage.py loaddata blog_export.json
```

> **Note :** Les modèles sont identiques donc le `loaddata` fonctionne directement.

---

## Checklist avant mise en production

### Sécurité
- [ ] `DEBUG=False` dans `.env`
- [ ] `SECRET_KEY` unique et longue (50+ caractères)
- [ ] `ALLOWED_HOSTS` liste exacte des domaines
- [ ] `CORS_ALLOWED_ORIGINS` sans `localhost`

### Base de données
- [ ] `python manage.py migrate` exécuté
- [ ] Superutilisateur créé
- [ ] Blog importé depuis l'ancien projet

### MongoDB
- [ ] Toutes les URI MongoDB renseignées
- [ ] Connexions testées (ping MongoDB)

### Statiques
- [ ] `collectstatic` exécuté
- [ ] WhiteNoise configuré (déjà en settings)

### Fonctionnel
- [ ] `GET /api/v1/produits/?q=test` retourne des résultats
- [ ] `GET /api/v1/blog/` retourne les articles
- [ ] `GET /api/v1/boutiques/` retourne les 3 boutiques
- [ ] Admin Django accessible sur `/admin/`

---

## Surveiller les logs

```bash
# Logs Django
tail -f ~/domains/api.toprix.net/public_python/logs/django.log

# Logs API
tail -f ~/domains/api.toprix.net/public_python/logs/api.log
```

---

## Rollback

```bash
# Lister les commits
git log --oneline -10

# Revenir à un commit précédent
git checkout <commit-hash>
touch tmp/restart.txt
```
