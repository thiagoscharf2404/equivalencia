# equivalencIA

Sistema interno para apoiar a coordenação acadêmica na análise de aproveitamento de disciplinas. O coordenador cadastra e localiza alunos, reúne histórico e planos, revisa os dados extraídos, avalia sugestões e emite o parecer. O aluno não usa esta interface.

## Aplicação React e API

O novo fluxo usa React/Vite no navegador, FastAPI para os serviços e mantém o PostgreSQL e as operações de domínio existentes em `database.py`.

```text
React (frontend/) → FastAPI (api/) → PostgreSQL
                            ├──────→ extração de PDF/DOCX
                            └──────→ adaptador opcional de agente de equivalência
```

O aplicativo Streamlit anterior continua disponível pelo `app.py` enquanto o fluxo React é integrado. As alterações existentes nesse código foram preservadas.

### Publicar um link gratuito no Render

O `render.yaml` e o `Dockerfile` publicam a interface React e a API FastAPI no mesmo serviço. O PostgreSQL fica em um serviço separado (por exemplo, no Render ou no Supabase); React não substitui o banco. No plano gratuito, o serviço do Render pode dormir após um período sem acessos e levar alguns segundos para acordar.

1. Envie o repositório para o GitHub e, no Render, crie um **Blueprint** conectado a esse repositório. O Render encontrará o `render.yaml` automaticamente.
2. No serviço criado, preencha `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD` com os dados do banco de teste escolhido.
3. Para habilitar as sugestões com Gemini, crie uma chave no Google AI Studio e adicione `GEMINI_API_KEY` no Environment do Render. Não coloque a chave no GitHub. O Blueprint seleciona `gemini-2.5-flash` e a integração permanece sem chamadas até a chave ser configurada.
4. Aguarde o deploy concluir e abra a URL `.onrender.com` informada pelo Render. O login existente usa os coordenadores e unidades do banco conectado.

Não coloque senhas ou chaves no GitHub nem no `render.yaml`; informe os dados do banco nos Environment Variables do serviço Render. O `SESSION_SECRET` é gerado pelo Blueprint.

### Iniciar localmente

1. Crie/ative o ambiente virtual e instale as dependências Python:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Configure `.env` com acesso ao PostgreSQL. Use `.env.example` como referência e não compartilhe credenciais.
3. Aplique uma vez, nesta ordem, as migrações `sql/migrations/auth_coordenacao.sql` e `sql/migrations/equivalencias_ia.sql` no banco usado pelo projeto. A primeira cria as unidades e contas de coordenação e associa os dados existentes à unidade principal.
4. Defina `APP_ENV=development` durante testes locais e `SESSION_SECRET` no `.env` com um valor aleatório de pelo menos 32 caracteres. Para criar um valor no PowerShell: `py -c "import secrets; print(secrets.token_urlsafe(48))"`. O cadastro inicial aceita senha curta apenas em desenvolvimento; em produção, exige ao menos 12 caracteres.
5. Cadastre o primeiro acesso à coordenação sem colocar a senha no histórico do terminal:

```powershell
py scripts/create_coordinator.py
```

6. Inicie a API na raiz do repositório:

```powershell
uvicorn api.main:app --reload
```

7. Em outro terminal, inicie a interface React:

```powershell
cd frontend
pnpm install
pnpm run dev
```

A API aceita a origem `http://localhost:5173` por padrão. Para outro endereço, configure `FRONTEND_ORIGINS`. A URL da API pode ser definida no frontend com `VITE_API_URL` (por padrão, `http://localhost:8000/api`). Em produção, use HTTPS e `SESSION_COOKIE_SECURE=true`.

## Fluxo da coordenação

