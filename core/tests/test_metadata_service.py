from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from core.services.metadata_service import MetadataService


class RDAPTest(SimpleTestCase):
    def _mock_rdap_response(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            'ldhName': 'example.com',
            'status': ['active'],
            'entities': [
                {
                    'roles': ['registrant'],
                    'vcardArray': ['vcard', [['fn', {}, 'text', 'Empresa Exemplo Ltda']]],
                },
                {
                    'roles': ['registrar'],
                    'vcardArray': ['vcard', [['fn', {}, 'text', 'Registrar Brasil']]],
                },
            ],
            'events': [
                {'eventAction': 'registration', 'eventDate': '2010-03-15T00:00:00Z'},
                {'eventAction': 'expiration', 'eventDate': '2030-03-15T00:00:00Z'},
            ],
        }
        return resp

    def test_rdap_retorna_registrante_e_datas(self):
        with patch('core.services.metadata_service.httpx.get', return_value=self._mock_rdap_response()):
            result = MetadataService._rdap('example.com')

        self.assertTrue(result['disponivel'])
        self.assertEqual(result['registrant'], 'Empresa Exemplo Ltda')
        self.assertEqual(result['registrar'], 'Registrar Brasil')
        self.assertEqual(result['data_registro'], '2010-03-15T00:00:00Z')
        self.assertEqual(result['data_expiracao'], '2030-03-15T00:00:00Z')
        self.assertEqual(result['nome_dominio'], 'example.com')
        self.assertIn('active', result['status'])

    def test_rdap_status_nao_200_marca_indisponivel(self):
        resp = MagicMock()
        resp.status_code = 404
        with patch('core.services.metadata_service.httpx.get', return_value=resp):
            result = MetadataService._rdap('dominio-inexistente.br')

        self.assertFalse(result['disponivel'])
        self.assertIn('motivo', result)

    def test_rdap_excecao_nao_quebra_fluxo(self):
        with patch('core.services.metadata_service.httpx.get', side_effect=Exception('timeout')):
            result = MetadataService._rdap('gov.br')

        self.assertFalse(result['disponivel'])
        self.assertIn('erro', result)

    def test_rdap_sem_entidades_retorna_campos_nulos(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {'ldhName': 'sem-entidades.com', 'status': [], 'entities': [], 'events': []}
        with patch('core.services.metadata_service.httpx.get', return_value=resp):
            result = MetadataService._rdap('sem-entidades.com')

        self.assertTrue(result['disponivel'])
        self.assertIsNone(result['registrant'])
        self.assertIsNone(result['data_registro'])


class SSLCertTest(SimpleTestCase):
    def _setup_ssl_mock(self, cert, der):
        mock_ssock = MagicMock()
        mock_ssock.getpeercert.side_effect = lambda binary_form=False: der if binary_form else cert
        mock_ssock.__enter__ = lambda s: s
        mock_ssock.__exit__ = MagicMock(return_value=False)

        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)

        mock_ctx = MagicMock()
        mock_ctx.wrap_socket.return_value = mock_ssock
        return mock_sock, mock_ctx

    def test_ssl_retorna_emissor_validade_fingerprint(self):
        import hashlib
        cert = {
            'subject': ((('commonName', 'example.com'),),),
            'issuer': ((('organizationName', 'DigiCert Inc'),),),
            'notBefore': 'Jan  1 00:00:00 2024 GMT',
            'notAfter': 'Jan  1 00:00:00 2025 GMT',
            'version': 3,
        }
        der = b'der_bytes_mock'
        mock_sock, mock_ctx = self._setup_ssl_mock(cert, der)

        with patch('core.services.metadata_service.socket.create_connection', return_value=mock_sock), \
             patch('core.services.metadata_service.ssl.create_default_context', return_value=mock_ctx):
            result = MetadataService._ssl_cert('example.com')

        self.assertTrue(result['disponivel'])
        self.assertEqual(result['issuer']['organizationName'], 'DigiCert Inc')
        self.assertEqual(result['subject']['commonName'], 'example.com')
        self.assertEqual(result['not_before'], 'Jan  1 00:00:00 2024 GMT')
        self.assertEqual(result['not_after'], 'Jan  1 00:00:00 2025 GMT')
        self.assertEqual(result['fingerprint_sha256'], hashlib.sha256(der).hexdigest())
        self.assertEqual(result['version'], 3)

    def test_ssl_indisponivel_nao_quebra_fluxo(self):
        with patch('core.services.metadata_service.socket.create_connection', side_effect=ConnectionRefusedError()):
            result = MetadataService._ssl_cert('offline.example.com')

        self.assertFalse(result['disponivel'])
        self.assertIn('erro', result)

    def test_ssl_nao_coletado_para_http(self):
        result = MetadataService.collect('http://example.com')

        self.assertFalse(result['ssl']['disponivel'])
        self.assertEqual(result['ssl']['motivo'], 'protocolo HTTP')


