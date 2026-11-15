"""
============================================
API/CONTACT.PY — Formulaires Contact et Devis du site
============================================
Endpoints :
  POST /api/v1/contact/  → message du formulaire Contact
  POST /api/v1/devis/    → demande de devis

Le site (Cloudflare Workers) ne peut pas ouvrir de connexion SMTP : il poste ici
en JSON, et c'est ce serveur, sur le même compte serv00 que la boîte
contact@toprix.tn, qui envoie le message.

Ces routes ne sont jamais appelées par un navigateur : elles exigent l'en-tête
X-Contact-Key, secret partagé avec le Worker. Sans CONTACT_API_KEY dans .env,
elles restent fermées.
"""
import hmac
import logging
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from rest_framework import status
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes, throttle_classes,
)
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger('api')

MAX_PRODUITS = 50

# Un nom, un sujet ou un produit n'a aucune raison de contenir une adresse web :
# c'est la signature des robots qui collent leur publicité dans les formulaires.
LIEN = re.compile(r'https?:|www[.]|://|[.](?:com|net|org|ru|xyz|top|info|biz)(?![a-z0-9])', re.IGNORECASE)
MAX_LIENS_MESSAGE = 2


# ============================================
# ACCÈS
# ============================================

class ClePartagee(BasePermission):
    """
    Autorise uniquement les appels portant le secret partagé avec le site.

    Vérifiée avant le plafond de débit : un appel anonyme est refusé sans
    consommer le quota, il ne peut donc pas bloquer le vrai formulaire.
    """

    def has_permission(self, request, view):
        attendue = settings.CONTACT_API_KEY
        if not attendue:
            logger.warning("CONTACT_API_KEY absente de .env : routes contact/devis fermées.")
            return False
        recue = request.headers.get('X-Contact-Key', '')
        return hmac.compare_digest(recue.encode(), attendue.encode())


class PlafondHoraire(SimpleRateThrottle):
    """
    Plafond global, toutes origines confondues.

    Le site appelle depuis les adresses de Cloudflare, pas depuis celles des
    visiteurs : un plafond par IP ne distinguerait personne. Celui-ci borne le
    volume d'e-mails, et la réputation d'envoi du compte serv00, si le
    formulaire est inondé. Le compteur est propre à chaque processus (cache en
    mémoire locale) : la limite réelle peut être un multiple de celle-ci.
    """
    rate = '30/hour'

    def get_cache_key(self, request, view):
        return f'throttle_{self.scope}'


class ContactThrottle(PlafondHoraire):
    scope = 'contact'


class DevisThrottle(PlafondHoraire):
    scope = 'devis'


# ============================================
# VALIDATION
# ============================================

class ChampInvalide(Exception):
    """Un champ du formulaire est absent, trop long ou mal formé."""


def _lire(donnees, cle, max_len, *, requis=True, multiligne=False, sans_lien=True):
    brut = donnees.get(cle, '')
    if brut is None:
        brut = ''
    if not isinstance(brut, str):
        raise ChampInvalide(cle)
    texte = brut.strip()
    if sans_lien and not multiligne and LIEN.search(texte):
        raise ChampInvalide(cle)
    if multiligne and len(re.findall(r'https?://|www[.]', texte, re.IGNORECASE)) > MAX_LIENS_MESSAGE:
        raise ChampInvalide(cle)
    if not multiligne:
        # Pas de saut de ligne dans un champ qui finit dans un en-tête d'e-mail.
        texte = re.sub(r'\s*[\r\n]+\s*', ' ', texte)
    if len(texte) > max_len or (requis and not texte):
        raise ChampInvalide(cle)
    return texte


def _lire_email(donnees):
    # Une adresse e-mail contient légitimement un domaine (.com, .net...).
    adresse = _lire(donnees, 'email', 254, sans_lien=False)
    try:
        validate_email(adresse)
    except ValidationError:
        raise ChampInvalide('email')
    return adresse


def _lire_produits(donnees):
    brut = donnees.get('produits')
    if not isinstance(brut, list) or len(brut) > MAX_PRODUITS:
        raise ChampInvalide('produits')
    lignes = []
    for ligne in brut:
        if not isinstance(ligne, dict):
            raise ChampInvalide('produits')
        nom = _lire(ligne, 'nom', 200, requis=False)
        if not nom:
            continue
        quantite = _lire(ligne, 'quantite', 20, requis=False) or '1'
        lignes.append(f'  • {nom} — {quantite} pcs')
    if not lignes:
        raise ChampInvalide('produits')
    return lignes


def _refus(champ):
    return Response({'erreur': f'Champ invalide : {champ}'}, status=status.HTTP_400_BAD_REQUEST)


def _envoyer(mail, origine):
    try:
        mail.send(fail_silently=False)
    except Exception:
        logger.exception("Échec d'envoi du formulaire %s", origine)
        return Response({'erreur': 'Envoi impossible pour le moment.'},
                        status=status.HTTP_502_BAD_GATEWAY)
    return Response({'message': 'Message envoyé.'})


# ============================================
# CONTACT
# ============================================

@api_view(['POST'])
@authentication_classes([])
@permission_classes([ClePartagee])
@throttle_classes([ContactThrottle])
def contact_create(request):
    """POST /api/v1/contact/"""
    donnees = request.data
    if not isinstance(donnees, dict):
        return _refus('corps')
    try:
        nom = _lire(donnees, 'nom', 100)
        email = _lire_email(donnees)
        sujet = _lire(donnees, 'sujet', 200)
        message = _lire(donnees, 'message', 5000, multiligne=True)
    except ChampInvalide as erreur:
        return _refus(erreur)

    return _envoyer(EmailMessage(
        subject=sujet,
        body=f'Message de {nom} <{email}> :\n\n{message}',
        from_email=settings.CONTACT_EMAIL,
        to=[settings.CONTACT_EMAIL],
        reply_to=[email],
    ), 'contact')


# ============================================
# DEVIS
# ============================================

@api_view(['POST'])
@authentication_classes([])
@permission_classes([ClePartagee])
@throttle_classes([DevisThrottle])
def devis_create(request):
    """POST /api/v1/devis/"""
    donnees = request.data
    if not isinstance(donnees, dict):
        return _refus('corps')
    try:
        nom = _lire(donnees, 'nom', 100)
        prenom = _lire(donnees, 'prenom', 100)
        entreprise = _lire(donnees, 'entreprise', 150, requis=False)
        tel = _lire(donnees, 'tel', 30, requis=False)
        email = _lire_email(donnees)
        lignes = _lire_produits(donnees)
    except ChampInvalide as erreur:
        return _refus(erreur)

    corps = [
        'NOUVELLE DEMANDE DE DEVIS',
        '━━━━━━━━━━━━━━━━━━━━━━━━',
        f'Nom complet : {prenom} {nom}',
        f'Entreprise  : {entreprise}' if entreprise else '',
        f'Téléphone   : {tel or "Non renseigné"}',
        f'Email       : {email}',
        'PRODUITS DEMANDÉS :',
        '━━━━━━━━━━━━━━━━━━━━━━━━',
        *lignes,
    ]
    # Pas de copie (cc) au visiteur : l'adresse est saisie librement, c'était un
    # moyen de faire envoyer du spam à des tiers depuis contact@toprix.tn.
    return _envoyer(EmailMessage(
        subject=f'Demande de devis — {prenom} {nom}' + (f' ({entreprise})' if entreprise else ''),
        body='\n'.join(ligne for ligne in corps if ligne),
        from_email=settings.CONTACT_EMAIL,
        to=[settings.CONTACT_EMAIL],
        reply_to=[email],
    ), 'devis')
