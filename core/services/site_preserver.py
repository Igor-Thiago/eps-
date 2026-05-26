import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from django.utils import timezone
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .hash_service import HashService
from .metadata_service import MetadataService


class SitePreservationError(Exception):
    default_message = 'Nao foi possivel preservar o site informado.'

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class SiteTimeoutError(SitePreservationError):
    default_message = 'Tempo limite excedido ao acessar o site.'


class SiteOfflineError(SitePreservationError):
    default_message = 'Site offline ou inacessivel no momento.'


@dataclass(frozen=True)
class SitePreservationResult:
    url: str
    final_url: str
    domain: str
    output_dir: Path
    html_path: Path
    screenshot_path: Path
    mhtml_path: Path
    metadata_path: Path
    hash_sha256: str
    status: int | None
    title: str
    technical_metadata: dict = field(default_factory=dict)


class SitePreserver:
    def __init__(self, timeout_ms=30000):
        self.timeout_ms = timeout_ms

    def preserve(self, url: str, case_path) -> SitePreservationResult:
        domain = self._domain_from_url(url)
        output_dir = self._build_output_dir(case_path, domain)
        html_path = output_dir / 'index.html'
        screenshot_path = output_dir / 'screenshot.png'
        mhtml_path = output_dir / 'pagina.mhtml'
        metadata_path = output_dir / 'metadata.json'

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(ignore_https_errors=True)
                page = context.new_page()

                response = page.goto(url, wait_until='networkidle', timeout=self.timeout_ms)
                if response is None:
                    raise SiteOfflineError()

                html_path.write_text(page.content(), encoding='utf-8')
                page.screenshot(path=str(screenshot_path), full_page=True)

                cdp_session = context.new_cdp_session(page)
                snapshot = cdp_session.send('Page.captureSnapshot', {'format': 'mhtml'})
                mhtml_path.write_text(snapshot['data'], encoding='utf-8')

                title = page.title()
                final_url = page.url
                status = response.status
                browser.close()
        except PlaywrightTimeoutError as exc:
            raise SiteTimeoutError() from exc
        except SitePreservationError:
            raise
        except PlaywrightError as exc:
            raise SiteOfflineError() from exc

        try:
            technical_metadata = MetadataService.collect(url)
        except Exception:
            technical_metadata = {}

        metadata = {
            'url': url,
            'final_url': final_url,
            'domain': domain,
            'status': status,
            'title': title,
            'captured_at': timezone.now().isoformat(),
            'artifacts': {
                'html': str(html_path),
                'screenshot': str(screenshot_path),
                'mhtml': str(mhtml_path),
            },
            'technical_metadata': technical_metadata,
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        hash_sha256 = HashService.hash_file(mhtml_path)

        return SitePreservationResult(
            url=url,
            final_url=final_url,
            domain=domain,
            output_dir=output_dir,
            html_path=html_path,
            screenshot_path=screenshot_path,
            mhtml_path=mhtml_path,
            metadata_path=metadata_path,
            hash_sha256=hash_sha256,
            status=status,
            title=title,
            technical_metadata=technical_metadata,
        )

    def _domain_from_url(self, url: str) -> str:
        hostname = urlparse(url).hostname or 'site'
        return re.sub(r'[^a-zA-Z0-9.-]+', '_', hostname).strip('._') or 'site'

    def _build_output_dir(self, case_path, domain: str) -> Path:
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(case_path) / 'sites' / domain / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
