import hashlib
import socket
import ssl
from urllib.parse import urlparse

import dns.resolver
import httpx


class MetadataService:
    TIMEOUT = 10

    @staticmethod
    def collect(url: str) -> dict:
        parsed = urlparse(url)
        domain = parsed.hostname or ''
        is_https = parsed.scheme.lower() == 'https'
        return {
            'whois_rdap': MetadataService._rdap(domain),
            'ssl': MetadataService._ssl_cert(domain) if is_https else {'disponivel': False, 'motivo': 'protocolo HTTP'},
            'http_headers': MetadataService._http_headers(url),
            'dns': MetadataService._dns_records(domain),
            'ip': MetadataService._resolve_ip(domain),
        }

    @staticmethod
    def _rdap(domain: str) -> dict:
        try:
            resp = httpx.get(
                f'https://rdap.org/domain/{domain}',
                timeout=MetadataService.TIMEOUT,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return {'disponivel': False, 'motivo': f'HTTP {resp.status_code}'}
            data = resp.json()

            registrant = None
            registrar = None
            creation = None
            expiration = None

            for entity in data.get('entities', []):
                roles = entity.get('roles', [])
                vcard_array = entity.get('vcardArray')
                name = None
                if vcard_array and len(vcard_array) > 1:
                    name = next(
                        (v[3] for v in vcard_array[1] if isinstance(v, list) and v[0] == 'fn'),
                        None,
                    )
                if 'registrant' in roles and name:
                    registrant = name
                if 'registrar' in roles and name:
                    registrar = name

            for event in data.get('events', []):
                action = event.get('eventAction', '')
                date = event.get('eventDate', '')
                if action == 'registration':
                    creation = date
                elif action == 'expiration':
                    expiration = date

            return {
                'disponivel': True,
                'nome_dominio': data.get('ldhName'),
                'status': data.get('status', []),
                'registrant': registrant,
                'registrar': registrar,
                'data_registro': creation,
                'data_expiracao': expiration,
            }
        except Exception as e:
            return {'disponivel': False, 'erro': str(e)}

    @staticmethod
    def _ssl_cert(domain: str) -> dict:
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=MetadataService.TIMEOUT) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    der = ssock.getpeercert(binary_form=True)
            fingerprint = hashlib.sha256(der).hexdigest()
            subject = dict(x[0] for x in cert.get('subject', []))
            issuer = dict(x[0] for x in cert.get('issuer', []))
            return {
                'disponivel': True,
                'subject': subject,
                'issuer': issuer,
                'not_before': cert.get('notBefore'),
                'not_after': cert.get('notAfter'),
                'fingerprint_sha256': fingerprint,
                'version': cert.get('version'),
            }
        except Exception as e:
            return {'disponivel': False, 'erro': str(e)}

    @staticmethod
    def _http_headers(url: str) -> dict:
        try:
            resp = httpx.head(
                url,
                timeout=MetadataService.TIMEOUT,
                follow_redirects=True,
                verify=False,
            )
            return {
                'disponivel': True,
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
            }
        except Exception as e:
            return {'disponivel': False, 'erro': str(e)}

    @staticmethod
    def _dns_records(domain: str) -> dict:
        records = {}
        for rtype in ('A', 'AAAA', 'MX', 'NS'):
            try:
                answers = dns.resolver.resolve(domain, rtype, lifetime=float(MetadataService.TIMEOUT))
                records[rtype] = [str(r) for r in answers]
            except Exception:
                records[rtype] = []
        return records

    @staticmethod
    def _resolve_ip(domain: str) -> str | None:
        try:
            return socket.gethostbyname(domain)
        except Exception:
            return None
