# Toprix Backend — API REST Django

Backend Django REST Framework pour le comparateur de produits high-tech **Toprix**.

---

## Stack

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Framework | Django | 5.2.4 |
| API | Django REST Framework | 3.16.1 |
| CORS | django-cors-headers | 4.7.0 |
| Base NoSQL | MongoDB (pymongo) | 4.13.2 |
| Base SQL | SQLite | built-in |
| Static files | WhiteNoise | 6.9.0 |
| Config | python-decouple | 3.8 |

---

## Démarrage rapide

```bash
# 1. Cloner le dépôt
git clone https://github.com/Toprix-comparateur/toprix-backend.git
cd toprix-backend

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Créer le fichier .env
cp .env.example .env
# Renseigner les variables MongoDB et autres clés

# 4. Migrations SQLite
python manage.py migrate

# 5. Créer un superutilisateur (admin Django)
python manage.py createsuperuser

# 6. Lancer le serveur
python manage.py runserver
```

Le serveur est accessible sur `http://localhost:8000/api/v1/`.

---

## Variables d'environnement (`.env`)

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `SECRET_KEY` | Oui | Clé secrète Django |
| `DEBUG` | Non (défaut `False`) | Mode debug |
| `ALLOWED_HOSTS` | Oui | Hôtes autorisés (séparés par virgule) |
| `CORS_ALLOWED_ORIGINS` | Oui | Origines CORS (ex: `https://toprix.net`) |
| `MONGODB_TUNISIANET_URI` | Oui | URI MongoDB Tunisianet |
| `MONGODB_MYTEK_URI` | Oui | URI MongoDB Mytek |
| `MONGODB_SPACENET_URI` | Oui | URI MongoDB Spacenet |
| `MONGODB_COMPARATIF_URI` | Oui | URI MongoDB collection comparatif |
| `EMAIL_HOST_USER` | Non | Email SMTP Serv00 |
| `EMAIL_HOST_PASSWORD` | Non | Mot de passe SMTP |
| `DEFAULT_FROM_EMAIL` | Non | Email expéditeur |

---

## Dépôts

| Projet | URL |
|--------|-----|
| Backend (ce dépôt) | https://github.com/Toprix-comparateur/toprix-backend |
| Frontend Next.js | https://github.com/Toprix-comparateur/toprix |
| Projet original Django | https://github.com/Gas1212/toprix |

---

## Scripts utiles

```bash
# Vérifier la configuration
python manage.py check

# Migrations
python manage.py makemigrations
python manage.py migrate

# Collecter les fichiers statiques (production)
python manage.py collectstatic --noinput

# Lancer en production avec gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 2
```
