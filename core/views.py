import os
import subprocess
import sys
from pathlib import Path

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.contrib.auth.views import LoginView
from django.views.generic import DetailView, FormView, ListView

from django.shortcuts import render
from .forms import AnalistaRegistrationForm, CasoForm, ConfiguracaoForm, CriarAdminForm, SiteCaptureForm
from .models import Analista, Caso, ConfiguracaoAnalista, Evidencia, RelatorioGerado
from .services.audit_logger import AuditLogger
from .services.case_folder_service import CaseFolderError, CaseFolderService
from .services.forensic_report_service import ForensicReportError, ForensicReportService
from django.conf import settings

from .services.download_watcher_service import DownloadWatcherService
from .services.forensic_copy_service import ForensicCopyError, ForensicCopyService
from .services.certidao_service import CertidaoError, CertidaoService
from .services.integrity_report_service import IntegrityReportError, IntegrityReportService
from .services.screen_recording_service import ScreenRecordingError, ScreenRecordingService
from .services.screenshot_service import ScreenshotError, ScreenshotService
from .services.site_preserver import SitePreservationError, SitePreserver


def _get_or_create_config(user):
    config, _ = ConfiguracaoAnalista.objects.get_or_create(
        analista=user,
        defaults={
            'assinatura_nome': user.get_full_name(),
            'assinatura_orgao': 'CORF/PCDF',
        },
    )
    return config


class ConfiguracaoView(LoginRequiredMixin, View):
    template_name = 'core/configuracao.html'

    def get(self, request):
        config = _get_or_create_config(request.user)
        form = ConfiguracaoForm(instance=config)
        tab = request.GET.get('tab', 'relatorios')
        return render(request, self.template_name, {'form': form, 'config': config, 'tab': tab})

    def post(self, request):
        config = _get_or_create_config(request.user)
        tab = request.POST.get('tab', 'relatorios')
        form = ConfiguracaoForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações salvas com sucesso.')
            return redirect(f'{reverse("configuracao")}?tab={tab}')
        return render(request, self.template_name, {'form': form, 'config': config, 'tab': tab})


def home(request):
    if request.user.is_authenticated:
        return redirect('casos')
    return redirect('login')


def _admin_existe():
    return Analista.objects.filter(role=Analista.Role.ADMIN_PCDF).exists()


