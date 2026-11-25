# Auth Login & Protect

API de autenticação com FastAPI e Supabase Auth. O cliente se cadastra e entra pelo Supabase, recebe um JWT e envia esse token no cabeçalho `Authorization` para acessar as rotas protegidas.

## Sobre o projeto

O Supabase é o provedor de identidade: ele guarda a senha e emite o access token. Esta API não armazena senha. Ela valida o corpo do pedido, repassa o cadastro e o login ao Supabase e, nas rotas protegidas, confere o token com `get_user` antes de responder.

## Arquitetura resumida

Tudo vive em `main.py`.

- `signup` e `login` falam com `supabase.auth`.
- `extract_bearer_token` lê o cabeçalho `Authorization: Bearer <token>`.
- `require_user` é a dependência reutilizável. Ela rejeita token ausente ou inválido e só então deixa a rota executar.
- `HTTPBearer` publica o cadeado no Swagger. `auto_error=False` preserva o status **401** com a chave `error`.

## Pré-requisitos

- Python 3.10 ou superior
- Um projeto no [Supabase](https://supabase.com)
- A porta definida em `PORT` livre. O padrão é `8000`.

## Instalação e configuração

1. Crie um projeto no Supabase.
2. Em **Authentication → Sign In / Providers → Email**, desligue **Confirm email** para este exercício. Com essa opção ligada, o plano gratuito só envia dois e-mails por hora e o login não devolve sessão até a confirmação.
3. No botão **Connect**, copie a Project URL e a chave publishable (`sb_publishable_...`). No painel antigo essa chave se chama anon key. Não use a chave secret nem a service role.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Preencha o `.env` com os seus valores. Esse arquivo está no `.gitignore` e não deve ir para o Git.

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_publishable_key
PORT=8000
```

## Como executar

```bash
source .venv/bin/activate
python main.py
```

O terminal mostra `Server running and connected to Supabase`. A documentação interativa fica em [http://localhost:8000/docs](http://localhost:8000/docs).

## Rotas

| Método | Caminho | Auth | Sucesso |
| --- | --- | --- | --- |
| POST | `/auth/signup` | não | 201 |
| POST | `/auth/login` | não | 200 |
| POST | `/auth/logout` | Bearer | 204 |
| GET | `/public/info` | não | 200 |
| GET | `/protected/profile` | Bearer | 200 |
| GET | `/protected/dashboard` | Bearer | 200 |

Corpo de signup e login:

```json
{ "email": "usuario@email.com", "password": "sua-senha" }
```

Rotas protegidas exigem:

```http
Authorization: Bearer <access_token>
```

| Situação | Status |
| --- | --- |
| E-mail ou senha ausente ou vazio | 400 |
| Login incorreto | 401 |
| Token ausente ou mal formatado | 401 |
| Token inválido ou expirado | 401 |
| Logout concluído | 204 |

No Swagger, use **Authorize** e cole somente o `access_token`, sem a palavra `Bearer`.

## Swagger UI

![Swagger UI com o cadeado nas rotas protegidas](docs/swagger-ui.jpg)

## Como rodar os testes

Ainda não há testes automatizados. A verificação é manual, com a API no ar.

```bash
curl -i http://localhost:8000/public/info

curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"usuario@email.com","password":"sua-senha"}'

curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN"
```

`/public/info` responde **200**. `/protected/profile` sem token responde **401**. Com um access token válido, responde **200** com `id`, `email` e `created_at`.
