# Issues do Projeto — Sistema de Preservação e Coleta de Vestígios Digitais

> EDIFRAUDS / CORF / PCDF — UnB-FGA EPS 2026/1

---

# Fase 0 — Setup e Infraestrutura

---

### Issue #1 — Dev A — Backend & Segurança

**Título:** `[SETUP] Configurar projeto Django + Docker`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Criar o projeto Django com app principal (`core`), Dockerfile com todas as dependências Python, ajustar o `docker-compose.yml` existente para integrar o serviço `app`, configurar `settings.py` com conexão ao PostgreSQL e rodar as migrations iniciais.

## Tarefas

- [ ] Criar projeto Django (`django-admin startproject`) com app `core`
- [ ] Criar `Dockerfile` com Python 3.12, instalação de dependências via `requirements.txt`
- [ ] Ajustar `docker-compose.yml` para buildar o Dockerfile e expor porta 8000
- [ ] Configurar `settings.py`: `DATABASES` apontando para `db` via `DATABASE_URL`
- [ ] Criar `requirements.txt` com Django, psycopg2-binary, pydantic, cryptography
- [ ] Rodar `python manage.py migrate` no container e validar conexão com PostgreSQL
- [ ] Criar superusuário de teste (`createsuperuser`)

## Critérios de Aceitação

- [ ] `docker-compose up --build` sobe sem erros
- [ ] Django responde em `http://localhost:8000`
- [ ] PostgreSQL aceita conexão e migrations rodam com sucesso
- [ ] Admin Django acessível em `/admin`

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Alta |
| **Story Points** | 3 |
| **Fase** | Fase 0 |
| **Requisitos** | RNF04, RNF06 |
| **Labels** | setup, backend, devops |

</details>

---

### Issue #2 — Dev A — Backend & Segurança

**Título:** `[SETUP] Modelagem do Banco de Dados (Models Django)`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Criar os models Django que sustentam toda a aplicação: `Analista`, `Caso`, `Evidencia`, `AuditLog` e `RelatorioGerado`. Implementar relacionamentos, campos de hash SHA-256, timestamps UTC e `JSONField` para metadados. Registrar todos os models no Django Admin.

## Tarefas

- [ ] Criar model `Analista` (id, nome, matrícula, senha_hash, created_at)
- [ ] Criar model `Caso` (id, nome, numero_processo, analista_fk, path_pasta, created_at, updated_at)
- [ ] Criar model `Evidencia` (id, caso_fk, tipo_enum, hash_sha256, path_arquivo, metadados_json, created_at)
- [ ] Criar model `AuditLog` (id, caso_fk, analista_fk, acao, timestamp_utc, hash_bloco_anterior, hash_bloco_atual, dados_json)
- [ ] Criar model `RelatorioGerado` (id, caso_fk, tipo, hash_sha256, path_arquivo, created_at)
- [ ] Definir choices/enum para tipos de evidência: SITE, VIDEO, SCREENSHOT, COPIA_FORENSE, DOWNLOAD
- [ ] Criar e rodar migrations
- [ ] Registrar todos os models no `admin.py` com list_display e filtros

## Critérios de Aceitação

- [ ] Todos os 5 models criados com campos documentados
- [ ] Migrations rodam sem erro no container
- [ ] `JSONField` funciona para metadados (testar via shell)
- [ ] Todos os timestamps usam UTC (`auto_now_add=True` com `USE_TZ=True`)
- [ ] Django Admin lista e filtra todos os models corretamente
- [ ] Relacionamentos FK funcionam com `on_delete` adequado

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Alta |
| **Story Points** | 5 |
| **Fase** | Fase 0 |
| **Requisitos** | RF03, RF09, RF10, RNF09 |
| **Labels** | setup, backend, database |

</details>

---

### Issue #3 — Dev B — Frontend & Integração

**Título:** `[SETUP] Pipeline CI/CD com Bandit, Safety e Testes`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Configurar GitHub Actions para rodar automaticamente em cada push e pull request: Bandit (análise estática de segurança — SAST), Safety (verificação de dependências vulneráveis — SCA) e pytest para testes unitários.

## Tarefas

- [ ] Criar `.github/workflows/ci.yml`
- [ ] Configurar job `security`: rodar `bandit -r src/ -ll` (falhar em HIGH/MEDIUM)
- [ ] Configurar job `dependencies`: rodar `safety check -r requirements.txt`
- [ ] Configurar job `tests`: rodar `pytest` com relatório de cobertura
- [ ] Garantir que o pipeline falha se Bandit encontrar severidade HIGH
- [ ] Adicionar badge de status no README

## Critérios de Aceitação

- [ ] Pipeline roda automaticamente em cada push e PR
- [ ] Bandit analisa todo o código Python do projeto
- [ ] Safety checa `requirements.txt` sem CVEs críticas
- [ ] pytest roda e reporta resultados (mesmo que inicialmente sem testes)
- [ ] Pipeline falha visivelmente se houver vulnerabilidade HIGH
- [ ] Badge de CI visível no README

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Alta |
| **Story Points** | 3 |
| **Fase** | Fase 0 |
| **Requisitos** | RNF05 |
| **Labels** | setup, devops, seguranca |

</details>

---

### Issue #4 — Dev B — Frontend & Integração

**Título:** `[SETUP] Sistema de Autenticação e Controle de Acesso`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar cadastro e login de analistas usando Django Auth. Garantir que cada analista só acessa seus próprios casos (isolation). Incluir validação de entrada com Pydantic seguindo o padrão do `olaseguranca.py` (bloquear extensões perigosas, validar campos).

## Tarefas

- [ ] Criar views de registro e login (Django Auth ou DRF)
- [ ] Criar template/página de login com identidade visual PCDF
- [ ] Implementar middleware/mixin que filtra `Caso.objects.filter(analista=request.user)`
- [ ] Criar serializer/validator Pydantic para validação de entrada (extensões proibidas: .vbs, .exe, .bat, .sh)
- [ ] Implementar logout e redirecionamento
- [ ] Criar testes: login válido, login inválido, acesso a caso alheio retorna 403

## Critérios de Aceitação

- [ ] Analista consegue se cadastrar com nome, matrícula e senha
- [ ] Analista faz login e é redirecionado para tela inicial
- [ ] Listagem de casos mostra SOMENTE os casos do analista logado
- [ ] Tentativa de acessar caso de outro analista retorna 403 Forbidden
- [ ] Pydantic bloqueia upload de arquivos com extensões perigosas
- [ ] Senhas armazenadas com hash (nunca plaintext)

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Alta |
| **Story Points** | 5 |
| **Fase** | Fase 0 |
| **Requisitos** | RNF04, RNF10 |
| **Labels** | setup, backend, seguranca |

</details>

# Fase 1 — MVP: Preservação de Sites

---

### Issue #5 — Dev B — Frontend & Integração

**Título:** `[MVP] Motor de Captura de Sites (Playwright)`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar serviço que recebe uma URL e realiza a preservação completa do site: renderizar a página com Playwright (para suportar JavaScript), salvar HTML completo, CSS, screenshot em PNG e assets estáticos. Todos os artefatos devem ser salvos na estrutura de pastas do caso.

## Tarefas

- [ ] Instalar e configurar Playwright no container Docker
- [ ] Criar serviço `SitePreserver` que recebe URL e path do caso
- [ ] Capturar HTML completo renderizado (`page.content()`)
- [ ] Capturar screenshot full-page em PNG (`page.screenshot(full_page=True)`)
- [ ] Salvar MHTML ou HTML + CSS inline para renderização offline
- [ ] Criar pasta `sites/<dominio>/` dentro do caso
- [ ] Tratar erros: timeout, site offline, certificado inválido
- [ ] Criar view/endpoint que recebe URL do usuário e dispara a captura

## Critérios de Aceitação

- [ ] Captura HTML + CSS de sites com e sem JavaScript
- [ ] Screenshot PNG full-page gerada automaticamente
- [ ] Arquivo HTML renderizado abre no navegador e é visualmente similar ao original
- [ ] Funciona com sites HTTP e HTTPS
- [ ] Erros (timeout, offline) exibem mensagem amigável ao usuário
- [ ] Artefatos salvos em `sites/<dominio>/` dentro da pasta do caso

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Alta |
| **Story Points** | 8 |
| **Fase** | Fase 1 |
| **Requisitos** | RF01 |
| **Labels** | feature, core, sites |

</details>

---

### Issue #6 — Dev A — Backend & Segurança

**Título:** `[MVP] Coleta de Metadados do Site (WHOIS, SSL, HTTP)`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Ao preservar um site, coletar automaticamente todos os metadados técnicos relevantes: WHOIS/RDAP do domínio, certificado SSL (emissor, validade, fingerprint), headers HTTP completos, DNS records (A, AAAA, MX, NS) e IP do servidor. Armazenar como JSON na `Evidencia`.

