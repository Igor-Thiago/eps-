import json
import re
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .hash_service import HashService


class ScreenshotError(Exception):
    pass


@dataclass(frozen=True)
class ScreenshotResult:
    path: Path
    hash_sha256: str
    filename: str
    size_bytes: int
    captured_at_utc: str
    metadata: dict


@dataclass(frozen=True)
class ScreenshotReportResult:
    report_number: str
    pdf_path: Path
    hash_sha256: str
    generated_at_utc: str


class ScreenshotService:
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
    BLACK = colors.HexColor('#1A1A1A')
    GOLD = colors.HexColor('#C8A951')

    def save_screenshot(self, caso, uploaded_file, metadata: dict | None = None) -> ScreenshotResult:
        if not uploaded_file:
            raise ScreenshotError('Nenhuma captura de tela foi enviada.')

        metadata = metadata or {}
        extension = self._extension(uploaded_file.name)
        screenshot_id = self._safe_identifier(metadata.get('screenshot_id') or 'captura')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')

        output_dir = Path(caso.path_pasta) / 'capturas'
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f'{timestamp}_{screenshot_id}{extension}'
        output_path = output_dir / filename

        size = 0
        try:
            with output_path.open('wb') as destination:
                for chunk in uploaded_file.chunks():
                    size += len(chunk)
                    destination.write(chunk)
        except OSError as exc:
            raise ScreenshotError(f'Nao foi possivel salvar a captura: {exc}') from exc

        hash_sha256 = HashService.hash_file(output_path)
        captured_at = timezone.now().isoformat()
        normalized_metadata = {
            **metadata,
            'filename': filename,
            'size_bytes': size,
            'captured_at_utc': captured_at,
            'content_type': getattr(uploaded_file, 'content_type', ''),
        }

        metadata_path = output_path.with_suffix('.json')
        metadata_path.write_text(json.dumps(normalized_metadata, ensure_ascii=False, indent=2), encoding='utf-8')

        return ScreenshotResult(
            path=output_path,
            hash_sha256=hash_sha256,
            filename=filename,
            size_bytes=size,
            captured_at_utc=captured_at,
            metadata={**normalized_metadata, 'metadata_path': str(metadata_path)},
        )

    def generate_individual_report(self, caso, evidencia, sequence: int) -> ScreenshotReportResult:
        screenshot_path = Path(evidencia.path_arquivo)
        if not screenshot_path.exists():
            raise ScreenshotError('Imagem da captura indisponivel para gerar relatorio.')

        report_number = f'RC-{caso.id:04d}-{sequence:03d}'
        pdf_path = screenshot_path.with_name(f'relatorio_captura_{report_number}.pdf')
        generated_at = timezone.now()
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=1.6 * cm,
            leftMargin=1.6 * cm,
            topMargin=1.4 * cm,
            bottomMargin=1.4 * cm,
            title=f'Relatorio de Captura {report_number}',
            author='EDIFRAUDS/CORF/PCDF',
        )

        image = Image(str(screenshot_path))
        max_width = 17.0 * cm
        max_height = 17.0 * cm
        ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
        image.drawWidth = image.imageWidth * ratio
        image.drawHeight = image.imageHeight * ratio

        table = Table(
            [
                ['Relatorio', report_number],
                ['Caso', caso.nome],
                ['Processo', caso.numero_processo or '-'],
                ['Analista', caso.analista.get_full_name() or caso.analista.matricula],
                ['Captura UTC', evidencia.metadados_json.get('captured_at_utc', '-')],
                ['Relatorio UTC', generated_at.isoformat()],
                ['Arquivo', evidencia.path_arquivo],
                ['SHA-256', evidencia.hash_sha256],
            ],
            colWidths=[4.0 * cm, 13.8 * cm],
        )
        table.setStyle(
            TableStyle(
                [
                    ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D6DBDF')),
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F7F4EA')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                ]
            )
        )

        story = [
            Paragraph('EDIFRAUDS / CORF / PCDF', styles['Title']),
            Paragraph(f'Relatorio Individual de Captura de Tela - {report_number}', styles['Heading2']),
            Spacer(1, 0.35 * cm),
            table,
            Spacer(1, 0.45 * cm),
            image,
        ]
        doc.build(story, onFirstPage=self._draw_page, onLaterPages=self._draw_page)
        return ScreenshotReportResult(
            report_number=report_number,
            pdf_path=pdf_path,
            hash_sha256=HashService.hash_file(pdf_path),
            generated_at_utc=generated_at.isoformat(),
        )

    def _draw_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(self.GOLD)
        canvas.setLineWidth(1)
        canvas.line(1.6 * cm, 1.0 * cm, A4[0] - 1.6 * cm, 1.0 * cm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.BLACK)
        canvas.drawRightString(A4[0] - 1.6 * cm, 0.65 * cm, f'Pagina {doc.page}')
        canvas.restoreState()

    def _extension(self, filename: str) -> str:
        extension = Path(filename or '').suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ScreenshotError('Formato de imagem nao permitido. Use PNG ou JPEG.')
        return extension

    @staticmethod
    def _safe_identifier(value: str) -> str:
        safe = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(value)).strip('-')
        return safe[:80] or 'captura'
