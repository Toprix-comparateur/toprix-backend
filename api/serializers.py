"""
============================================
API/SERIALIZERS.PY — Sérialiseurs DRF
============================================
"""
from django.conf import settings
from rest_framework import serializers
from .models import BlogPost, BlogSummary, BlogSpecifications, BlogSection, StoreRequest


class BlogSummarySerializer(serializers.ModelSerializer):
    avantages = serializers.SerializerMethodField()
    inconvenients = serializers.SerializerMethodField()

    class Meta:
        model = BlogSummary
        fields = ['avantages', 'inconvenients']

    def get_avantages(self, obj):
        return [line.strip() for line in obj.advantages.splitlines() if line.strip()]

    def get_inconvenients(self, obj):
        return [line.strip() for line in obj.disadvantages.splitlines() if line.strip()]


class BlogSpecsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogSpecifications
        fields = ['ram', 'storage', 'processor', 'screen', 'battery', 'audio', 'camera']


class BlogSectionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    banner = serializers.SerializerMethodField()

    class Meta:
        model = BlogSection
        fields = ['order', 'h2_title', 'paragraph', 'image', 'banner', 'banner_url']

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_banner(self, obj):
        if obj.banner:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.banner.url) if request else obj.banner.url
        return None


class BlogPostListSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = ['id', 'slug', 'titre', 'image', 'date_publication', 'resume']

    # Renommage des champs pour correspondre aux types TypeScript du frontend
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'id': str(data['id']),
            'slug': data['slug'],
            'titre': instance.title,
            'image': data['image'],
            'date_publication': instance.published_date.isoformat(),
            'resume': data['resume'],
        }

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

    def get_resume(self, obj):
        # Résumé : texte brut des 300 premiers caractères du contenu
        return obj.content[:300] if obj.content else ''


class BlogPostDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = ['id', 'slug', 'title', 'content', 'image', 'published_date']

    def to_representation(self, instance):
        request = self.context.get('request')

        image_url = None
        if instance.image:
            image_url = request.build_absolute_uri(instance.image.url) if request else instance.image.url

        # Avantages / Inconvénients
        avantages = []
        inconvenients = []
        try:
            avantages = [l.strip() for l in instance.summary.advantages.splitlines() if l.strip()]
            inconvenients = [l.strip() for l in instance.summary.disadvantages.splitlines() if l.strip()]
        except BlogSummary.DoesNotExist:
            pass

        # Spécifications
        specifications = None
        try:
            specs = instance.specs
            specifications = {
                'ram': specs.ram,
                'stockage': specs.storage,
                'processeur': specs.processor,
                'ecran': specs.screen,
                'batterie': specs.battery,
                'audio': specs.audio,
                'camera': specs.camera,
            }
        except BlogSpecifications.DoesNotExist:
            pass

        return {
            'id': str(instance.id),
            'slug': instance.slug,
            'titre': instance.title,
            'contenu': instance.content,
            'image': image_url,
            'date_publication': instance.published_date.isoformat(),
            'resume': instance.content[:300] if instance.content else '',
            'avantages': avantages,
            'inconvenients': inconvenients,
            'specifications': specifications,
        }


class StoreRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreRequest
        fields = [
            'request_type',
            'store_name', 'website',
            'product_name', 'product_url',
            'contact_person', 'email', 'phone',
            'message',
        ]
