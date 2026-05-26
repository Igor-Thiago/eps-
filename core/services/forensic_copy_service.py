import json
from dataclasses import dataclass, field
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .hash_service import HashService


class ForensicCopyError(Exception):
    pass


@dataclass(frozen=True)
class FileCopyResult:
    original_name: str
    filename: str
    path: Path
    hash_sha256: str
    size_bytes: int
    exif: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ForensicCopyResult:
    files: list
    zip_path: Path
    zip_hash_sha256: str
    pdf_path: Path
    pdf_hash_sha256: str
    copied_at_utc: str


class ForensicCopyService:
    BLACK = colors.HexColor('#1A1A1A')
    GOLD = colors.HexColor('#C8A951')
    WHITE = colors.white

    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp', '.heic'}

    def copy(self, caso, uploaded_files) -> ForensicCopyResult:
        if not uploaded_files:
            raise ForensicCopyError('Nenhum arquivo foi enviado.')

        output_dir = Path(caso.path_pasta) / 'copias_forenses'
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        copied_at = timezone.now().isoformat()
        file_results = []

        for uploaded in uploaded_files:
            filename = f'{timestamp}_{uploaded.name}'
            dest = output_dir / filename
            size = 0
            try:
                with dest.open('wb') as fout:
                    for chunk in uploaded.chunks():
                        size += len(chunk)
                        fout.write(chunk)
            except OSError as exc:
                raise ForensicCopyError(f'Nao foi possivel copiar {uploaded.name}: {exc}') from exc

            hash_sha256 = HashService.hash_file(dest)
            exif = self._extract_exif(dest)

            metadata_path = dest.with_suffix('.json')
            metadata_path.write_text(
                json.dumps({
                    'original_name': uploaded.name,
                    'filename': filename,
                    'size_bytes': size,
                    'hash_sha256': hash_sha256,
                    'copied_at_utc': copied_at,
                    'exif': exif,
                }, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

            file_results.append(FileCopyResult(
                original_name=uploaded.name,
                filename=filename,
                path=dest,
                hash_sha256=hash_sha256,
                size_bytes=size,
                exif=exif,
            ))

        zip_path = output_dir / f'{timestamp}_copia_forense.zip'
        zip_hash = HashService.hash_zip([r.path for r in file_results], zip_path)

        pdf_path = output_dir / f'{timestamp}_relatorio_copia_forense.pdf'
        self._build_pdf(pdf_path, caso, file_results, zip_path, zip_hash, copied_at)
        pdf_hash = HashService.hash_file(pdf_path)

        return ForensicCopyResult(
            files=file_results,
            zip_path=zip_path,
            zip_hash_sha256=zip_hash,
            pdf_path=pdf_path,
            pdf_hash_sha256=pdf_hash,
            copied_at_utc=copied_at,
        )

    # ── EXIF ─────────────────────────────────────────────────────────────────

    def _extract_exif(self, path: Path) -> dict:
        if path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            return {}
        try:
            from PIL import Image
            from PIL.ExifTags import GPSTAGS, TAGS

            with Image.open(path) as img:
                exif_raw = img.getexif()
                if not exif_raw:
                    return {}

                result = {}
                for tag_id, value in exif_raw.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    if isinstance(value, bytes):
                        result[tag_name] = value.hex()
                    else:
                        try:
                            result[tag_name] = str(value)
                        except Exception:
                            pass

                gps_ifd = exif_raw.get_ifd(0x8825)
                if gps_ifd:
                    gps_data = {}
                    for gps_id, gps_val in gps_ifd.items():
                        gps_name = GPSTAGS.get(gps_id, str(gps_id))
                        gps_data[gps_name] = str(gps_val)
                    result['GPS'] = gps_data
                    try:
                        lat = self._dms_to_decimal(gps_ifd[2], gps_ifd[1])
                        lon = self._dms_to_decimal(gps_ifd[4], gps_ifd[3])
                        result['GPS_decimal'] = {'latitude': lat, 'longitude': lon}
                    except Exception:
                        pass

                return result
        except Exception:
            return {}

    @staticmethod
    def _dms_to_decimal(dms, ref: str) -> float:
        d, m, s = (float(x) for x in dms)
        decimal = d + m / 60 + s / 3600
        if ref in ('S', 'W'):
            decimal = -decimal
        return round(decimal, 7)

    # ── PDF ──────────────────────────────────────────────────────────────────

    def _build_pdf(self, pdf_path, caso, file_results, zip_path, zip_hash, copied_at):
        styles = self._styles()
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=1.6 * cm,
            leftMargin=1.6 * cm,
            topMargin=1.4 * cm,
            bottomMargin=1.4 * cm,
            title='Relatorio de Copia Forense',
            author='EDIFRAUDS/CORF/PCDF',
        )

        story = [
            self._header_table(styles),
            Spacer(1, 0.45 * cm),
            Paragraph('Dados do Caso', styles['Section']),
            self._kv_table([
                ('Caso', caso.nome),
                ('Processo', caso.numero_processo or '-'),
                ('Analista', caso.analista.get_full_name() or caso.analista.matricula),
                ('Matricula', caso.analista.matricula),
                ('Copia realizada em UTC', copied_at),
                ('Total de arquivos', str(len(file_results))),
            ], styles),
            Spacer(1, 0.35 * cm),
            Paragraph('Arquivos Copiados', styles['Section']),
            self._files_summary_table(file_results, styles),
        ]

        for i, fr in enumerate(file_results, 1):
            story += [
                Spacer(1, 0.4 * cm),
                Paragraph(f'Arquivo {i}: {self._esc(fr.original_name)}', styles['Subsection']),
                self._kv_table([
                    ('Nome original', fr.original_name),
                    ('Arquivo copiado', fr.filename),
                    ('Tamanho', f'{fr.size_bytes:,} bytes'),
                    ('Hash SHA-256', fr.hash_sha256),
                ], styles),
            ]
            if fr.exif:
                story += [
                    Spacer(1, 0.2 * cm),
                    Paragraph('Metadados EXIF', styles['Body']),
                    self._exif_table(fr.exif, styles),
                ]

        story += [
            Spacer(1, 0.4 * cm),
            Paragraph('Pacote ZIP dos Artefatos', styles['Section']),
            self._kv_table([
                ('Arquivo ZIP', zip_path.name),
                ('Caminho', str(zip_path)),
                ('Hash SHA-256 do ZIP', zip_hash),
            ], styles),
            Spacer(1, 0.35 * cm),
            Paragraph('Cadeia de Custodia', styles['Section']),
            Paragraph(
                'Os arquivos foram copiados bit a bit para a pasta do caso. '
                'Os hashes SHA-256 individuais e do pacote ZIP garantem a integridade '
                'dos artefatos coletados.',
                styles['Body'],
            ),
        ]

        doc.build(story, onFirstPage=self._draw_page, onLaterPages=self._draw_page)

    def _styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='HeaderTitle', fontSize=15, leading=18, alignment=TA_CENTER, textColor=self.WHITE))
        styles.add(ParagraphStyle(name='HeaderSub', fontSize=9, leading=12, alignment=TA_CENTER, textColor=self.WHITE))
        styles.add(ParagraphStyle(name='Section', fontSize=13, leading=16, textColor=self.BLACK, spaceAfter=8))
        styles.add(ParagraphStyle(name='Subsection', fontSize=10, leading=13, textColor=self.BLACK, spaceAfter=4))
        styles.add(ParagraphStyle(name='Body', fontSize=9, leading=12, textColor=self.BLACK))
        styles.add(ParagraphStyle(name='Small', fontSize=7, leading=9, textColor=self.BLACK))
        return styles

    def _header_table(self, styles):
        table = Table(
            [
                [Paragraph('EDIFRAUDS / CORF / PCDF', styles['HeaderTitle'])],
                [Paragraph('Relatorio de Copia Forense de Arquivos', styles['HeaderSub'])],
            ],
            colWidths=[17.8 * cm],
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.BLACK),
            ('BOX', (0, 0), (-1, -1), 1.2, self.GOLD),
            ('LINEBELOW', (0, 0), (-1, 0), 1, self.GOLD),
            ('TOPPADDING', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ]))
        return table

    def _files_summary_table(self, file_results, styles):
        header = ['#', 'Nome original', 'Tamanho', 'Hash SHA-256', 'EXIF']
        rows = [header]
        for i, fr in enumerate(file_results, 1):
            rows.append([
                str(i),
                fr.original_name,
                f'{fr.size_bytes:,} B',
                fr.hash_sha256[:16] + '...',
                'Sim' if fr.exif else 'Nao',
            ])
        t = Table(rows, colWidths=[0.6 * cm, 6.0 * cm, 2.2 * cm, 5.5 * cm, 1.5 * cm], repeatRows=1)
        t.setStyle(self._base_style(header=True, font_size=7))
        return t

    def _exif_table(self, exif: dict, styles):
        rows = []
        for key, value in exif.items():
            if key == 'GPS':
                continue
            rows.append([
                Paragraph(self._esc(str(key)), styles['Small']),
                Paragraph(self._esc(str(value)[:120]), styles['Small']),
            ])
        if 'GPS_decimal' in exif:
            gps = exif['GPS_decimal']
            rows.append([
                Paragraph('GPS (decimal)', styles['Small']),
                Paragraph(f'Lat: {gps["latitude"]}, Lon: {gps["longitude"]}', styles['Small']),
            ])
        elif 'GPS' in exif:
            for k, v in exif['GPS'].items():
                rows.append([
                    Paragraph(self._esc(f'GPS/{k}'), styles['Small']),
                    Paragraph(self._esc(str(v)[:120]), styles['Small']),
                ])
        if not rows:
            return Paragraph('Nenhum dado EXIF relevante encontrado.', styles['Small'])
        t = Table(rows, colWidths=[4.6 * cm, 13.2 * cm], hAlign='LEFT')
        t.setStyle(self._base_style())
        return t

    def _kv_table(self, rows, styles):
        data = [
            [
                Paragraph(self._esc(str(k)), styles['Small']),
                Paragraph(self._esc(str(v)), styles['Small']),
            ]
            for k, v in rows
        ]
        t = Table(data, colWidths=[4.6 * cm, 13.2 * cm], hAlign='LEFT')
        t.setStyle(self._base_style())
        return t

    def _base_style(self, header=False, font_size=8):
        style = [
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D6DBDF')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]
        if header:
            style += [
                ('BACKGROUND', (0, 0), (-1, 0), self.BLACK),
                ('TEXTCOLOR', (0, 0), (-1, 0), self.WHITE),
                ('LINEBELOW', (0, 0), (-1, 0), 1, self.GOLD),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ]
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
    def _esc(value: str) -> str:
        return (
            str(value)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', '<br/>')
        )
