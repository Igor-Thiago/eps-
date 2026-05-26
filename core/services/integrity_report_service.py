import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core.models import AuditLog, Evidencia, RelatorioGerado
from .audit_logger import AuditLogger
from .hash_service import HashService


class IntegrityReportError(Exception):
    pass


@dataclass(frozen=True)
class IntegrityReportResult:
    report_number: str
    pdf_path: Path
    html_path: Path
    pdf_hash_sha256: str
    html_hash_sha256: str
    chain_valid: bool
    generated_at_utc: str
    software_hash: str
    total_logs: int


class IntegrityReportService:
    BLACK = colors.HexColor('#1A1A1A')
    GOLD = colors.HexColor('#C8A951')
    WHITE = colors.white
    GREEN = colors.HexColor('#2E7D32')
    RED = colors.HexColor('#C62828')

    def generate(self, caso, analista) -> IntegrityReportResult:
        output_dir = Path(caso.path_pasta) / 'integridade'
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_at = timezone.now()
        logs = list(AuditLog.objects.filter(caso=caso).order_by('timestamp_utc'))
        evidencias_site = list(caso.evidencias.filter(tipo=Evidencia.Tipo.SITE))
        evidencias_video = list(caso.evidencias.filter(tipo=Evidencia.Tipo.VIDEO))
        evidencias_screenshot = list(caso.evidencias.filter(tipo=Evidencia.Tipo.SCREENSHOT))
        evidencias_download = list(caso.evidencias.filter(tipo=Evidencia.Tipo.DOWNLOAD))
        relatorios = list(caso.relatorios.all())
        chain_valid = AuditLogger.verificar_cadeia(caso)
        software_hash = self._hash_software()

        report_number = f'RI-{caso.id:04d}-{generated_at.strftime("%Y%m%d%H%M%S")}'
        pdf_path = output_dir / f'relatorio_integridade_{report_number}.pdf'
        html_path = output_dir / f'relatorio_integridade_{report_number}.html'

        try:
            self._build_pdf(
                pdf_path, report_number, generated_at, caso,
                logs, evidencias_site, evidencias_video, evidencias_screenshot,
                evidencias_download, relatorios, chain_valid, software_hash,
            )
            self._build_html(
                html_path, report_number, generated_at, caso,
                logs, evidencias_site, evidencias_video, evidencias_screenshot,
                evidencias_download, relatorios, chain_valid, software_hash,
            )
        except Exception as exc:
            raise IntegrityReportError(f'Nao foi possivel gerar o relatorio de integridade: {exc}') from exc

        return IntegrityReportResult(
            report_number=report_number,
            pdf_path=pdf_path,
            html_path=html_path,
            pdf_hash_sha256=HashService.hash_file(pdf_path),
            html_hash_sha256=HashService.hash_file(html_path),
            chain_valid=chain_valid,
            generated_at_utc=generated_at.isoformat(),
            software_hash=software_hash,
            total_logs=len(logs),
        )

    # ── PDF ──────────────────────────────────────────────────────────────────

    def _build_pdf(
        self, pdf_path, report_number, generated_at, caso,
        logs, sites, videos, screenshots, downloads, relatorios,
        chain_valid, software_hash,
    ):
        styles = self._styles()
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=1.6 * cm,
            leftMargin=1.6 * cm,
            topMargin=1.4 * cm,
            bottomMargin=1.4 * cm,
            title=f'Relatorio de Integridade {report_number}',
            author='EDIFRAUDS/CORF/PCDF',
        )

        story = [
            self._header_table(report_number, styles),
            Spacer(1, 0.45 * cm),
            Paragraph('Dados do Caso', styles['Section']),
            self._kv_table([
                ('Caso', caso.nome),
                ('Processo', caso.numero_processo or '-'),
                ('Analista', caso.analista.get_full_name() or caso.analista.matricula),
                ('Matricula', caso.analista.matricula),
                ('Pasta', caso.path_pasta),
                ('Gerado em UTC', generated_at.isoformat()),
            ], styles),
            Spacer(1, 0.35 * cm),
            Paragraph('Integridade do Software', styles['Section']),
            self._kv_table([
                ('SHA-256 do Sistema', software_hash),
                ('Escopo', 'Todos os arquivos .py do projeto (exceto migrations e cache)'),
            ], styles),
            Spacer(1, 0.35 * cm),
            Paragraph('Verificacao da Cadeia de Custodia', styles['Section']),
            self._chain_status_table(chain_valid, len(logs), styles),
            Spacer(1, 0.35 * cm),
            Paragraph('Sumario de Evidencias', styles['Section']),
            self._kv_table([
                ('Sites preservados', str(len(sites))),
                ('Gravacoes de tela', str(len(videos))),
                ('Capturas de tela', str(len(screenshots))),
                ('Downloads monitorados', str(len(downloads))),
                ('Relatorios gerados', str(len(relatorios))),
                ('Total de blocos na cadeia', str(len(logs))),
            ], styles),
            PageBreak(),
            Paragraph('Tabela de Encadeamento (Blockchain)', styles['Section']),
            self._chain_table(logs, styles),
            PageBreak(),
            Paragraph('Registro Cronologico de Acoes', styles['Section']),
            self._log_table(logs, styles),
        ]

        if sites:
            story += [
                Spacer(1, 0.35 * cm),
                Paragraph('Sites Preservados', styles['Section']),
                self._sites_table(sites, styles),
            ]

        if relatorios:
            story += [
                Spacer(1, 0.35 * cm),
                Paragraph('Relatorios Gerados', styles['Section']),
                self._relatorios_table(relatorios, styles),
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

    def _header_table(self, report_number, styles):
        table = Table(
            [
                [Paragraph('EDIFRAUDS / CORF / PCDF', styles['HeaderTitle'])],
                [Paragraph(f'Relatorio de Integridade Final - {report_number}', styles['HeaderSub'])],
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

    def _kv_table(self, rows, styles):
        data = [
            [
                Paragraph(self._pdf_esc(str(k)), styles['Small']),
                Paragraph(self._pdf_esc(str(v)), styles['Small']),
            ]
            for k, v in rows
        ]
        t = Table(data, colWidths=[4.6 * cm, 13.2 * cm], hAlign='LEFT')
        t.setStyle(self._base_style())
        return t

    def _chain_status_table(self, chain_valid, total, styles):
        status_text = 'INTEGRA' if chain_valid else 'VIOLADA'
        status_color = self.GREEN if chain_valid else self.RED
        status_style = ParagraphStyle(
            'StatusText', fontSize=12, leading=14,
            alignment=TA_CENTER, textColor=self.WHITE,
        )
        data = [[
            Paragraph(f'Cadeia: {status_text}', status_style),
            Paragraph(f'{total} blocos verificados', styles['Body']),
        ]]
        t = Table(data, colWidths=[8.9 * cm, 8.9 * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), status_color),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F7F4EA')),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#D6DBDF')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        return t

    def _chain_table(self, logs, styles):
        header = ['#', 'Timestamp UTC', 'Acao', 'Hash Anterior', 'Hash Atual']
        rows = [header]
        for i, log in enumerate(logs, 1):
            anterior = (log.hash_bloco_anterior[:16] + '...') if log.hash_bloco_anterior else '—'
            rows.append([
                str(i),
                log.timestamp_utc.strftime('%d/%m/%Y %H:%M:%S'),
                log.acao,
                anterior,
                log.hash_bloco_atual[:16] + '...',
            ])
        t = Table(rows, colWidths=[0.7 * cm, 3.8 * cm, 4.5 * cm, 4.4 * cm, 4.4 * cm], repeatRows=1)
        t.setStyle(self._base_style(header=True, font_size=6))
        return t

    def _log_table(self, logs, styles):
        header = ['Timestamp UTC', 'Acao', 'Analista']
        rows = [header]
        for log in logs:
            rows.append([
                log.timestamp_utc.strftime('%d/%m/%Y %H:%M:%S'),
                log.acao,
                log.analista.get_full_name() or log.analista.matricula,
            ])
        t = Table(rows, colWidths=[4.0 * cm, 9.0 * cm, 4.8 * cm], repeatRows=1)
        t.setStyle(self._base_style(header=True, font_size=7))
        return t

    def _sites_table(self, sites, styles):
        header = ['URL', 'Dominio', 'HTTP', 'Hash SHA-256', 'Capturado em']
        rows = [header]
        for ev in sites:
            m = ev.metadados_json
            rows.append([
                m.get('url', '-'),
                m.get('domain', '-'),
                str(m.get('status', '-')),
                ev.hash_sha256[:16] + '...',
                ev.created_at.strftime('%d/%m/%Y %H:%M'),
            ])
        t = Table(rows, colWidths=[5.0 * cm, 3.0 * cm, 1.3 * cm, 4.5 * cm, 3.0 * cm], repeatRows=1)
        t.setStyle(self._base_style(header=True, font_size=6))
        return t

    def _relatorios_table(self, relatorios, styles):
        header = ['Tipo', 'Arquivo', 'Hash SHA-256', 'Gerado em']
        rows = [header]
        for r in relatorios:
            rows.append([
                r.get_tipo_display(),
                Path(r.path_arquivo).name,
                r.hash_sha256[:16] + '...',
                r.created_at.strftime('%d/%m/%Y %H:%M'),
            ])
        t = Table(rows, colWidths=[2.0 * cm, 8.8 * cm, 4.5 * cm, 2.5 * cm], repeatRows=1)
        t.setStyle(self._base_style(header=True, font_size=6))
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

    # ── HTML ─────────────────────────────────────────────────────────────────

    def _build_html(
        self, html_path, report_number, generated_at, caso,
        logs, sites, videos, screenshots, downloads, relatorios,
        chain_valid, software_hash,
    ):
        status_text = 'ÍNTEGRA' if chain_valid else 'VIOLADA'
        status_color = '#2E7D32' if chain_valid else '#C62828'

        chain_rows = ''
        for i, log in enumerate(logs, 1):
            anterior = log.hash_bloco_anterior or '—'
            chain_rows += (
                f'<tr>'
                f'<td>{i}</td>'
                f'<td class="mono">{log.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S")} UTC</td>'
                f'<td>{self._hesc(log.acao)}</td>'
                f'<td class="mono small">{self._hesc(anterior)}</td>'
                f'<td class="mono small">{self._hesc(log.hash_bloco_atual)}</td>'
                f'</tr>'
            )

        log_rows = ''
        for log in logs:
            dados_str = json.dumps(log.dados_json, ensure_ascii=False)
            log_rows += (
                f'<tr>'
                f'<td class="mono">{log.timestamp_utc.strftime("%Y-%m-%d %H:%M:%S")} UTC</td>'
                f'<td>{self._hesc(log.acao)}</td>'
                f'<td>{self._hesc(log.analista.get_full_name() or log.analista.matricula)}</td>'
                f'<td class="small">{self._hesc(dados_str)}</td>'
                f'</tr>'
            )

        sites_section = ''
        if sites:
            site_rows = ''
            for ev in sites:
                m = ev.metadados_json
                site_rows += (
                    f'<tr>'
                    f'<td>{self._hesc(m.get("url", "-"))}</td>'
                    f'<td>{self._hesc(m.get("domain", "-"))}</td>'
                    f'<td>{m.get("status", "-")}</td>'
                    f'<td class="mono small">{self._hesc(ev.hash_sha256)}</td>'
                    f'<td>{ev.created_at.strftime("%d/%m/%Y %H:%M")}</td>'
                    f'</tr>'
                )
            sites_section = (
                '<div class="section">'
                '<div class="section-title">Sites Preservados</div>'
                '<div class="section-body"><table>'
                '<thead><tr><th>URL</th><th>Domínio</th><th>HTTP</th><th>Hash SHA-256</th><th>Capturado em</th></tr></thead>'
                f'<tbody>{site_rows}</tbody>'
                '</table></div></div>'
            )

        rel_section = ''
        if relatorios:
            rel_rows = ''
            for r in relatorios:
                rel_rows += (
                    f'<tr>'
                    f'<td>{self._hesc(r.get_tipo_display())}</td>'
                    f'<td class="small">{self._hesc(r.path_arquivo)}</td>'
                    f'<td class="mono small">{self._hesc(r.hash_sha256)}</td>'
                    f'<td>{r.created_at.strftime("%d/%m/%Y %H:%M")}</td>'
                    f'</tr>'
                )
            rel_section = (
                '<div class="section">'
                '<div class="section-title">Relatórios Gerados</div>'
                '<div class="section-body"><table>'
                '<thead><tr><th>Tipo</th><th>Arquivo</th><th>Hash SHA-256</th><th>Gerado em</th></tr></thead>'
                f'<tbody>{rel_rows}</tbody>'
                '</table></div></div>'
            )

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Integridade {self._hesc(report_number)}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Arial,sans-serif;font-size:13px;color:#1A1A1A;background:#F5F5F5}}
  .header{{background:#1A1A1A;color:#fff;padding:18px 24px;border-bottom:3px solid #C8A951}}
  .header h1{{font-size:20px;letter-spacing:1px}}
  .header p{{font-size:11px;color:#C8A951;margin-top:4px}}
  .container{{max-width:1100px;margin:24px auto;padding:0 16px}}
  .section{{background:#fff;border:1px solid #D6DBDF;border-radius:4px;margin-bottom:20px}}
  .section-title{{background:#1A1A1A;color:#fff;padding:8px 14px;font-size:13px;font-weight:bold;border-bottom:2px solid #C8A951}}
  .section-body{{padding:12px 14px}}
  .kv-table{{width:100%;border-collapse:collapse}}
  .kv-table td{{padding:5px 8px;border:1px solid #D6DBDF;font-size:12px}}
  .kv-table td:first-child{{background:#F7F4EA;font-weight:bold;width:200px}}
  table{{width:100%;border-collapse:collapse;font-size:11px}}
  thead th{{background:#1A1A1A;color:#fff;padding:6px 8px;text-align:left;border-bottom:2px solid #C8A951}}
  tbody tr:nth-child(even){{background:#F7F4EA}}
  tbody td{{padding:5px 8px;border:1px solid #D6DBDF;vertical-align:top;word-break:break-all}}
  .mono{{font-family:Courier,monospace;font-size:10px}}
  .small{{font-size:10px}}
  .badge{{display:inline-block;padding:6px 18px;border-radius:4px;font-size:15px;font-weight:bold;color:#fff}}
  .chain-info{{display:flex;align-items:center;gap:18px}}
  .count{{font-size:13px;color:#555}}
</style>
</head>
<body>
<div class="header">
  <h1>EDIFRAUDS / CORF / PCDF</h1>
  <p>Relatório de Integridade Final — {self._hesc(report_number)}</p>
</div>
<div class="container">

  <div class="section">
    <div class="section-title">Dados do Caso</div>
    <div class="section-body">
      <table class="kv-table">
        <tr><td>Caso</td><td>{self._hesc(caso.nome)}</td></tr>
        <tr><td>Processo</td><td>{self._hesc(caso.numero_processo or '-')}</td></tr>
        <tr><td>Analista</td><td>{self._hesc(caso.analista.get_full_name() or caso.analista.matricula)}</td></tr>
        <tr><td>Matrícula</td><td>{self._hesc(caso.analista.matricula)}</td></tr>
        <tr><td>Pasta</td><td>{self._hesc(caso.path_pasta)}</td></tr>
        <tr><td>Gerado em UTC</td><td>{self._hesc(generated_at.isoformat())}</td></tr>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Integridade do Software</div>
    <div class="section-body">
      <table class="kv-table">
        <tr><td>SHA-256 do Sistema</td><td class="mono">{self._hesc(software_hash)}</td></tr>
        <tr><td>Escopo</td><td>Todos os arquivos .py do projeto (exceto migrations e cache)</td></tr>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Verificação da Cadeia de Custódia</div>
    <div class="section-body">
      <div class="chain-info">
        <span class="badge" style="background:{status_color}">{self._hesc(status_text)}</span>
        <span class="count">{len(logs)} blocos verificados</span>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Sumário de Evidências</div>
    <div class="section-body">
      <table class="kv-table">
        <tr><td>Sites preservados</td><td>{len(sites)}</td></tr>
        <tr><td>Gravações de tela</td><td>{len(videos)}</td></tr>
        <tr><td>Capturas de tela</td><td>{len(screenshots)}</td></tr>
        <tr><td>Downloads monitorados</td><td>{len(downloads)}</td></tr>
        <tr><td>Relatórios gerados</td><td>{len(relatorios)}</td></tr>
        <tr><td>Total de blocos na cadeia</td><td>{len(logs)}</td></tr>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Tabela de Encadeamento (Blockchain)</div>
    <div class="section-body">
      <table>
        <thead><tr><th>#</th><th>Timestamp UTC</th><th>Ação</th><th>Hash Anterior</th><th>Hash Atual</th></tr></thead>
        <tbody>{chain_rows}</tbody>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Registro Cronológico de Ações</div>
    <div class="section-body">
      <table>
        <thead><tr><th>Timestamp UTC</th><th>Ação</th><th>Analista</th><th>Dados</th></tr></thead>
        <tbody>{log_rows}</tbody>
      </table>
    </div>
  </div>

  {sites_section}
  {rel_section}

</div>
</body>
</html>"""
        html_path.write_text(html, encoding='utf-8')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hash_software(self) -> str:
        base = Path(__file__).resolve().parent.parent.parent
        py_files = sorted(
            p for p in base.rglob('*.py')
            if 'migrations' not in p.parts
            and '__pycache__' not in p.parts
            and 'tests' not in p.parts
        )
        combined = hashlib.sha256()
        for f in py_files:
            try:
                combined.update(f.read_bytes())
            except OSError:
                pass
        return combined.hexdigest()

    @staticmethod
    def _pdf_esc(value: str) -> str:
        return (
            str(value)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('\n', '<br/>')
        )

    @staticmethod
    def _hesc(value: str) -> str:
        return (
            str(value)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )
