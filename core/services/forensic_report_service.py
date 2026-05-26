import json
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .hash_service import HashService


class ForensicReportError(Exception):
    pass


@dataclass(frozen=True)
class ForensicReportResult:
    report_number: str
    pdf_path: Path
    hash_sha256: str
    artifact_hashes: list[dict]
    generated_at_utc: str


class ForensicReportService:
    BLACK = colors.HexColor('#1A1A1A')
    GOLD = colors.HexColor('#C8A951')
    WHITE = colors.white

    def generate_site_report(self, caso, evidencia, preservation_result, sequence: int, config=None) -> ForensicReportResult:
        output_dir = Path(preservation_result.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        report_number = f'RF-{caso.id:04d}-{sequence:03d}'
        pdf_path = output_dir / f'relatorio_forense_{report_number}.pdf'
        generated_at = timezone.now()
        artifact_hashes = self._artifact_hashes(preservation_result)

        try:
            self._build_pdf(
                pdf_path=pdf_path,
                report_number=report_number,
                generated_at=generated_at,
                caso=caso,
                evidencia=evidencia,
                preservation_result=preservation_result,
                artifact_hashes=artifact_hashes,
                config=config,
            )
        except Exception as exc:
            raise ForensicReportError(f'Nao foi possivel gerar o relatorio PDF: {exc}') from exc

        return ForensicReportResult(
            report_number=report_number,
            pdf_path=pdf_path,
            hash_sha256=HashService.hash_file(pdf_path),
            artifact_hashes=artifact_hashes,
            generated_at_utc=generated_at.isoformat(),
        )

    def _build_pdf(self, pdf_path, report_number, generated_at, caso, evidencia, preservation_result, artifact_hashes, config=None):
        styles = self._styles()
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=1.6 * cm,
            leftMargin=1.6 * cm,
            topMargin=1.4 * cm,
            bottomMargin=1.4 * cm,
            title=f'Relatorio Forense {report_number}',
            author='EDIFRAUDS/CORF/PCDF',
        )

        cabecalho = (config.cabecalho if config and config.cabecalho else 'EDIFRAUDS / CORF / PCDF')
        incluir_tecnica = config.incluir_info_tecnica if config else True

        story = [
            self._header_table(report_number, cabecalho, config),
            Spacer(1, 0.45 * cm),
            Paragraph('Dados do Caso', styles['Section']),
            self._key_value_table(
                [
                    ('Caso', caso.nome),
                    ('Numero do processo', caso.numero_processo or '-'),
                    ('Analista', caso.analista.get_full_name() or caso.analista.matricula),
                    ('Matricula', caso.analista.matricula),
                    ('Pasta do caso', caso.path_pasta),
                    ('Relatorio gerado em UTC', generated_at.isoformat()),
                    ('Evidencia criada em UTC', evidencia.created_at.isoformat()),
                ]
            ),
            Spacer(1, 0.35 * cm),
            Paragraph('URL Preservada', styles['Section']),
            self._key_value_table(
                [
                    ('URL original', preservation_result.url),
                    ('URL final', preservation_result.final_url),
                    ('Dominio', preservation_result.domain),
                    ('Status HTTP', preservation_result.status if preservation_result.status is not None else '-'),
                    ('Titulo da pagina', preservation_result.title or '-'),
                ]
            ),
            Spacer(1, 0.35 * cm),
            Paragraph('Screenshot', styles['Section']),
            *self._screenshot_block(preservation_result.screenshot_path, styles),
        ]

        if incluir_tecnica:
            story += [
                PageBreak(),
                Paragraph('Metadados Tecnicos', styles['Section']),
                *self._metadata_blocks(preservation_result.technical_metadata, styles),
                Spacer(1, 0.35 * cm),
            ]
        else:
            story.append(PageBreak())

        story += [
            Paragraph('Hashes SHA-256 dos Artefatos', styles['Section']),
            self._hash_table(artifact_hashes),
            Spacer(1, 0.35 * cm),
            Paragraph('Cadeia de Custodia', styles['Section']),
            Paragraph(
                'Este relatorio foi gerado automaticamente a partir dos artefatos preservados. '
                'O hash SHA-256 do PDF e registrado no banco em RelatorioGerado apos a geracao do arquivo.',
                styles['Body'],
            ),
        ]

        if config and (config.assinatura_nome or config.assinatura_cargo):
            story += [
                Spacer(1, 0.8 * cm),
                Paragraph('Assinatura do Responsavel', styles['Section']),
                self._key_value_table(
                    [
                        ('Nome', config.assinatura_nome or '-'),
                        ('Cargo', config.assinatura_cargo or '-'),
                        ('Orgao', config.assinatura_orgao or 'CORF/PCDF'),
                    ]
                ),
            ]

        doc.build(story, onFirstPage=self._draw_page, onLaterPages=self._draw_page)

    def _styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='HeaderTitle', fontSize=15, leading=18, alignment=TA_CENTER, textColor=self.WHITE))
        styles.add(ParagraphStyle(name='HeaderSub', fontSize=9, leading=12, alignment=TA_CENTER, textColor=self.WHITE))
        styles.add(ParagraphStyle(name='Section', fontSize=13, leading=16, textColor=self.BLACK, spaceAfter=8))
        styles.add(ParagraphStyle(name='Body', fontSize=9, leading=12, textColor=self.BLACK))
        styles.add(ParagraphStyle(name='Small', fontSize=7, leading=9, textColor=self.BLACK))
        return styles

    def _header_table(self, report_number, cabecalho='EDIFRAUDS / CORF / PCDF', config=None):
        styles = self._styles()
        titulo = self._escape(cabecalho.replace('\n', '<br/>'))
        rows = [
            [Paragraph(titulo, styles['HeaderTitle'])],
            [Paragraph(f'Relatorio Forense de Preservacao de Site - {report_number}', styles['HeaderSub'])],
        ]

        if config and config.logo and hasattr(config.logo, 'path'):
            logo_path = Path(config.logo.path)
            if logo_path.exists():
                logo_img = Image(str(logo_path), width=1.8 * cm, height=1.8 * cm)
                rows[0] = [logo_img, Paragraph(titulo, styles['HeaderTitle'])]
                table = Table(rows, colWidths=[2.2 * cm, 15.6 * cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), self.BLACK),
                    ('BOX', (0, 0), (-1, -1), 1.2, self.GOLD),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, self.GOLD),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
                    ('SPAN', (0, 1), (1, 1)),
                ]))
                return table

        table = Table(rows, colWidths=[17.8 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.BLACK),
            ('BOX', (0, 0), (-1, -1), 1.2, self.GOLD),
            ('LINEBELOW', (0, 0), (-1, 0), 1, self.GOLD),
            ('TOPPADDING', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ]))
        return table

    def _key_value_table(self, rows):
        styles = self._styles()
        data = [
            [
                Paragraph(self._escape(str(key)), styles['Small']),
                Paragraph(self._escape(self._safe_text(value)), styles['Small']),
            ]
            for key, value in rows
        ]
        table = Table(data, colWidths=[4.6 * cm, 13.2 * cm], hAlign='LEFT')
        table.setStyle(self._base_table_style())
        return table

    def _hash_table(self, artifact_hashes):
        styles = self._styles()
        data = [['Artefato', 'Caminho', 'SHA-256']]
        data.extend(
            [
                [
                    Paragraph(self._escape(item['name']), styles['Small']),
                    Paragraph(self._escape(item['path']), styles['Small']),
                    Paragraph(self._escape(item['sha256']), styles['Small']),
                ]
                for item in artifact_hashes
            ]
        )
        table = Table(data, colWidths=[3.0 * cm, 6.8 * cm, 8.0 * cm], repeatRows=1)
        table.setStyle(self._base_table_style(header=True, font_size=6))
        return table

    def _metadata_blocks(self, metadata, styles):
        metadata = metadata or {}
        blocks = []
        blocks.extend(self._metadata_section('WHOIS/RDAP', metadata.get('whois_rdap'), styles))
        blocks.extend(self._metadata_section('SSL', metadata.get('ssl'), styles))
        blocks.extend(self._metadata_section('HTTP', metadata.get('http_headers'), styles))
        blocks.extend(self._metadata_section('DNS', metadata.get('dns'), styles))
        blocks.extend(self._metadata_section('IP do Servidor', {'ip': metadata.get('ip')}, styles))
        return blocks

    def _metadata_section(self, title, data, styles):
        pretty = json.dumps(data or {}, ensure_ascii=False, indent=2, sort_keys=True)
        return [
            Paragraph(title, styles['Body']),
            Paragraph(f'<font face="Courier">{self._escape(pretty)}</font>', styles['Small']),
            Spacer(1, 0.22 * cm),
        ]

    def _screenshot_block(self, screenshot_path, styles):
        path = Path(screenshot_path)
        if not path.exists():
            return [Paragraph('Screenshot indisponivel no caminho informado.', styles['Body'])]
        image = Image(str(path))
        max_width = 17.2 * cm
        max_height = 15.5 * cm
        ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
        image.drawWidth = image.imageWidth * ratio
        image.drawHeight = image.imageHeight * ratio
        return [image]

    def _artifact_hashes(self, preservation_result):
        artifacts = [
            ('HTML renderizado', preservation_result.html_path),
            ('Screenshot PNG', preservation_result.screenshot_path),
            ('Snapshot MHTML', preservation_result.mhtml_path),
            ('Metadados JSON', preservation_result.metadata_path),
        ]
        hashes = []
        for name, path in artifacts:
            artifact_path = Path(path)
            hashes.append(
                {
                    'name': name,
                    'path': str(artifact_path),
                    'sha256': HashService.hash_file(artifact_path) if artifact_path.exists() else 'arquivo indisponivel',
                }
            )
        return hashes

    def _base_table_style(self, header=False, font_size=8):
        style = [
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D6DBDF')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]
        if header:
            style.extend(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), self.BLACK),
                    ('TEXTCOLOR', (0, 0), (-1, 0), self.WHITE),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, self.GOLD),
                ]
            )
        else:
            style.append(('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F7F4EA')))
        return TableStyle(style)

    def _draw_page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(self.GOLD)
        canvas.setLineWidth(1)
        canvas.line(1.6 * cm, 1.0 * cm, A4[0] - 1.6 * cm, 1.0 * cm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(self.BLACK)
        canvas.drawRightString(A4[0] - 1.6 * cm, 0.65 * cm, f'Pagina {doc.page}')
        canvas.restoreState()

    @staticmethod
    def _safe_text(value):
        if value is None:
            return '-'
        return str(value)

    @staticmethod
    def _escape(value):
        return (
            value.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', '<br/>')
        )
