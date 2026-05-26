[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/B91zYAhm)
[![CI](https://github.com/FCTE-UNB-EPS5/sistema-de-preserva-o-e-coleta-de-vest-gios-digitais-grupo-22-1/actions/workflows/ci.yml/badge.svg)](https://github.com/FCTE-UNB-EPS5/sistema-de-preserva-o-e-coleta-de-vest-gios-digitais-grupo-22-1/actions/workflows/ci.yml)

# EDIFRAUDS — Sistema de Preservação e Coleta de Vestígios Digitais

> CORF / PCDF — UnB-FGA EPS 2026/1

Sistema interno para coleta e preservação de evidências digitais com validade jurídica (Lei nº 13.964/2019). Garante cadeia de custódia via hashing SHA-256, criptografia AES-256-GCM e trilha de auditoria encadeada (blockchain-like).

---

## Pré-requisitos

- Docker >= 24
- Docker Compose >= 2.20

---

## Setup (primeira vez)

```bash
# 1. Clone o repositório
git clone <url-do-repo>
cd sistema-de-preservacao-...

# 2. Crie o arquivo de variáveis de ambiente
cp .env.example .env

# 3. Suba os containers (primeira vez: adicione --build)
docker-compose up --build
```

O `entrypoint.sh` faz automaticamente:
1. Aguarda o PostgreSQL aceitar conexões
2. Roda `makemigrations` e `migrate`
3. Sobe o Django em `0.0.0.0:8000`

Quando pronto você verá:
```
app-1  | Starting development server at http://0.0.0.0:8000/
```

Acesse: **http://localhost:8000**

---

## Primeiro acesso

Ao abrir o sistema pela primeira vez sem nenhum admin cadastrado, a tela de login exibe um link **"Configurar primeiro acesso"** que redireciona para `/criar-admin/`.

Preencha os dados do administrador PCDF e clique em **Criar**. Em seguida, faça login normalmente.

Analistas comuns se cadastram em `/cadastro/` (acessível pelo link na tela de login) e ficam com role `ANALISTA` por padrão.

---

## Tipos de usuário

| Role | Acesso |
|------|--------|
| `ANALISTA` | Apenas os próprios casos e evidências |
| `ADMIN_PCDF` | Todos os casos e evidências do sistema |

---

## Fluxo de uso

1. **Login** — analista entra com matrícula e senha
2. **Novo caso** — preenche nome, número de processo e pasta de destino
3. **Coleta de evidências** dentro de um caso:
   - Preservar site (MHTML + PDF + screenshot + metadados)
   - Gravação de tela com áudio (FFmpeg)
   - Captura de tela manual ou automática (intervalo configurável)
   - Cópia forense de arquivo (copia + calcula hash + compacta em ZIP)
4. **Encerramento** — gera Relatório de Integridade (PDF + HTML) e Certidão (.docx) em um clique
5. **Download** — relatórios ficam listados no caso e podem ser baixados individualmente
6. **Auditoria** — toda ação fica registrada na cadeia de auditoria do caso

---

## Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/` | Redireciona para `/casos/` (autenticado) ou `/login/` |
| GET/POST | `/login/` | Tela de login (matrícula + senha) |
| GET/POST | `/logout/` | Encerra a sessão |
| GET/POST | `/cadastro/` | Cadastro de novo analista |
| GET/POST | `/criar-admin/` | Cria o primeiro administrador PCDF (só funciona sem admin cadastrado) |
| GET/POST | `/configuracoes/` | Configurações do analista (cabeçalho, assinatura, logotipo, intervalo de capturas) |
| GET | `/casos/` | Lista de casos do analista (ou todos, se admin) |
| GET/POST | `/casos/novo/` | Criar novo caso |
| GET | `/casos/<id>/` | Detalhe de um caso (evidências, ações, relatórios) |
| POST | `/casos/<id>/capturar-site/` | Preserva um site (MHTML + PDF + screenshot) |
| POST | `/casos/<id>/gravacao/iniciar/` | Inicia gravação de tela com áudio |
| POST | `/casos/<id>/gravacao/finalizar/` | Finaliza a gravação em andamento |
| POST | `/casos/<id>/capturas/criar/` | Captura de tela manual |
| POST | `/casos/<id>/relatorio-integridade/` | Gera Relatório de Integridade + Certidão |
| POST | `/casos/<id>/certidao/` | Gera apenas a Certidão (.docx) |
| POST | `/casos/<id>/copia-forense/` | Cópia forense de arquivo local |
| POST | `/casos/<id>/abrir-pasta/` | Abre a pasta do caso no gerenciador de arquivos |
| GET | `/casos/<id>/relatorios/<rel_id>/download/` | Download de um relatório gerado |

---

## Rodar os testes

```bash
# Todos os testes (recomendado — usa pytest)
docker-compose exec app python3 -m pytest

# Com saída verbosa
docker-compose exec app python3 -m pytest -v

# Módulo específico
docker-compose exec app python3 -m pytest core/tests/test_audit_logger.py -v
docker-compose exec app python3 -m pytest core/tests/test_certidao_service.py -v
docker-compose exec app python3 -m pytest core/tests/test_configuracao.py -v

# Com cobertura de código
docker-compose exec app python3 -m pytest --cov=core/services --cov-report=term-missing
```

### Cobertura dos módulos críticos

| Módulo | Cobertura |
|--------|-----------|
| `hash_service` | 100% |
| `audit_logger` | 100% |
| `certidao_service` | 97% |
| `screen_recording_service` | 96% |
| `screenshot_service` | 96% |
| `forensic_report_service` | 92% |
| `crypto_service` | 88% |
| `case_folder_service` | 89% |

### Suítes de teste

| Arquivo | O que testa |
|---------|-------------|
| `test_hash_service` | SHA-256 de arquivos, bytes e ZIPs |
| `test_audit_logger` | Cadeia de auditoria, linkagem de blocos, detecção de adulteração |
| `test_crypto_service` | Criptografia AES-256-GCM: cifragem, decifragem, chaves erradas |
| `test_certidao_service` | Geração de .docx, hash do arquivo, falhas, view POST/403/405 |
| `test_configuracao` | Modelo ConfiguracaoAnalista, ConfiguracaoView GET/POST, isolamento por analista |
| `test_forensic_report_service` | Geração de PDF de preservação de site |
| `test_metadata_service` | Extração de metadados de arquivos |
| `test_site_capture` | View de preservação de site |
| `test_screenshot_capture` | View de captura de tela |
| `test_screen_recording` | Início e finalização de gravação |
| `test_auth_access` | Login, logout, registro, controle de acesso por caso |
| `test_case_management` | Criação, listagem, detalhe, statusbar de caso ativo |
| `test_validators` | Validação de extensões de arquivo |

---

## Arquitetura

```
.
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh               # setup automático do container
├── requirements.txt
├── pytest.ini                  # configuração do pytest-django
├── pcdf/                       # configurações Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── core/                       # app principal
    ├── models.py               # Analista, ConfiguracaoAnalista, Caso,
    │                           # Evidencia, AuditLog, RelatorioGerado
    ├── views.py                # todas as views (CBV)
    ├── forms.py                # formulários com validação
    ├── urls.py                 # roteamento da app
    ├── services/
    │   ├── hash_service.py            # SHA-256 de arquivo, bytes e ZIP
    │   ├── crypto_service.py          # AES-256-GCM (cifragem/decifragem)
    │   ├── audit_logger.py            # trilha de auditoria encadeada
    │   ├── case_folder_service.py     # criação de pastas de caso
    │   ├── site_preserver.py          # captura de site (Playwright)
    │   ├── screenshot_service.py      # captura de tela (Playwright)
    │   ├── screen_recording_service.py # gravação com FFmpeg
    │   ├── forensic_copy_service.py   # cópia forense + ZIP
    │   ├── forensic_report_service.py # relatório PDF de preservação
    │   ├── integrity_report_service.py # relatório de integridade da cadeia
    │   ├── certidao_service.py        # certidão .docx (python-docx)
    │   ├── metadata_service.py        # extração de metadados EXIF/arquivo
    │   └── download_watcher_service.py # monitoramento de downloads
    └── tests/
        ├── test_hash_service.py
        ├── test_crypto_service.py
        ├── test_audit_logger.py
        ├── test_certidao_service.py
        ├── test_configuracao.py
        ├── test_forensic_report_service.py
        ├── test_metadata_service.py
        ├── test_site_capture.py
        ├── test_screenshot_capture.py
        ├── test_screen_recording.py
        ├── test_auth_access.py
        ├── test_case_management.py
        └── test_validators.py
```

### Cadeia de custódia

Cada ação relevante (abertura de caso, preservação de site, geração de relatório, etc.) gera um bloco `AuditLog` com:
- `timestamp_utc` — momento exato da ação (UTC)
- `hash_bloco_anterior` — SHA-256 do bloco anterior da cadeia
- `hash_bloco_atual` — SHA-256 deste bloco (inclui ação + dados + timestamp + hash anterior)
- `dados_json` — metadados específicos da ação

Qualquer adulteração em um bloco (dados, hash) é detectada pelo `AuditLogger.verificar_cadeia()` e reportada no Relatório de Integridade.

---

## Comandos úteis

```bash
# Subir em background
docker-compose up -d

# Parar (preserva o banco)
docker-compose down

# Apagar tudo (banco incluído)
docker-compose down -v

# Logs da app em tempo real
docker-compose logs -f app

# Shell Django
docker-compose exec app python manage.py shell

# Aplicar migrations manualmente
docker-compose exec app python manage.py migrate
```

---

## Variáveis de ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SECRET_KEY` | Chave secreta Django | `django-insecure-...` |
| `DEBUG` | Modo de depuração | `True` |
| `DB_NAME` | Nome do banco PostgreSQL | `investigacao` |
| `DB_USER` | Usuário do banco | `pcdf_admin` |
| `DB_PASSWORD` | Senha do banco | `pcdf_secure_pass` |
| `DB_HOST` | Host do banco (serviço Docker) | `db` |
| `DB_PORT` | Porta do banco | `5432` |
| `CASES_ROOT` | Pasta base dos casos | `/app/media/casos` |

---

## Pipeline CI

O pipeline (`.github/workflows/ci.yml`) roda em cada push e PR:

- **Bandit** — análise estática de segurança (SAST): falha em severidade HIGH/MEDIUM
- **Safety** — verificação de dependências com CVEs conhecidas (SCA)
- **Testes** — suite completa com pytest-django

---

## Roadmap

| Fase | Issues | Status |
|------|--------|--------|
| Fase 0 — Setup e Infraestrutura | #1–4 | Concluído |
| Fase 1 — MVP: Preservação de Sites | #5–10 | Concluído |
| Fase 2 — Gravação e Capturas | #11–15 | Concluído |
| Fase 3 — Polimento e Entrega | #16–20 | Concluído |
