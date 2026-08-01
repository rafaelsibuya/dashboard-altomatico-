# Dashboard Automático
Projeto próprio voltado à criação de dashboard automático para análise de dados tabulares (planilhas Excel - XLSX), permitindo a geração de gráficos, KPIs e insights sem necessidade de configurações complexas.

---
**Desenvolvedor:** Rafael Sibuya
**Data da Criação/Atualização:** 01/08/2026 às 20:35
---

## 🚀 Funcionalidades Principais
- **Upload de Planilhas (`.xlsx`)**: Aceita upload direto da máquina do usuário.
- **Análise Dinâmica**: Sugestões automáticas de gráficos baseadas nos tipos de dados (temporais, numéricos e categóricos).
- **Múltiplos Gráficos**: Gráficos de barra, linha, doughnut, construídos dinamicamente de acordo com as colunas escolhidas.
- **KPIs (Indicadores-Chave de Desempenho)**: Geração instantânea de KPIs, incluindo soma, média, valores máximos/mínimos e total de registros analisados.
- **Exportação de Dados**: Permite que os dados consolidados ou filtrados sejam baixados em formato CSV.
- **Limpeza de Sessão**: Remoção de dados em memória utilizando um *garbage collector* aprimorado ou requisições manuais para garantir que os dados sensíveis da sessão sejam devidamente destruídos.

## 🛠️ Tecnologias Utilizadas
- **Linguagem Principal**: Python e HTML/CSS/JS (Frontend)
- **Backend**: FastAPI
- **Processamento de Dados**: Pandas
- **Templates e Visualizações**: Jinja2 (Servindo páginas HTML)
- **Servidor Web**: Uvicorn

## 📦 Como executar localmente

1. **Ativar o Ambiente Virtual (se existir)**:
   - No Windows: `venv\Scripts\activate` ou `.venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

2. **Instalar dependências** (caso ainda não estejam instaladas):
   ```bash
   pip install fastapi uvicorn pandas openpyxl jinja2
   ```

3. **Rodar o servidor de desenvolvimento**:
   ```bash
   python app.py
   ```
   *Ou utilizando diretamente o uvicorn:*
   ```bash
   uvicorn app:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Acesso**: Abra o navegador e acesse `http://127.0.0.1:8000/`.

## 📌 Principais Endpoints da API

- `GET /` : Renderiza a página principal do dashboard (`index.html`).
- `POST /upload` : Recebe um arquivo Excel (`.xlsx`), lê usando Pandas, gera uma visualização prévia (preview) e cria uma sessão contendo os dados na memória.
- `POST /process` : Recebe configurações de cruzamentos de colunas, eixos e tipos de agrupamento (soma, média, contagem) para gerar os arrays de labels, valores e os respectivos KPIs do gráfico desejado.
- `POST /suggestions` : Avalia os tipos de colunas do DataFrame carregado para sugerir cruzamentos lógicos (por exemplo, analisar faturamento ao longo do tempo ou vendas por categoria).
- `POST /download_data` : Permite que o usuário exporte os dados filtrados em formato `.csv`.
- `POST /clear` : Deleta da memória os DataFrames e contextos da sessão ativa do usuário.

## 🛡️ Segurança (Módulo Rust)
O projeto tenta importar um módulo otimizado (`rust_security`) para validação binária rápida do arquivo Excel submetido, evitando arquivos maliciosos ou corrompidos de travarem o sistema e trazendo mais segurança durante o upload. Caso esse módulo não exista no ambiente, o sistema avisa e opera em modo tradicional via Pandas.