## Tarefas

- [ ] Implementar coleta WHOIS/RDAP usando `python-whois` ou `httpx` para RDAP
- [ ] Implementar extração de certificado SSL via `ssl` + `socket` (emissor, validade, fingerprint SHA-256)
- [ ] Coletar headers HTTP completos da resposta (via `httpx` ou `requests`)
- [ ] Coletar DNS records (A, AAAA, MX, NS) via `dnspython`
- [ ] Resolver IP do servidor
- [ ] Montar JSON estruturado com todos os metadados
- [ ] Salvar JSON na pasta do caso e no campo `metadados_json` da `Evidencia`
- [ ] Tratar domínios que não retornam WHOIS (ex: `.gov.br`)

## Critérios de Aceitação

- [ ] WHOIS retorna registrante, data de registro e expiração (quando disponível)
- [ ] SSL retorna emissor, validade e fingerprint SHA-256
- [ ] Headers HTTP completos armazenados
- [ ] DNS (A, AAAA, MX, NS) coletados
- [ ] Metadados salvos como JSON legível no banco e na pasta do caso
- [ ] Domínios sem WHOIS não quebram o fluxo (registra como indisponível)

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Alta |
| **Story Points** | 5 |
| **Fase** | Fase 1 |
| **Requisitos** | RF02 |
| **Labels** | feature, core, sites |

</details>

---

### Issue #7 — Dev A — Backend & Segurança

**Título:** `[MVP] Motor de Hashing SHA-256 e Cadeia de Auditoria`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar o serviço central de integridade: gerar hash SHA-256 de cada arquivo imediatamente após coleta, criar registro encadeado no `AuditLog` onde cada entrada referencia o hash da anterior (blockchain-like), e gerar hash do ZIP de evidências. Este serviço é consumido por TODAS as outras features.

## Tarefas

- [ ] Criar serviço `HashService.hash_file(path) -> str` usando `hashlib.sha256`
- [ ] Criar serviço `HashService.hash_bytes(data) -> str` para dados em memória
- [ ] Implementar `AuditLogger.log(caso, acao, dados)` que:
  -  Busca o último `AuditLog` do caso para pegar `hash_bloco_atual`
  -  Calcula o novo hash do bloco (hash do anterior + ação + timestamp + dados)
  -  Cria novo registro com `hash_bloco_anterior` e `hash_bloco_atual`
- [ ] Criar função `verificar_cadeia(caso)` que percorre todos os blocos e valida o encadeamento
- [ ] Criar função para zipar evidências e gerar hash do ZIP
- [ ] Criar testes unitários: hash correto, cadeia válida, adulteração detectada

## Critérios de Aceitação

- [ ] Hash SHA-256 gerado corretamente para qualquer arquivo
- [ ] Cada `AuditLog` referencia o hash do bloco anterior
- [ ] `verificar_cadeia()` retorna `True` para cadeia íntegra
- [ ] `verificar_cadeia()` retorna `False` se qualquer bloco for adulterado
- [ ] ZIP de evidências gerado com hash próprio
- [ ] Log registra timestamp UTC, ação, analista e caso
- [ ] Primeiro bloco da cadeia tem `hash_bloco_anterior = None`

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Alta |
| **Story Points** | 8 |
| **Fase** | Fase 1 |
| **Requisitos** | RF03, RF09, RNF02 |
| **Labels** | feature, core, seguranca |

</details>

---

### Issue #8 — Dev A — Backend & Segurança

**Título:** `[MVP] Criptografia AES-256 para Evidências em Repouso`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar criptografia AES-256-GCM para proteger os arquivos de evidência armazenados em disco. A chave é derivada por caso (usando PBKDF2 ou similar). Evidências são cifradas após o hash ser calculado (hash do original, não do cifrado) e decifradas sob demanda.

## Tarefas

- [ ] Implementar `CryptoService.encrypt_file(path, key)` usando AES-256-GCM (lib `cryptography`)
- [ ] Implementar `CryptoService.decrypt_file(path, key) -> bytes`
- [ ] Derivar chave por caso usando PBKDF2 com salt aleatório
- [ ] Armazenar salt no banco (model `Caso`) — NUNCA a chave
- [ ] Garantir que o hash SHA-256 é calculado ANTES da cifração
- [ ] Tratar erro de decifração com chave errada (mensagem amigável)
- [ ] Criar testes: cifrar → decifrar = original, chave errada falha, hash bate com original

