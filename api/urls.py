"""
============================================
API/URLS.PY — Routes /api/v1/
============================================
"""
from django.urls import path
from . import contact, views

urlpatterns = [
    # Produits
    path('produits/',         views.produits_list,    name='produits-list'),
    path('produits/<slug:slug>/', views.produit_detail, name='produit-detail'),

    # Catégories
    path('categories/',                         views.categories_list,       name='categories-list'),
    path('categories/<str:parent>/<str:sous>/', views.sous_categorie_detail, name='sous-categorie-detail'),
    path('categories/<str:slug>/',              views.categorie_detail,      name='categorie-detail'),

    # Marques
    path('marques/',           views.marques_list,  name='marques-list'),
    path('marques/<str:nom>/', views.marque_detail, name='marque-detail'),

    # Blog
    path('blog/',              views.blog_list,   name='blog-list'),
    path('blog/<slug:slug>/',  views.blog_detail, name='blog-detail'),

    # Boutiques
    path('boutiques/', views.boutiques_list, name='boutiques-list'),

    # Demandes
    path('demandes/', views.demandes_create, name='demandes-create'),

    # Formulaires du site (Contact, Devis) : appelés par le Worker, jamais par un navigateur
    path('contact/', contact.contact_create, name='contact-create'),
    path('devis/',   contact.devis_create,   name='devis-create'),

    # Export complet
    path('export/', views.export_produits, name='export-produits'),
]