class HTTPHeadersTest(SimpleTestCase):
    def test_headers_capturados_com_status_e_cabecalhos(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'content-type': 'text/html; charset=utf-8', 'server': 'nginx/1.24'}

        with patch('core.services.metadata_service.httpx.head', return_value=mock_resp):
            result = MetadataService._http_headers('https://example.com')

        self.assertTrue(result['disponivel'])
        self.assertEqual(result['status_code'], 200)
        self.assertEqual(result['headers']['server'], 'nginx/1.24')
        self.assertIn('content-type', result['headers'])

    def test_headers_indisponivel_nao_quebra_fluxo(self):
        with patch('core.services.metadata_service.httpx.head', side_effect=Exception('connection error')):
            result = MetadataService._http_headers('https://offline.example.com')

        self.assertFalse(result['disponivel'])
        self.assertIn('erro', result)


class DNSRecordsTest(SimpleTestCase):
    def test_dns_retorna_registros_a_e_ns(self):
        def mock_resolve(domain, rtype, **kwargs):
            mocks = {
                'A': ['93.184.216.34'],
                'NS': ['a.iana-servers.net.', 'b.iana-servers.net.'],
            }
            if rtype in mocks:
                return [MagicMock(__str__=lambda s, v=v: v) for v in mocks[rtype]]
            raise Exception('NXDOMAIN')

        with patch('core.services.metadata_service.dns.resolver.resolve', side_effect=mock_resolve):
            result = MetadataService._dns_records('example.com')

        self.assertEqual(result['A'], ['93.184.216.34'])
        self.assertEqual(len(result['NS']), 2)
        self.assertEqual(result['AAAA'], [])
        self.assertEqual(result['MX'], [])

    def test_dns_tipo_inexistente_retorna_lista_vazia(self):
        with patch('core.services.metadata_service.dns.resolver.resolve', side_effect=Exception('NXDOMAIN')):
            result = MetadataService._dns_records('sem-registro.example.com')

        self.assertEqual(result['A'], [])
        self.assertEqual(result['AAAA'], [])
        self.assertEqual(result['MX'], [])
        self.assertEqual(result['NS'], [])


class ResolveIPTest(SimpleTestCase):
    def test_resolve_ip_retorna_endereco(self):
        with patch('core.services.metadata_service.socket.gethostbyname', return_value='93.184.216.34'):
            result = MetadataService._resolve_ip('example.com')

        self.assertEqual(result, '93.184.216.34')

    def test_resolve_ip_falha_graciosamente(self):
        with patch('core.services.metadata_service.socket.gethostbyname', side_effect=OSError('Name resolution failed')):
            result = MetadataService._resolve_ip('nao-existe.invalid')

        self.assertIsNone(result)


class CollectTest(SimpleTestCase):
    def test_collect_retorna_todas_as_chaves_obrigatorias(self):
        with patch.object(MetadataService, '_rdap', return_value={'disponivel': True}), \
             patch.object(MetadataService, '_ssl_cert', return_value={'disponivel': True}), \
             patch.object(MetadataService, '_http_headers', return_value={'disponivel': True, 'status_code': 200, 'headers': {}}), \
             patch.object(MetadataService, '_dns_records', return_value={'A': [], 'AAAA': [], 'MX': [], 'NS': []}), \
             patch.object(MetadataService, '_resolve_ip', return_value='1.2.3.4'):
            result = MetadataService.collect('https://example.com')

        self.assertIn('whois_rdap', result)
        self.assertIn('ssl', result)
        self.assertIn('http_headers', result)
        self.assertIn('dns', result)
        self.assertIn('ip', result)

    def test_collect_chama_ssl_para_https(self):
        with patch.object(MetadataService, '_rdap', return_value={}), \
             patch.object(MetadataService, '_ssl_cert', return_value={'disponivel': True}) as mock_ssl, \
             patch.object(MetadataService, '_http_headers', return_value={}), \
             patch.object(MetadataService, '_dns_records', return_value={}), \
             patch.object(MetadataService, '_resolve_ip', return_value=None):
            MetadataService.collect('https://example.com')

        mock_ssl.assert_called_once_with('example.com')

    def test_collect_nao_chama_ssl_para_http(self):
        with patch.object(MetadataService, '_rdap', return_value={}), \
             patch.object(MetadataService, '_ssl_cert', return_value={}) as mock_ssl, \
             patch.object(MetadataService, '_http_headers', return_value={}), \
             patch.object(MetadataService, '_dns_records', return_value={}), \
             patch.object(MetadataService, '_resolve_ip', return_value=None):
            result = MetadataService.collect('http://example.com')

        mock_ssl.assert_not_called()
        self.assertFalse(result['ssl']['disponivel'])