class CustomLoginView(LoginView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['setup_needed'] = not _admin_existe()
        return ctx


class CriarAdminView(FormView):
    template_name = 'core/criar_admin.html'
    form_class = CriarAdminForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated or _admin_existe():
            return redirect('casos')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        admin = form.save()
        login(self.request, admin)
        messages.success(self.request, 'Conta de administrador criada com sucesso.')
        return redirect('casos')


class RegistroAnalistaView(FormView):
    template_name = 'core/cadastro.html'
    form_class = AnalistaRegistrationForm
    success_url = '/casos/'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not (
            request.user.is_superuser or request.user.is_admin_pcdf
        ):
            raise PermissionDenied('Apenas administradores podem cadastrar novos analistas.')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        analista = form.save()
        if self.request.user.is_authenticated:
            messages.success(
                self.request,
                f'Analista {analista.get_full_name()} cadastrado com sucesso.',
            )
            return redirect('cadastro')
        login(self.request, analista)
        return super().form_valid(form)


class CasoQuerysetMixin(LoginRequiredMixin):
    model = Caso

    def get_queryset(self):
        queryset = Caso.objects.select_related('analista')
        user = self.request.user
        if user.is_superuser or user.is_admin_pcdf:
            return queryset
        return queryset.filter(analista=user)


class CasoListView(CasoQuerysetMixin, ListView):
    template_name = 'core/casos.html'
    context_object_name = 'casos'


class CasoCreateView(LoginRequiredMixin, FormView):
    template_name = 'core/novo_caso.html'
    form_class = CasoForm

    def form_valid(self, form):
        try:
            case_path = CaseFolderService.create_case_folder(
                form.cleaned_data['nome'],
                form.cleaned_data['pasta_base'] or None,
            )
        except CaseFolderError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        caso = form.save(self.request.user, case_path)
        AuditLogger.log(
            caso,
            self.request.user,
            'CASO_CRIADO',
            {'path_pasta': caso.path_pasta, 'numero_processo': caso.numero_processo},
        )
        messages.success(self.request, 'Caso criado com estrutura de pastas completa.')
        return redirect('caso_detalhe', pk=caso.pk)


class CasoDetailView(CasoQuerysetMixin, DetailView):
    template_name = 'core/caso_detalhe.html'
    context_object_name = 'caso'

    def get_object(self, queryset=None):
        caso = get_object_or_404(Caso.objects.select_related('analista'), pk=self.kwargs['pk'])
        user = self.request.user
        if not (user.is_superuser or user.is_admin_pcdf or caso.analista_id == user.id):
            raise PermissionDenied('Voce nao tem permissao para acessar este caso.')
        Caso.objects.filter(pk=caso.pk).update(last_accessed_at=timezone.now())
        caso.refresh_from_db(fields=['last_accessed_at'])
        return caso

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['capture_form'] = SiteCaptureForm()
        context['evidencias_site'] = self.object.evidencias.filter(tipo=Evidencia.Tipo.SITE)
        context['evidencias_video'] = self.object.evidencias.filter(tipo=Evidencia.Tipo.VIDEO)
        context['evidencias_screenshot'] = self.object.evidencias.filter(tipo=Evidencia.Tipo.SCREENSHOT)
        context['evidencias_forense'] = self.object.evidencias.filter(tipo=Evidencia.Tipo.COPIA_FORENSE)
        context['evidencias_download'] = self.object.evidencias.filter(tipo=Evidencia.Tipo.DOWNLOAD)
        context['relatorios_pdf'] = self.object.relatorios.filter(tipo=RelatorioGerado.Tipo.PDF)
        config = _get_or_create_config(self.request.user)
        context['intervalo_screenshot_config'] = config.intervalo_screenshot
        return context


class CasoAccessMixin(CasoQuerysetMixin):
    permission_message = 'Voce nao tem permissao para acessar este caso.'

    def get_caso(self, pk):
        caso = get_object_or_404(Caso.objects.select_related('analista'), pk=pk)
        user = self.request.user
        if not (user.is_superuser or user.is_admin_pcdf or caso.analista_id == user.id):
            raise PermissionDenied(self.permission_message)
        return caso


class RecordingStartView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para iniciar gravacao neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)
        recording_id = request.POST.get('recording_id', '').strip()
        if not recording_id:
            return JsonResponse({'error': 'Identificador da gravacao ausente.'}, status=400)

        metadata = {
            'recording_id': recording_id,
            'microphone_label': request.POST.get('microphone_label', ''),
            'system_audio_requested': request.POST.get('system_audio_requested') == 'true',
            'started_at_utc': timezone.now().isoformat(),
        }
        AuditLogger.log(caso, request.user, 'GRAVACAO_INICIADA', metadata)
        return JsonResponse({'recording_id': recording_id, 'started_at_utc': metadata['started_at_utc']})


class RecordingFinishView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para finalizar gravacao neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)
        metadata = {
            'recording_id': request.POST.get('recording_id', ''),
            'started_at_utc': request.POST.get('started_at_utc', ''),
            'duration_ms': request.POST.get('duration_ms', ''),
            'microphone_label': request.POST.get('microphone_label', ''),
            'system_audio_requested': request.POST.get('system_audio_requested') == 'true',
            'mime_type': request.POST.get('mime_type', ''),
        }

        try:
            result = ScreenRecordingService().save_recording(caso, request.FILES.get('video'), metadata)
        except ScreenRecordingError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        evidencia = Evidencia.objects.create(
            caso=caso,
            tipo=Evidencia.Tipo.VIDEO,
            hash_sha256=result.hash_sha256,
            path_arquivo=str(result.path),
            metadados_json=result.metadata,
        )
        linked_screenshots = [
            screenshot
            for screenshot in caso.evidencias.filter(tipo=Evidencia.Tipo.SCREENSHOT)
            if screenshot.metadados_json.get('linked_recording_id') == result.metadata.get('recording_id')
        ]
        if linked_screenshots:
            evidencia.metadados_json.update(
                {
                    'linked_screenshot_ids': [screenshot.id for screenshot in linked_screenshots],
                    'linked_screenshot_paths': [screenshot.path_arquivo for screenshot in linked_screenshots],
                }
            )
            evidencia.save(update_fields=['metadados_json'])
        AuditLogger.log(
            caso,
            request.user,
            'GRAVACAO_FINALIZADA',
            {
                'recording_id': result.metadata.get('recording_id'),
                'evidencia_id': evidencia.id,
                'path_arquivo': str(result.path),
                'hash_sha256': result.hash_sha256,
                'size_bytes': result.size_bytes,
                'duration_ms': result.metadata.get('duration_ms'),
            },
        )
        return JsonResponse(
            {
                'evidencia_id': evidencia.id,
                'path_arquivo': str(result.path),
                'hash_sha256': result.hash_sha256,
                'recorded_at_utc': result.recorded_at_utc,
            }
        )


class ScreenshotCaptureView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para capturar tela neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)
        metadata = {
            'screenshot_id': request.POST.get('screenshot_id', ''),
            'capture_mode': request.POST.get('capture_mode', 'manual'),
            'linked_recording_id': request.POST.get('linked_recording_id', ''),
            'periodic_interval_seconds': request.POST.get('periodic_interval_seconds', ''),
        }

        try:
            result = ScreenshotService().save_screenshot(caso, request.FILES.get('image'), metadata)
        except ScreenshotError as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        evidencia = Evidencia.objects.create(
            caso=caso,
            tipo=Evidencia.Tipo.SCREENSHOT,
            hash_sha256=result.hash_sha256,
            path_arquivo=str(result.path),
            metadados_json=result.metadata,
        )

        response_data = {
            'evidencia_id': evidencia.id,
            'path_arquivo': str(result.path),
            'hash_sha256': result.hash_sha256,
            'captured_at_utc': result.captured_at_utc,
        }
        linked_recording_id = result.metadata.get('linked_recording_id')

        if not linked_recording_id:
            try:
                report_result = ScreenshotService().generate_individual_report(
                    caso,
                    evidencia,
                    sequence=caso.relatorios.filter(tipo=RelatorioGerado.Tipo.PDF).count() + 1,
                )
            except ScreenshotError as exc:
                response_data['report_error'] = str(exc)
            else:
                RelatorioGerado.objects.create(
                    caso=caso,
                    tipo=RelatorioGerado.Tipo.PDF,
                    hash_sha256=report_result.hash_sha256,
                    path_arquivo=str(report_result.pdf_path),
                )
                evidencia.metadados_json.update(
                    {
                        'report_number': report_result.report_number,
                        'report_pdf_path': str(report_result.pdf_path),
                        'report_hash_sha256': report_result.hash_sha256,
                        'report_generated_at_utc': report_result.generated_at_utc,
                    }
                )
                evidencia.save(update_fields=['metadados_json'])
                response_data.update(
                    {
                        'report_number': report_result.report_number,
                        'report_pdf_path': str(report_result.pdf_path),
                        'report_hash_sha256': report_result.hash_sha256,
                    }
                )

        AuditLogger.log(
            caso,
            request.user,
            'CAPTURA_TELA_REALIZADA',
            {
                'evidencia_id': evidencia.id,
                'path_arquivo': str(result.path),
                'hash_sha256': result.hash_sha256,
                'capture_mode': result.metadata.get('capture_mode'),
                'linked_recording_id': linked_recording_id,
            },
        )
        return JsonResponse(response_data)


class SiteCaptureView(CasoQuerysetMixin, View):
    def post(self, request, pk):
        caso = get_object_or_404(Caso.objects.select_related('analista'), pk=pk)
        user = request.user
        if not (user.is_superuser or user.is_admin_pcdf or caso.analista_id == user.id):
            raise PermissionDenied('Voce nao tem permissao para preservar sites neste caso.')

        form = SiteCaptureForm(request.POST)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect('caso_detalhe', pk=caso.pk)

        try:
            result = SitePreserver().preserve(form.cleaned_data['url'], caso.path_pasta)
        except SitePreservationError as exc:
            messages.error(request, str(exc))
            return redirect('caso_detalhe', pk=caso.pk)

        evidencia = Evidencia.objects.create(
            caso=caso,
            tipo=Evidencia.Tipo.SITE,
            hash_sha256=result.hash_sha256,
            path_arquivo=str(result.mhtml_path),
            metadados_json={
                'url': result.url,
                'final_url': result.final_url,
                'domain': result.domain,
                'status': result.status,
                'title': result.title,
                'html_path': str(result.html_path),
                'screenshot_path': str(result.screenshot_path),
                'mhtml_path': str(result.mhtml_path),
                'metadata_path': str(result.metadata_path),
                'output_dir': str(result.output_dir),
                'technical_metadata': result.technical_metadata,
            },
        )

        try:
            config = _get_or_create_config(request.user)
            report_result = ForensicReportService().generate_site_report(
                caso=caso,
                evidencia=evidencia,
                preservation_result=result,
                sequence=caso.relatorios.filter(tipo=RelatorioGerado.Tipo.PDF).count() + 1,
                config=config,
            )
        except ForensicReportError as exc:
            messages.warning(request, str(exc))
        else:
            RelatorioGerado.objects.create(
                caso=caso,
                tipo=RelatorioGerado.Tipo.PDF,
                hash_sha256=report_result.hash_sha256,
                path_arquivo=str(report_result.pdf_path),
            )
            evidencia.metadados_json.update(
                {
                    'report_number': report_result.report_number,
                    'report_pdf_path': str(report_result.pdf_path),
                    'report_hash_sha256': report_result.hash_sha256,
                    'report_generated_at_utc': report_result.generated_at_utc,
                    'artifact_hashes': report_result.artifact_hashes,
                }
            )
            evidencia.save(update_fields=['metadados_json'])

        AuditLogger.log(
            caso,
            request.user,
            'SITE_PRESERVADO',
            {'url': result.url, 'evidencia_id': evidencia.id, 'hash_sha256': result.hash_sha256},
        )
        messages.success(request, 'Site preservado com sucesso.')
        return redirect(reverse('caso_detalhe', kwargs={'pk': caso.pk}))


