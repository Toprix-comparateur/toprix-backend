from django.contrib import admin
from .models import BlogPost, BlogSummary, BlogSpecifications, BlogSection, StoreRequest


class BlogSummaryInline(admin.StackedInline):
    model = BlogSummary
    extra = 0


class BlogSpecsInline(admin.StackedInline):
    model = BlogSpecifications
    extra = 0


class BlogSectionInline(admin.StackedInline):
    model = BlogSection
    extra = 0
    ordering = ['order']


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'published_date']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [BlogSummaryInline, BlogSpecsInline, BlogSectionInline]


@admin.register(StoreRequest)
class StoreRequestAdmin(admin.ModelAdmin):
    list_display = ['request_type', 'store_name', 'product_name', 'email', 'status', 'created_at']
    list_filter = ['request_type', 'status']
    list_editable = ['status']
