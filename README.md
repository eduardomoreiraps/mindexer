# 🚀 Mindexer

<p align="center">
  <b>Stack completa e portátil para indexação e automação de torrents brasileiros no ecossistema Arr (Prowlarr, Radarr, Sonarr, Jellyseerr e qBittorrent).</b>
</p>

---

## 📖 Visão Geral

O **Mindexer** reúne indexadores nacionais em uma solução pronta para uso com Docker Compose. Já vem integrado com **Prowlarr**, bypass otimizado de Cloudflare via **FlareSolverr** e cache em memória com **Redis**.

### 🌐 Sites Suportados
- ✅ **#ÐЯ †ØЯЯ€₦†$**
- ✅ **฿£µÐ√** *(requer FlareSolverr)*
- ✅ **©Ø₥@₦ÐØ** *(requer FlareSolverr)*
- ✅ **Я€Ð€**
- ✅ **$†@Я©Ҝ**
- ✅ **†₣!£₥€**
- ✅ **฿€†ØЯ**

---

## 📦 Estrutura do Repositório

```text
mindexer/
├── docker-compose.yml       # Orquestração de todos os serviços
├── .env.example             # Variáveis de ambiente padrão
├── .gitignore               # Ignora logs e dados temporários
├── README.md                # Este guia
├── mindexer/                # Código-fonte da API Python e scrapers
├── prowlarr/
│   └── Definitions/
│       └── Custom/          # Definições Cardigann prontas para o Prowlarr
└── redis/
    └── data/                # Diretório de persistência do Redis
```

---

## 🚀 Como Iniciar

### 1. Clonar o Repositório
```bash
git clone https://github.com/eduardomoreiraps/mindexer.git
cd mindexer
```

### 2. Configurar o Ambiente (Opcional)
Copie o `.env.example` para `.env`:
```bash
cp .env.example .env
```
*(Caso queira mudar as portas `7006` ou `9696`, edite o `.env`)*.

### 3. Subir os Contêineres
```bash
docker compose up -d
```

*(No CasaOS, ZimaOS, Portainer, Synology ou Unraid, basta importar a pasta ou o arquivo `docker-compose.yml`).*

---

## 🌐 Endereços e Portas

| Serviço | Endereço | Descrição |
| :--- | :--- | :--- |
| **Mindexer API** | `http://SEU_IP:7006` | Status da API e endpoints dos indexadores |
| **Prowlarr** | `http://SEU_IP:9696` | Gerenciador de indexadores |
| **FlareSolverr** | Interno (`http://flaresolverr:8191`) | Bypass de proteção Cloudflare |
| **Redis** | Interno (`redis:6379`) | Cache persistente em memória |

---

## ⚙️ Como Adicionar os Scrapers no Prowlarr

1. Acesse o **Prowlarr**: `http://SEU_IP:9696`.
2. Vá em **Indexers** e clique em **Add Indexer (+)**.
3. Pesquise por **`Mindexer`**:
   - Você verá os indexadores prontos para adicionar individualmente:
     - `Mindexer (#ÐЯ)`
     - `Mindexer (฿£µÐ√)`
     - `Mindexer (©Ø₥@₦ÐØ)`
     - `Mindexer (Я€Ð€)`
     - `Mindexer ($†@Я©Ҝ)`
     - `Mindexer (†₣!£₥€)`
     - Ou a definição genérica `Mindexer` com seletor no menu.
   - Também encontrará o `฿€†ØЯ`.
4. Clique no indexador desejado e clique em **Save**. Pronto!

---

## 🔗 Integração com Sonarr / Radarr

1. No Prowlarr, vá em **Settings** > **Apps** > clique em **(+)**.
2. Escolha **Radarr** ou **Sonarr**.
3. Em **Prowlarr Server**, informe a URL acessível: `http://172.50.0.103:9696` ou `http://SEU_IP:9696`.
4. Insira a URL e a API Key do seu Radarr/Sonarr.
5. Salve. Todos os indexadores do Mindexer serão sincronizados automaticamente!

---

## ⚡ Otimizações Implementadas

- **Consumo de Hardware do FlareSolverr:** Limitado a 1.5 núcleos de CPU e 1.5 GB de RAM máxima, evitando sobrecarga ou travamentos em mini PCs e servidores domésticos.
- **Cache Redis com Limpeza LRU:** Mantém resultados frequentes em memória (com persistência AOF) e limite de 512 MB com política `allkeys-lru`.
- **Compatibilidade Portátil:** Redes e volumes utilizam caminhos relativos e resolução de DNS interno de contêineres Docker.

---

## 👏 Créditos e Agradecimentos

Este projeto é baseado no trabalho original do **[DF Indexer](https://github.com/DFlexy/dfindexer)**, desenvolvido por **[dflexy](https://github.com/DFlexy)**.

Todos os créditos pelo conceito fundamental e arquitetura inicial pertencem ao autor original. Esta versão (**Mindexer**) estende o projeto com:
- Novos scrapers nacionais (como **#ÐЯ**).
- Otimização e contenção de recursos do **FlareSolverr** e **Redis**.
- Definições individuais e pré-configuradas no padrão **`Mindexer (scrapper)`** para o Prowlarr.
- Orquestração completa, desacoplada e 100% portátil em Docker Compose.

---

## 📄 Licença
Distribuído sob a licença MIT. Veja `LICENSE` para mais detalhes.