## Critérios de Aceitação

- [ ] Arquivos de evidência salvos cifrados no disco (não legíveis sem chave)
- [ ] Decifração retorna o arquivo original idêntico (hash confere)
- [ ] Chave nunca armazenada em plaintext — só o salt
- [ ] Tentativa de decifrar com chave errada falha sem crash
- [ ] Hash SHA-256 é do arquivo ORIGINAL (antes de cifrar)
- [ ] GCM authentication tag verificada na decifração

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Alta |
| **Story Points** | 5 |
| **Fase** | Fase 1 |
| **Requisitos** | RNF01 |
| **Labels** | feature, core, seguranca |

</details>

---

### Issue #9 — Dev B — Frontend & Integração

**Título:** `[MVP] Gestão de Casos e Estrutura de Pastas`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar a criação e gestão de casos com geração automática da estrutura de pastas. Interface para criar novo caso, listar casos existentes (somente do analista logado), retomar caso e acessar pasta do caso.

## Tarefas

- [ ] Criar view de listagem de casos (tela inicial após login)
- [ ] Criar view/formulário para novo caso (nome ou nºmero do processo)
- [ ] Ao criar caso, gerar estrutura de pastas automaticamente:
  -  `<path>/<nome_caso>/sites/`
  -  `<path>/<nome_caso>/gravacoes/`
  -  `<path>/<nome_caso>/capturas/`
  -  `<path>/<nome_caso>/downloads/`
  -  `<path>/<nome_caso>/copias_forenses/`
  -  `<path>/<nome_caso>/integridade/`
- [ ] Implementar botão “Retomar caso” que abre o caso existente
- [ ] Implementar link para abrir pasta do caso no explorador de arquivos
- [ ] Mostrar nome do caso aberto no rodapé/barra inferior da interface

## Critérios de Aceitação

- [ ] Tela inicial lista casos do analista com nome, data e último acesso
- [ ] Criar caso gera todas as 6 subpastas automaticamente
- [ ] Retomar caso funciona e carrega o contexto correto
- [ ] Link para pasta do caso abre no explorador
- [ ] Nome do caso visível na barra inferior
- [ ] Path de salvamento configurável (pasta padrão ou personalizada)

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Alta |
| **Story Points** | 5 |
| **Fase** | Fase 1 |
| **Requisitos** | RF10 |
| **Labels** | feature, core, ui |

</details>

---

### Issue #10 — Dev B — Frontend & Integração

**Título:** `[MVP] Geração de Relatório Forense em PDF (Sites)`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Gerar relatório PDF completo ao preservar um site. O relatório deve conter: cabeçalho EDIFRAUDS/CORF/PCDF, dados do caso, URL preservada, screenshot embutida, metadados técnicos (WHOIS, SSL, HTTP, DNS), hashes SHA-256 de todos os artefatos e timestamps UTC. Usar ReportLab ou WeasyPrint.

## Tarefas

