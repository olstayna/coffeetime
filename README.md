# CoffeeTime

E-commerce acadêmico para cafeteria, desenvolvido com Flask, MySQL, HTML, CSS e JavaScript. O sistema possui catálogo responsivo, autenticação, carrinho, checkout, acompanhamento de pedidos e painel administrativo.

Todos os direitos reservados. Projeto construído por Tayná Santana - [olstayna](https://github.com/olstayna), para a disciplina de Projeto Integrador Transdisciplinar em Sistemas de Informação II do curso Sistemas de Informação, 8º semestre, da Universidade Cidade de São Paulo.

Meu [Linkedin](https://www.linkedin.com/in/olstayna/) e
[Portfólio](https://taynasantana.com.br/);

## Funcionalidades

### Clientes

- cadastro e autenticação;
- máscara e validação de celular;
- catálogo com busca instantânea e filtro por categoria;
- detalhes do produto e recomendações aleatórias;
- carrinho com ajuste de quantidade;
- cupons de desconto e regras de primeira compra;
- checkout com máscara e validação de CEP;
- histórico e acompanhamento de pedidos;
- tema claro e escuro.

### Administração

- cadastro e edição de produtos;
- upload de imagens armazenadas como `LONGBLOB` no MySQL;
- ativação e inativação de produtos;
- criação e remoção de cupons;
- configuração de desconto percentual ou fixo, compra mínima, validade e primeira compra;
- listagem e remoção de clientes;
- acompanhamento e atualização sequencial do status dos pedidos.

## Tecnologias

- Python 3.12+
- Flask 3
- MySQL 8
- HTML com templates Jinja
- CSS
- JavaScript

## Estrutura

```text
coffeetime/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── decorators.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── run.py
├── database/
│   ├── images/
│   └── schema.sql
├── frontend/
│   ├── static/
│   │   ├── css/style.css
│   │   ├── js/app.js
│   │   └── favicon.ico
│   └── templates/
│       ├── admin/
│       ├── auth/
│       └── shop/
├── .gitignore
└── README.md
```

O Flask utiliza os templates e arquivos estáticos da pasta `frontend`. As regras de negócio permanecem no backend e o acesso ao MySQL é centralizado nos repositórios.

## Configuração

### 1. Preparar o MySQL

Inicie uma instância do MySQL 8 e tenha em mãos host, porta, usuário e senha. O comando de inicialização cria automaticamente o banco configurado caso ele ainda não exista.

### 2. Criar o ambiente Python

No PowerShell, a partir da raiz do projeto:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

No Linux ou macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

### 3. Configurar as variáveis de ambiente

Edite `backend/.env`:

```env
SECRET_KEY=troque-esta-chave-em-producao
DB_HOST=localhost
DB_PORT=3306
DB_NAME=coffeetime
DB_USER=root
DB_PASSWORD=sua-senha
ADMIN_EMAIL=admin@coffeetime.com
ADMIN_PASSWORD=uma-senha-segura
```

Não envie arquivos `.env` para o repositório. Em produção, substitua a chave secreta e a senha administrativa padrão.

### 4. Inicializar o banco

Com o terminal dentro de `backend`:

```powershell
python -m flask --app run.py init-db
```

Esse comando:

- cria o banco e as tabelas;
- aplica migrações compatíveis com versões anteriores;
- cadastra os produtos e cupons iniciais;
- cria o administrador definido no `.env`;
- armazena senhas exclusivamente como hash.

As imagens não ficam no frontend. O administrador deve enviá-las pelo formulário de produto; os bytes são armazenados em `products.image_data` e o MIME type em `products.image_mime`.

## Execução

Dentro de `backend`:

```powershell
python -m flask --app run.py run --debug
```

Acesse [http://127.0.0.1:5000](http://127.0.0.1:5000).

O painel administrativo fica em `/admin` e utiliza `ADMIN_EMAIL` e `ADMIN_PASSWORD` configurados no `.env`.

## Testes

Dentro de `backend`:

```powershell
python -m unittest discover -v
```

Os testes cobrem carrinho, totais, opções de pagamento, fluxo de status, validação de CEP e regras de cupons de primeira compra.

## Deploy

O projeto do CoffeeTime está disponível no link https://coffeetime-7qu2.onrender.com/, com deploy da aplicação no [Render](https://render.com/) e o banco de dados My-SQL disponibilizado através do [Aiven](https://aiven.io/), sendo uma alternativa gratuita e acessível para este projeto acadêmico.

## Observações

- O projeto não processa pagamentos reais.
- Nenhum dado de cartão é armazenado.
- PIX, cartão e dinheiro são modalidades demonstrativas registradas no pedido.
- A remoção de um cliente pelo administrador também remove seus pedidos e registros relacionados.