1. Localizar um cadastro de aluno ou cadastrar um novo. O mesmo cadastro pode ser reutilizado em várias análises; RA é opcional.
2. Registrar instituição, curso e situação de origem.
3. Selecionar um curso de referência e sua matriz e informar o período de ingresso. A análise de IA procura disciplinas em todos os cursos/matrizes da mesma unidade.
4. Anexar o histórico (PDF ou DOCX) e os planos/ementas da origem (PDF ou DOCX) com conteúdo e carga horária para uma análise acadêmica mais confiável.
5. Extrair e revisar as disciplinas do histórico. Dados não identificados permanecem para correção do coordenador; documentos digitalizados sem camada de texto não têm OCR.
6. Confirmar os dados, consultar sugestões quando um adaptador de IA estiver conectado ou registrar uma correspondência manual. Só disciplinas explicitamente aprovadas e com carga de origem igual ou superior à carga de destino podem ser associadas.
7. Aprovar, rejeitar ou deixar pendente cada item e conferir a prévia do parecer.
8. Gerar o DOCX com itens aprovados, não aprovados e pendentes.

A IA é uma fonte de sugestões. A decisão acadêmica continua com o coordenador. A interface continua o fluxo mesmo quando a IA ainda não foi conectada.

## Integração de IA

`services/equivalencia_agent.py` define o contrato `EquivalenceAgent` e o adaptador REST `GeminiAgent`. Ele recebe disciplinas de origem confirmadas como aprovadas, o texto dos planos/ementas enviados e as disciplinas cadastradas em todas as matrizes dos cursos da mesma unidade do curso de referência. O nome e o RA do aluno não são enviados ao Gemini. A comparação exige carga horária de origem igual ou maior, e sugestões só podem apontar para pares previamente elegíveis. A coordenação revisa e toma a decisão final.

O Render configura `AI_PROVIDER=gemini` e `GEMINI_MODEL=gemini-2.5-flash`; adicione `GEMINI_API_KEY` no painel do serviço. A chave é obtida no Google AI Studio. A modalidade gratuita tem limites de uso que podem mudar e o conteúdo enviado pode ser usado pelo Google para melhoria dos serviços; use somente documentos e dados de teste autorizados. Ao não configurar a chave, não há chamada externa e o fluxo manual continua disponível.

## Parecer institucional

A API usa `REPORT_TEMPLATE_PATH` para abrir um modelo DOCX e substituir marcadores como `{{student_name}}`, `{{student_ra}}`, `{{origin_institution}}`, `{{origin_course}}`, `{{target_course}}`, `{{target_matrix}}`, `{{term}}` e `{{coordinator_note}}`. Se o arquivo não estiver disponível, é gerado um documento provisório. O DOC/PDF de referência enviado contém dados pessoais de alunos e não foi copiado para o repositório. Coloque o modelo oficial DOCX em `documents/modelo_parecer.docx` ou atualize a variável de ambiente quando o arquivo editável correto estiver disponível.

## Banco e dados

`sql/schema.sql` descreve uma base nova. Migrações em `sql/migrations/` são incrementais e devem ser aplicadas uma única vez na base existente apropriada. Para o fluxo React, execute `sql/migrations/auth_coordenacao.sql` e `sql/migrations/equivalencias_ia.sql`. A migração não é executada automaticamente pela API.

Arquivos enviados permanecem associados à análise no PostgreSQL. Há limite padrão de 20 MB por documento, configurável em `MAX_DOCUMENT_BYTES`.

## Requisitos do documento recebido

O arquivo `requisitos-aproveitamento-disciplinas.docx` define uma visão de produto voltada a coordenadores e administradores. A aplicação já oferece login institucional, escolha de unidade, sessão protegida e separação de alunos, cursos e análises por unidade. O perfil administrativo avançado, importação Excel/CSV, trilha de auditoria completa e exportação PDF continuam como próximos incrementos.

## Estrutura principal

```text
api/                       API FastAPI
frontend/                  Interface React/Vite da coordenação
services/equivalencia_agent.py  Contrato do agente de IA
services/documentos.py     Validação e leitura de PDF/DOCX
sql/migrations/             Migrações incrementais do PostgreSQL
app.py                      Interface Streamlit anterior
```

## Segurança e privacidade

Use somente dados de teste ao desenvolver. Os pareceres enviados são documentos identificáveis e devem permanecer fora do Git. O acesso usa cookie `HttpOnly`, assinatura HMAC e senha com PBKDF2; cada coordenador é associado a uma unidade e as rotas de análise verificam a unidade proprietária. Configure segredos fortes e HTTPS antes de disponibilizar em ambiente real; CORS não substitui controle de acesso.
