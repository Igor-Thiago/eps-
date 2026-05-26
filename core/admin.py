from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Analista, AuditLog, Caso, Evidencia, RelatorioGerado


@admin.register(Analista)
class AnalistaAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('PCDF', {'fields': ('matricula', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('PCDF', {'fields': ('matricula', 'role')}),
    )
    list_display = ('username', 'get_full_name', 'matricula', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'matricula', 'first_name', 'last_name')


@admin.register(Caso)
class CasoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'numero_processo', 'analista', 'last_accessed_at', 'created_at', 'updated_at')
    list_filter = ('analista',)
    search_fields = ('nome', 'numero_processo')
    readonly_fields = ('last_accessed_at', 'created_at', 'updated_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_admin_pcdf or request.user.is_superuser:
            return qs
        return qs.filter(analista=request.user)


@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'caso', 'hash_sha256', 'created_at')
    list_filter = ('tipo', 'caso__analista')
    search_fields = ('hash_sha256', 'caso__nome')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_admin_pcdf or request.user.is_superuser:
            return qs
        return qs.filter(caso__analista=request.user)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp_utc', 'acao', 'caso', 'analista')
    list_filter = ('analista', 'caso')
    search_fields = ('acao', 'caso__nome')
    readonly_fields = ('timestamp_utc',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_admin_pcdf or request.user.is_superuser:
            return qs
        return qs.filter(caso__analista=request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RelatorioGerado)
class RelatorioGeradoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'caso', 'hash_sha256', 'created_at')
    list_filter = ('tipo', 'caso__analista')
    search_fields = ('hash_sha256', 'caso__nome')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_admin_pcdf or request.user.is_superuser:
            return qs
        return qs.filter(caso__analista=request.user)
