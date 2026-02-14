"""
============================================
API/MODELS.PY — Modèles SQLite
Blog + Demandes (repris du projet toprix)
============================================
"""
from django.db import models
from django.utils import timezone


# ============================================
# BLOG
# ============================================

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    image = models.ImageField(upload_to='blog/', blank=True, null=True)
    published_date = models.DateTimeField(default=timezone.now)
    launch_date = models.DateField(null=True, blank=True)
    estimated_price = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ['-published_date']

    def __str__(self):
        return self.title


class BlogSummary(models.Model):
    post = models.OneToOneField(BlogPost, on_delete=models.CASCADE, related_name='summary')
    advantages = models.TextField()
    disadvantages = models.TextField()

    def __str__(self):
        return f"Résumé — {self.post.title}"


class BlogSpecifications(models.Model):
    post = models.OneToOneField(BlogPost, on_delete=models.CASCADE, related_name='specs')
    ram = models.CharField(max_length=100, blank=True, null=True)
    storage = models.CharField(max_length=100, blank=True, null=True)
    processor = models.CharField(max_length=100, blank=True, null=True)
    screen = models.CharField(max_length=100, blank=True, null=True)
    battery = models.CharField(max_length=100, blank=True, null=True)
    audio = models.CharField(max_length=100, blank=True, null=True)
    camera = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Specs — {self.post.title}"


class BlogSection(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='sections')
    order = models.PositiveIntegerField(default=0)
    h2_title = models.CharField(max_length=200, blank=True, null=True)
    paragraph = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='blog/sections/', blank=True, null=True)
    banner = models.ImageField(upload_to='blog/banners/', blank=True, null=True)
    banner_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Section {self.order} — {self.h2_title or 'Sans titre'}"


# ============================================
# DEMANDES (ajouter boutique / produit)
# ============================================

class StoreRequest(models.Model):
    REQUEST_TYPES = [
        ('store', 'Nouvelle Boutique'),
        ('product', 'Nouveau Produit'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]

    request_type = models.CharField(max_length=10, choices=REQUEST_TYPES)
    store_name = models.CharField(max_length=200, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    product_name = models.CharField(max_length=200, blank=True, null=True)
    product_url = models.URLField(blank=True, null=True)
    contact_person = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_type} — {self.store_name or self.product_name}"
