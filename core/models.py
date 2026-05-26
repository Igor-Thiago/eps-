import re
from pathlib import Path, PureWindowsPath

from django.contrib.auth.models import AbstractUser
from django.db import models


class ConfiguracaoAnalista(models.Model):
    INTERVALO_CHOICES = [
        (0, 'Desativado'),
        (5, 'A cada 5 segundos'),
        (10, 'A cada 10 segundos'),
        (30, 'A cada 30 segundos'),
    ]

    analista = models.OneToOneField(
        'Analista', on_delete=models.CASCADE, related_name='configuracao'
    )
    cabecalho = models.TextField(
        blank=True,
        default='POLÍCIA CIVIL DO DISTRITO FEDERAL\nCORF — Coordenadoria de Repressão aos Crimes Cibernéticos',
    )
    assinatura_nome = models.CharField(max_length=150, blank=True)
    assinatura_cargo = models.CharField(max_length=150, blank=True)
    assinatura_orgao = models.CharField(max_length=150, blank=True, default='CORF/PCDF')
    logo = models.ImageField(upload_to='configuracoes/logos/', blank=True)
    incluir_info_tecnica = models.BooleanField(default=True)
    intervalo_screenshot = models.IntegerField(default=0, choices=INTERVALO_CHOICES)
    pasta_padrao = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração do Analista'
        verbose_name_plural = 'Configurações dos Analistas'

    def __str__(self):
        return f'Config — {self.analista}'


class Analista(AbstractUser):
    class Role(models.TextChoices):
        ANALISTA = 'ANALISTA', 'Analista'
        ADMIN_PCDF = 'ADMIN_PCDF', 'Administrador PCDF'

    matricula = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ANALISTA)

    REQUIRED_FIELDS = ['matricula', 'email']

    @property
    def is_admin_pcdf(self):
        return self.role == self.Role.ADMIN_PCDF

    class Meta:
        verbose_name = 'Analista'
        verbose_name_plural = 'Analistas'

    def __str__(self):
        return f'{self.get_full_name()} ({self.matricula})'


class Caso(models.Model):
    nome = models.CharField(max_length=255)
    numero_processo = models.CharField(max_length=100, blank=True)
    analista = models.ForeignKey(Analista, on_delete=models.PROTECT, related_name='casos')
    path_pasta = models.CharField(max_length=500)
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Caso'
        verbose_name_plural = 'Casos'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.nome} — {self.analista}'

    @property
    def folder_uri(self):
        if re.match(r'^[a-zA-Z]:[\\/]', self.path_pasta):
            return PureWindowsPath(self.path_pasta).as_uri()
        return Path(self.path_pasta).resolve().as_uri()


class Evidencia(models.Model):
    class Tipo(models.TextChoices):
        SITE = 'SITE', 'Site Preservado'
        VIDEO = 'VIDEO', 'Gravação de Tela'
        SCREENSHOT = 'SCREENSHOT', 'Captura de Tela'
        COPIA_FORENSE = 'COPIA_FORENSE', 'Cópia Forense'
        DOWNLOAD = 'DOWNLOAD', 'Download Monitorado'

    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='evidencias')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    hash_sha256 = models.CharField(max_length=64)
    path_arquivo = models.CharField(max_length=500)
    metadados_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evidência'
        verbose_name_plural = 'Evidências'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.caso.nome} ({self.hash_sha256[:12]}…)'


class AuditLog(models.Model):
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='audit_logs')
    analista = models.ForeignKey(Analista, on_delete=models.PROTECT, related_name='audit_logs')
    acao = models.CharField(max_length=255)
    timestamp_utc = models.DateTimeField()
    hash_bloco_anterior = models.CharField(max_length=64, null=True, blank=True)
    hash_bloco_atual = models.CharField(max_length=64)
    dados_json = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['timestamp_utc']

    def __str__(self):
        return f'[{self.timestamp_utc}] {self.acao} — {self.caso.nome}'


class RelatorioGerado(models.Model):
    class Tipo(models.TextChoices):
        PDF = 'PDF', 'PDF'
        HTML = 'HTML', 'HTML'
        DOCX = 'DOCX', 'Word (.docx)'

    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='relatorios')
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    hash_sha256 = models.CharField(max_length=64)
    path_arquivo = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Relatório Gerado'
        verbose_name_plural = 'Relatórios Gerados'
        ordering = ['-created_at']

    @property
    def nome_arquivo(self):
        return Path(self.path_arquivo).name

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.caso.nome} ({self.created_at:%d/%m/%Y})'