class IntegrityReportView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para gerar relatorio de integridade neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)
        try:
            result = IntegrityReportService().generate(caso, request.user)
        except IntegrityReportError as exc:
            messages.error(request, str(exc))
            return redirect('caso_detalhe', pk=caso.pk)

        relatorio = RelatorioGerado.objects.create(
            caso=caso,
            tipo=RelatorioGerado.Tipo.PDF,
            hash_sha256=result.pdf_hash_sha256,
            path_arquivo=str(result.pdf_path),
        )
        AuditLogger.log(
            caso,
            request.user,
            'RELATORIO_INTEGRIDADE_GERADO',
            {
                'report_number': result.report_number,
                'chain_valid': result.chain_valid,
                'total_logs': result.total_logs,
                'pdf_path': str(result.pdf_path),
                'html_path': str(result.html_path),
                'pdf_hash_sha256': result.pdf_hash_sha256,
                'html_hash_sha256': result.html_hash_sha256,
                'software_hash': result.software_hash,
            },
        )
        status = 'INTEGRA' if result.chain_valid else 'VIOLADA'
        messages.success(
            request,
            f'Relatorio de integridade gerado. Cadeia: {status}. Arquivo: {result.pdf_path.name}',
        )

        # Gera certidão automaticamente junto com o relatório de integridade
        config = _get_or_create_config(request.user)
        try:
            certidao = CertidaoService().generate(caso, request.user, config)
            RelatorioGerado.objects.create(
                caso=caso,
                tipo=RelatorioGerado.Tipo.DOCX,
                hash_sha256=certidao.hash_sha256,
                path_arquivo=str(certidao.docx_path),
            )
            messages.success(request, f'Certidão gerada: {certidao.docx_path.name}')
        except CertidaoError as exc:
            messages.warning(request, f'Relatório gerado, mas certidão falhou: {exc}')

        return redirect('relatorio_download', pk=caso.pk, rel_pk=relatorio.pk)


class CertidaoView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para gerar certidao neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)
        config = _get_or_create_config(request.user)
        try:
            result = CertidaoService().generate(caso, request.user, config)
        except CertidaoError as exc:
            messages.error(request, str(exc))
            return redirect('caso_detalhe', pk=caso.pk)

        relatorio = RelatorioGerado.objects.create(
            caso=caso,
            tipo=RelatorioGerado.Tipo.DOCX,
            hash_sha256=result.hash_sha256,
            path_arquivo=str(result.docx_path),
        )
        AuditLogger.log(
            caso,
            request.user,
            'CERTIDAO_GERADA',
            {'docx_path': str(result.docx_path), 'hash_sha256': result.hash_sha256},
        )
        messages.success(request, f'Certidão gerada: {result.docx_path.name}')
        return redirect('relatorio_download', pk=caso.pk, rel_pk=relatorio.pk)