- [ ] Escolher e configurar lib de PDF (ReportLab ou WeasyPrint)
- [ ] Criar template de relatório com cabeçalho EDIFRAUDS/CORF/PCDF
- [ ] Aplicar paleta de cores: preto (#1A1A1A), branco, dourado (#C8A951)
- [ ] Seção: Dados do Caso (nome, processo, analista, data)
- [ ] Seção: URL preservada e screenshot embutida no PDF
- [ ] Seção: Metadados Técnicos (WHOIS, SSL, HTTP, DNS) formatados
- [ ] Seção: Tabela de Hashes SHA-256 de todos os artefatos
- [ ] Seção: Timestamp UTC de coleta
- [ ] Numeração de relatório sequencial
- [ ] Salvar PDF na subpasta do site dentro do caso
- [ ] Registrar `RelatorioGerado` no banco com hash do PDF

## Critérios de Aceitação

- [ ] PDF gerado com cabeçalho EDIFRAUDS/CORF/PCDF legível
- [ ] Screenshot do site visível dentro do PDF
- [ ] Todos os hashes SHA-256 presentes e verificavelmente corretos
- [ ] Metadados WHOIS e SSL formatados de forma legível
- [ ] Timestamps UTC em todas as seções
- [ ] Cores preto/branco/dourado aplicadas consistentemente
- [ ] PDF salvo na pasta correta e registrado no banco

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Alta |
| **Story Points** | 8 |
| **Fase** | Fase 1 |
| **Requisitos** | RF08, RNF08, RNF09 |
| **Labels** | feature, core, relatorio |

</details>

# Fase 2 — Gravação e Capturas

---

### Issue #11 — Dev B — Frontend & Integração

**Título:** `[GRAVACAO] Gravação de Tela com Áudio`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar gravação de tela capturando vídeo + áudio do sistema (mixagem estéreo) e microfone. O usuário deve poder selecionar dispositivos de áudio, iniciar e parar a gravação. Ao finalizar, gerar hash SHA-256 do vídeo e registrar no AuditLog.

## Tarefas

- [ ] Pesquisar e implementar captura de tela (FFmpeg, PyAutoGUI ou OBS WebSocket)
- [ ] Implementar seleção de dispositivos de áudio (listagem via sistema)
- [ ] Capturar áudio do sistema (mixagem estéreo) + microfone simultaneamente
- [ ] Botão Iniciar/Parar gravação na interface
- [ ] Ao parar: salvar vídeo na pasta `gravacoes/` do caso
- [ ] Chamar `HashService.hash_file()` no vídeo gerado
- [ ] Registrar início e fim da gravação no `AuditLog`
- [ ] Criar `Evidencia` do tipo VIDEO com hash e metadados

## Critérios de Aceitação

- [ ] Gravação de tela com áudio funciona e gera arquivo de vídeo válido
- [ ] Usuário consegue selecionar dispositivos de áudio
- [ ] Hash SHA-256 gerado automaticamente ao finalizar gravação
- [ ] Vídeo salvo na subpasta `gravacoes/` do caso
- [ ] AuditLog registra ações de início e fim com timestamps UTC
- [ ] Vídeo reproduzível em player padrão (MP4/WebM)

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Alta |
| **Story Points** | 8 |
| **Fase** | Fase 2 |
| **Requisitos** | RF04 |
| **Labels** | feature, gravacao |

</details>

---

### Issue #12 — Dev B — Frontend & Integração

**Título:** `[GRAVACAO] Capturas de Tela (Manual + Periódica)`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar captura de screenshots de duas formas: manual (botão na interface ou atalho de teclado) e periódica (intervalo configurável: 5s, 10s, 30s ou desativado). Cada screenshot recebe hash SHA-256. Prints durante gravação são anexados ao relatório do vídeo; fora da gravação, geram relatório individual.

## Tarefas

- [ ] Implementar captura de screenshot manual (botão + atalho de teclado)
- [ ] Implementar captura periódica com intervalo configurável (5s, 10s, 30s, desativado)
- [ ] Salvar screenshots na pasta `capturas/` do caso
- [ ] Gerar hash SHA-256 de cada screenshot
- [ ] Se gravação ativa: marcar screenshot como vinculada ao vídeo (para incluir no relatório do vídeo)
- [ ] Se gravação inativa: gerar relatório PDF individual da screenshot
- [ ] Registrar no AuditLog cada captura

## Critérios de Aceitação

- [ ] Screenshot manual via botão e atalho de teclado funciona
- [ ] Screenshot periódica dispara no intervalo configurado
- [ ] Cada print tem hash SHA-256 individual
- [ ] Prints durante gravação aparecem no relatório do vídeo
- [ ] Prints fora de gravação geram relatório PDF próprio
- [ ] Configuração de intervalo persist entre sessões

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Média |
| **Story Points** | 5 |
| **Fase** | Fase 2 |
| **Requisitos** | RF05 |
| **Labels** | feature, gravacao |

</details>

---

### Issue #13 — Dev A — Backend & Segurança

**Título:** `[GRAVACAO] Cópia Forense de Arquivos Locais`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar seleção de um ou mais arquivos locais para cópia forense: copiar para pasta do caso, gerar hash SHA-256 de cada arquivo individualmente e do ZIP resultante, extrair metadados (EXIF para imagens incluindo geolocalização) e gerar relatório.

## Tarefas

- [ ] Criar interface de seleção de múltiplos arquivos
- [ ] Copiar arquivos selecionados para `copias_forenses/` do caso
- [ ] Gerar hash SHA-256 de cada arquivo copiado
- [ ] Criar ZIP com todos os arquivos e gerar hash do ZIP
- [ ] Extrair metadados EXIF de imagens (lib `Pillow` ou `exifread`)
- [ ] Extrair geolocalização GPS quando disponível
- [ ] Gerar relatório PDF com hashes individuais + hash do ZIP + metadados
- [ ] Registrar cada arquivo como `Evidencia` tipo COPIA_FORENSE no banco
- [ ] Registrar ação no AuditLog

## Critérios de Aceitação

- [ ] Seleção de múltiplos arquivos funciona
- [ ] Arquivos copiados corretamente para `copias_forenses/`
- [ ] Hash SHA-256 individual de cada arquivo + hash do ZIP
- [ ] Metadados EXIF extraídos de imagens (incluindo GPS quando presente)
- [ ] Relatório PDF gerado com todos os dados
- [ ] Arquivos que não têm EXIF não quebram o fluxo

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Média |
| **Story Points** | 5 |
| **Fase** | Fase 2 |
| **Requisitos** | RF06 |
| **Labels** | feature, forense |

</details>

---

### Issue #14 — Dev A — Backend & Segurança

**Título:** `[GRAVACAO] Monitoramento de Downloads`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar monitoramento em tempo real da pasta Downloads do sistema. Ao ativar, qualquer arquivo novo baixado é automaticamente copiado para a pasta do caso com hash SHA-256, metadados e rastreio de origem (URL de download, navegador utilizado). Pode ser ativado manualmente ou automaticamente junto com a gravação de tela.

## Tarefas

- [ ] Implementar watcher na pasta Downloads usando `watchdog` (lib Python)
- [ ] Ao detectar novo arquivo: copiar para `downloads/` do caso
- [ ] Gerar hash SHA-256 do arquivo baixado
- [ ] Tentar identificar origem do download (URL, navegador) via histórico do browser ou metadados do sistema
- [ ] Botão na interface para ativar/desativar monitoramento manualmente
- [ ] Opção de ativar automaticamente ao iniciar gravação (configurável)
- [ ] Gerar metadados JSON: hash, origem, navegador, timestamp
- [ ] Registrar cada download como `Evidencia` tipo DOWNLOAD no banco
- [ ] Registrar no AuditLog

## Critérios de Aceitação

- [ ] Watcher detecta novos arquivos na pasta Downloads em tempo real
- [ ] Arquivo copiado com hash SHA-256 gerado
- [ ] Origem (URL, navegador) registrada quando disponível
- [ ] Ativação manual via botão funciona
- [ ] Ativação automática com gravação funciona (quando configurado)
- [ ] Arquivos incompletos (download em andamento) não são copiados prematuramente

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Média |
| **Story Points** | 5 |
| **Fase** | Fase 2 |
| **Requisitos** | RF07 |
| **Labels** | feature, monitoramento |

</details>

---

### Issue #15 — Dev A — Backend & Segurança

**Título:** `[GRAVACAO] Relatório de Integridade Final (Blockchain-like)`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Ao encerrar o sistema/caso, gerar automaticamente o relatório de integridade completo: verificação de integridade do próprio software (hash do executável), registro cronológico de todas as ações, tabela de encadeamento blockchain-like (cada bloco valida o anterior), lista de sites preservados, downloads e relatórios gerados. Disponível em PDF e HTML.

## Tarefas

- [ ] Implementar trigger ao fechar o sistema: confirmação + geração do relatório
- [ ] Seção: Integridade do Software (hash SHA-256 do próprio sistema)
- [ ] Seção: Registro Cronológico de todas as ações (query AuditLog ordenado por timestamp)
- [ ] Seção: Tabela de Encadeamento (ID, ação, hash anterior, hash atual — visualização blockchain)
- [ ] Seção: Downloads realizados durante a sessão
- [ ] Seção: Sites preservados durante a sessão
- [ ] Seção: Relatórios gerados durante a sessão
- [ ] Executar `verificar_cadeia()` e reportar resultado (cadeia íntegra ou violada)
- [ ] Gerar versão PDF (formal) e HTML (interativa/didática)
- [ ] Salvar em `integridade/` do caso

## Critérios de Aceitação

- [ ] Relatório gerado automaticamente ao fechar o sistema (após confirmação)
- [ ] Tabela de encadeamento mostra todos os blocos com validação visual
- [ ] Registro cronológico lista todas as ações com timestamp UTC
- [ ] Lista sites, downloads e relatórios da sessão
- [ ] Resultado da verificação de cadeia exibido (integra / violada)
- [ ] Disponível em PDF e HTML
- [ ] Salvo em `integridade/` do caso

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Alta |
| **Story Points** | 8 |
| **Fase** | Fase 2 |
| **Requisitos** | RF09, RF11, RNF02 |
| **Labels** | feature, core, seguranca, relatorio |

</details>

# Fase 3 — Polimento e Entrega

---

### Issue #16 — Dev B — Frontend & Integração

**Título:** `[UI] Interface Principal e Identidade Visual PCDF`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Criar a interface principal da aplicação com a identidade visual da EDIFRAUDS/CORF/PCDF: brasão da Polícia Civil, paleta de cores preto/branco/dourado com degraê. Tela inicial com listagem de casos recentes, acesso rápido, botão de novo caso e navegação clara para todas as funções do sistema.

## Tarefas

- [ ] Definir layout base (sidebar ou topbar) com navegação entre funções
- [ ] Aplicar paleta: preto (#1A1A1A), branco (#FFFFFF), dourado (#C8A951), degraê escuro
- [ ] Inserir brasão da Polícia Civil no cabeçalho
- [ ] Inserir nome EDIFRAUDS/CORF/PCDF visível
- [ ] Tela inicial: lista de casos recentes com nome, data, último acesso
- [ ] Botão “Novo Caso” destacado
- [ ] Barra inferior com nome do caso aberto e link para pasta
- [ ] Design responsivo para diferentes resoluções de monitor

## Critérios de Aceitação

- [ ] Brasão PCDF presente e visível
- [ ] Paleta preto/branco/dourado aplicada em toda a interface
- [ ] Tela inicial lista casos com acesso rápido
- [ ] Navegação intuitiva entre todas as funções (preservar site, gravar, print, etc.)
- [ ] Nome EDIFRAUDS/CORF/PCDF visível
- [ ] Interface funciona em monitores 1080p e 1440p

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Média |
| **Story Points** | 5 |
| **Fase** | Fase 3 |
| **Requisitos** | RNF07, RNF08 |
| **Labels** | ui, design |

</details>

---

### Issue #17 — Dev B — Frontend & Integração

**Título:** `[UI] Janela Flutuante com Atalhos Rápidos`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar janela flutuante (overlay sempre visível sobre outras janelas) com atalhos rápidos para as ações principais: iniciar/parar gravação, capturar print, preservar site (com campo de URL), ativar/desativar monitoramento de downloads e cronômetro de sessão.

## Tarefas

- [ ] Criar componente de janela flutuante (always-on-top)
- [ ] Botão: Iniciar/Parar Gravação (com indicador visual de estado)
- [ ] Botão: Capturar Print (screenshot manual)
- [ ] Botão: Preservar Site (com campo de input para URL)
- [ ] Botão: Ativar/Desativar Monitoramento de Downloads
- [ ] Cronômetro de sessão visível (tempo desde abertura do caso)
- [ ] Associar atalhos de teclado (ex: Ctrl+Shift+P para print)
- [ ] Janela arrastável e minimizável

## Critérios de Aceitação

- [ ] Janela flutuante visível sobre outras janelas do sistema
- [ ] Todos os botões funcionais e conectados aos serviços
- [ ] Campo de URL para preservação rápida funciona
- [ ] Cronômetro conta tempo da sessão
- [ ] Atalhos de teclado funcionam globalmente
- [ ] Janela é arrastável e não atrapalha o uso do sistema

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev B — Frontend & Integração |
| **Prioridade** | Média |
| **Story Points** | 5 |
| **Fase** | Fase 3 |
| **Requisitos** | RF13 |
| **Labels** | ui, feature |

</details>

---

### Issue #18 — Dev A — Backend & Segurança

**Título:** `[CONFIG] Configurações e Personalização de Relatórios`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Implementar tela de configurações do sistema: personalização de logo institucional, cabeçalho e assinatura (nome, cargo, órgão) que aparecem nos relatórios PDF. Configuração de intervalo de screenshots periódicas, pasta padrão de salvamento e opção de incluir/excluir informações técnicas introdutórias nos relatórios.

## Tarefas

- [ ] Criar tela/página de configurações com abas (Geral, Gravação, Relatórios)
- [ ] Aba Geral: seleção de pasta padrão de salvamento
- [ ] Aba Gravação: intervalo de screenshots (5s, 10s, 30s, desativado)
- [ ] Aba Gravação: monitoramento de downloads automático (on/off)
- [ ] Aba Relatórios: upload de logo personalizada com preview
- [ ] Aba Relatórios: cabeçalho editável com preview
- [ ] Aba Relatórios: assinatura (nome, cargo, órgão/matrícula) com preview
- [ ] Aba Relatórios: toggle para incluir/excluir informações técnicas
- [ ] Persistir configurações no banco (por analista)
- [ ] Botão “Visualizar Relatório” para preview

## Critérios de Aceitação

- [ ] Logo personalizada aparece nos relatórios com preview funcional
- [ ] Cabeçalho editável reflete nos relatórios
- [ ] Assinatura com nome/cargo/órgão aparece nos relatórios
- [ ] Intervalo de screenshots configurável e persistente
- [ ] Toggle de informações técnicas funciona
- [ ] Configurações salvas por analista (cada um tem as suas)

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Baixa |
| **Story Points** | 3 |
| **Fase** | Fase 3 |
| **Requisitos** | RF14 |
| **Labels** | feature, config |

</details>

---

### Issue #19 — Dev A — Backend & Segurança

**Título:** `[CONFIG] Certidão de Coleta Automática (.docx)`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Ao encerrar o sistema/caso, gerar automaticamente um documento Word editável (.docx) servindo como certidão de coleta de evidência digital. Deve conter: cabeçalho com logo e identidade PCDF, resumo de todas as coletas realizadas, sites preservados, downloads monitorados, relatórios gerados e assinatura do analista.

## Tarefas

- [ ] Escolher lib Python para geração de .docx (`python-docx`)
- [ ] Criar template de certidão com cabeçalho EDIFRAUDS/PCDF
- [ ] Seção: Dados do Caso e do Analista
- [ ] Seção: Resumo de evidências coletadas (quantidade por tipo)
- [ ] Seção: Sites preservados (URL, data, hash)
- [ ] Seção: Downloads monitorados (arquivo, origem, hash)
- [ ] Seção: Relatórios gerados (tipo, data, hash)
- [ ] Seção: Assinatura do analista (conforme configurações)
- [ ] Gerar automaticamente ao fechar o caso (junto com relatório de integridade)
- [ ] Salvar na raiz da pasta do caso

## Critérios de Aceitação

- [ ] Documento .docx gerado automaticamente ao fechar caso
- [ ] Cabeçalho com logo e identidade PCDF presentes
- [ ] Todas as seções preenchidas com dados reais do caso
- [ ] Assinatura do analista conforme configurações
- [ ] Documento abre e é editável no Microsoft Word
- [ ] Salvo na raiz da pasta do caso

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Baixa |
| **Story Points** | 3 |
| **Fase** | Fase 3 |
| **Requisitos** | RF12 |
| **Labels** | feature, relatorio |

</details>

---

### Issue #20 — Dev A — Backend & Segurança

**Título:** `[QUALIDADE] Testes de Integração e Documentação`

<details>
<summary>Corpo da Issue (clique para expandir e copiar)</summary>

## Descrição

Escrever testes de integração cobrindo os fluxos críticos do sistema: preservar site → hash → relatório, gravação → hash → relatório, verificação de integridade da cadeia de auditoria, e criptografia end-to-end. Documentar a arquitetura, API e guia de uso no README do repositório.

## Tarefas

- [ ] Teste: fluxo completo de preservação de site (URL → captura → metadados → hash → relatório)
- [ ] Teste: integridade da cadeia de auditoria (inserir blocos → verificar → adulterar → detectar)
- [ ] Teste: criptografia end-to-end (cifrar → decifrar → comparar hash)
- [ ] Teste: isolamento de acesso (analista A não vê caso de analista B)
- [ ] Teste: validação Pydantic bloqueia extensões perigosas
- [ ] Teste: geração de relatório PDF contém todos os campos obrigatórios
- [ ] README: instruções de setup (docker-compose up)
- [ ] README: arquitetura do sistema (diagrama de componentes)
- [ ] README: guia de uso para investigadores
- [ ] README: descrição dos endpoints/views

## Critérios de Aceitação

- [ ] Todos os testes passam no pipeline CI/CD
- [ ] Cobertura de testes ≥ 70% nos módulos críticos (hash, crypto, audit)
- [ ] README com instruções claras de setup
- [ ] Diagrama de arquitetura presente no README
- [ ] Guia de uso compreensível por usuário não-técnico

## Informações Adicionais

| Campo | Valor |
|-------|-------|
| **Responsável** | Dev A — Backend & Segurança |
| **Prioridade** | Alta |
| **Story Points** | 5 |
| **Fase** | Fase 3 |
| **Requisitos** | RNF05 |
| **Labels** | testes, docs |

</details>

