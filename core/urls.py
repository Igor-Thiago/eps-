from django.contrib.auth.views import LogoutView
from django.urls import path

from .forms import MatriculaAuthenticationForm
from .views import (
    AbrirPastaCasoView,
    CasoCreateView,
    CertidaoView,
    CriarAdminView,
    CustomLoginView,
    CasoDetailView,
    CasoListView,
    ConfiguracaoView,
    ForensicCopyView,
    IntegrityReportView,
    RecordingFinishView,
    RecordingStartView,
    RegistroAnalistaView,
    RelatorioDownloadView,
    ScreenshotCaptureView,
    SiteCaptureView,
    home,
)

urlpatterns = [
    path('', home, name='home'),
    path('cadastro/', RegistroAnalistaView.as_view(), name='cadastro'),
    path('configuracoes/', ConfiguracaoView.as_view(), name='configuracao'),
    path('criar-admin/', CriarAdminView.as_view(), name='criar_admin'),
    path(
        'login/',
        CustomLoginView.as_view(
            template_name='core/login.html',
            authentication_form=MatriculaAuthenticationForm,
        ),
        name='login',
    ),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('casos/', CasoListView.as_view(), name='casos'),
    path('casos/novo/', CasoCreateView.as_view(), name='novo_caso'),
    path('casos/<int:pk>/', CasoDetailView.as_view(), name='caso_detalhe'),
    path('casos/<int:pk>/capturar-site/', SiteCaptureView.as_view(), name='capturar_site'),
    path('casos/<int:pk>/gravacao/iniciar/', RecordingStartView.as_view(), name='iniciar_gravacao'),
    path('casos/<int:pk>/gravacao/finalizar/', RecordingFinishView.as_view(), name='finalizar_gravacao'),
    path('casos/<int:pk>/capturas/criar/', ScreenshotCaptureView.as_view(), name='criar_captura'),
    path('casos/<int:pk>/relatorio-integridade/', IntegrityReportView.as_view(), name='relatorio_integridade'),
    path('casos/<int:pk>/certidao/', CertidaoView.as_view(), name='gerar_certidao'),
    path('casos/<int:pk>/copia-forense/', ForensicCopyView.as_view(), name='copia_forense'),
    # Downloads monitorados — desativado do frontend; backend preservado para reativação futura
    # path('casos/<int:pk>/downloads/ativar/', DownloadWatcherStartView.as_view(), name='downloads_ativar'),
    # path('casos/<int:pk>/downloads/desativar/', DownloadWatcherStopView.as_view(), name='downloads_desativar'),
    # path('casos/<int:pk>/downloads/status/', DownloadWatcherStatusView.as_view(), name='downloads_status'),
    path('casos/<int:pk>/abrir-pasta/', AbrirPastaCasoView.as_view(), name='abrir_pasta'),
    path('casos/<int:pk>/relatorios/<int:rel_pk>/download/', RelatorioDownloadView.as_view(), name='relatorio_download'),
]