class ForensicCopyView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para realizar copia forense neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)
        uploaded_files = request.FILES.getlist('arquivos')
        if not uploaded_files:
            messages.error(request, 'Nenhum arquivo selecionado.')
            return redirect('caso_detalhe', pk=caso.pk)

        try:
            result = ForensicCopyService().copy(caso, uploaded_files)
        except ForensicCopyError as exc:
            messages.error(request, str(exc))
            return redirect('caso_detalhe', pk=caso.pk)

        for file_result in result.files:
            Evidencia.objects.create(
                caso=caso,
                tipo=Evidencia.Tipo.COPIA_FORENSE,
                hash_sha256=file_result.hash_sha256,
                path_arquivo=str(file_result.path),
                metadados_json={
                    'original_name': file_result.original_name,
                    'filename': file_result.filename,
                    'size_bytes': file_result.size_bytes,
                    'copied_at_utc': result.copied_at_utc,
                    'exif': file_result.exif,
                    'zip_path': str(result.zip_path),
                    'zip_hash_sha256': result.zip_hash_sha256,
                    'report_pdf_path': str(result.pdf_path),
                    'report_pdf_hash_sha256': result.pdf_hash_sha256,
                },
            )

        RelatorioGerado.objects.create(
            caso=caso,
            tipo=RelatorioGerado.Tipo.PDF,
            hash_sha256=result.pdf_hash_sha256,
            path_arquivo=str(result.pdf_path),
        )

        AuditLogger.log(
            caso,
            request.user,
            'COPIA_FORENSE_REALIZADA',
            {
                'total_arquivos': len(result.files),
                'arquivos': [
                    {'nome': fr.original_name, 'hash_sha256': fr.hash_sha256, 'size_bytes': fr.size_bytes}
                    for fr in result.files
                ],
                'zip_path': str(result.zip_path),
                'zip_hash_sha256': result.zip_hash_sha256,
                'report_pdf_path': str(result.pdf_path),
                'report_pdf_hash_sha256': result.pdf_hash_sha256,
            },
        )

        messages.success(
            request,
            f'{len(result.files)} arquivo(s) copiado(s) com sucesso. Relatorio: {result.pdf_path.name}',
        )
        return redirect('caso_detalhe', pk=caso.pk)


class DownloadWatcherStartView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para monitorar downloads neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)

        if DownloadWatcherService.is_active(caso.pk):
            return JsonResponse({
                'status': 'ativo',
                'watch_folder': DownloadWatcherService.watch_folder(caso.pk),
            })

        watch_folder = request.POST.get('watch_folder', '').strip() or settings.WATCH_FOLDER
        try:
            DownloadWatcherService.start(caso.pk, watch_folder, caso.path_pasta, request.user.pk)
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)

        AuditLogger.log(caso, request.user, 'MONITORAMENTO_DOWNLOADS_ATIVADO', {
            'watch_folder': watch_folder,
        })
        return JsonResponse({'status': 'ativo', 'watch_folder': watch_folder})


class DownloadWatcherStopView(CasoAccessMixin, View):
    permission_message = 'Voce nao tem permissao para desativar monitoramento neste caso.'

    def post(self, request, pk):
        caso = self.get_caso(pk)

        if not DownloadWatcherService.is_active(caso.pk):
            return JsonResponse({'status': 'inativo'})

        DownloadWatcherService.stop(caso.pk)
        AuditLogger.log(caso, request.user, 'MONITORAMENTO_DOWNLOADS_DESATIVADO', {})
        return JsonResponse({'status': 'inativo'})


class DownloadWatcherStatusView(CasoAccessMixin, View):
    def get(self, request, pk):
        caso = self.get_caso(pk)
        active = DownloadWatcherService.is_active(caso.pk)
        result = {'status': 'ativo' if active else 'inativo'}
        if active:
            result['watch_folder'] = DownloadWatcherService.watch_folder(caso.pk)
        return JsonResponse(result)


class AbrirPastaCasoView(CasoAccessMixin, View):
    def get(self, request, pk):
        caso = self.get_caso(pk)
        path = caso.path_pasta
        host_root = os.environ.get('HOST_PROJECT_ROOT', '')
        if host_root and path.startswith('/app'):
            path = host_root + path[len('/app'):]
        if sys.platform.startswith('linux') and host_root and ':' in host_root:
            messages.warning(
                request,
                f'No modo Docker, o sistema nao consegue abrir o Explorer do Windows automaticamente. '
                f'Abra manualmente a pasta: {path}',
            )
            return redirect('caso_detalhe', pk=caso.pk)
        try:
            if sys.platform == 'win32':
                subprocess.Popen(['explorer', path])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception as exc:
            messages.error(request, f'Não foi possível abrir a pasta: {exc}')
        return redirect('caso_detalhe', pk=caso.pk)


class RelatorioDownloadView(CasoAccessMixin, View):
    _CONTENT_TYPES = {
        '.pdf':  'application/pdf',
        '.html': 'text/html',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }

    def get(self, request, pk, rel_pk):
        caso = self.get_caso(pk)
        relatorio = get_object_or_404(RelatorioGerado, pk=rel_pk, caso=caso)
        file_path = Path(relatorio.path_arquivo)
        if not file_path.exists():
            messages.error(request, f'Arquivo não encontrado: {file_path.name}')
            return redirect('caso_detalhe', pk=caso.pk)
        content_type = self._CONTENT_TYPES.get(file_path.suffix.lower(), 'application/octet-stream')
        as_attachment = file_path.suffix.lower() == '.docx'
        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=as_attachment,
            filename=file_path.name,
            content_type=content_type,
        )
