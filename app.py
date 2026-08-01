import os
import re
import io
import time
import uuid
import asyncio
import pandas as pd
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from datetime import datetime

# Configuração de Logs para o Ruby ler
logging.basicConfig(filename="system.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Tenta carregar o módulo em Rust
try:
    import rust_security
    HAS_RUST_SECURITY = True
    logging.info("Módulo rust_security carregado com sucesso.")
except ImportError:
    HAS_RUST_SECURITY = False
    logging.warning("Módulo rust_security não encontrado. Validação binária desativada. Execute 'maturin develop' na pasta rust_security.")

# Variável global para armazenar os dataframes e metadata
# Estrutura: { "uuid": {"df": DataFrame, "last_accessed": timestamp} }
dados_memoria = {}

# Garbage collector para limpar sessões antigas (> 1 hora inativas)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup
    task = asyncio.create_task(garbage_collector())
    yield
    # Teardown
    task.cancel()

async def garbage_collector():
    while True:
        try:
            await asyncio.sleep(600)  # roda a cada 10 minutos
            now = time.time()
            expired = [sid for sid, data in dados_memoria.items() if (now - data["last_accessed"]) > 3600]
            for sid in expired:
                dados_memoria.pop(sid, None)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Erro no GC: {e}")

app = FastAPI(lifespan=lifespan)

# Configuração de templates
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

# Configuração de arquivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Funções de agregação suportadas ("tipos de evolução")
AGG_FUNCS = {
    "sum": "sum",
    "count": "count",
    "count_distinct": "nunique",
    "mean": "mean",
    "min": "min",
    "max": "max",
    "median": "median",
}

AGG_LABELS = {
    "sum": "Soma (Evolução de Valor)",
    "count": "Contagem (Quantidade)",
    "count_distinct": "Contagem Única (Valores Distintos)",
    "mean": "Média",
    "min": "Mínimo",
    "max": "Máximo",
    "median": "Mediana",
}

def fmt_currency(v):
    if pd.isna(v): return "R$ 0,00"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_currency(val):
    if isinstance(val, str):
        val = val.replace('R$', '').replace(' ', '')
        if ',' in val:
            val = val.replace('.', '').replace(',', '.')
    return val

# ---------------------------------------------------------------------------
# Motor de sugestões de análise
# ---------------------------------------------------------------------------
def _to_float(v):
    try:
        v = re.sub(r"[R$\s]", "", str(v))
        if "," in v:
            v = v.replace(".", "").replace(",", ".")
        return float(v)
    except (ValueError, TypeError):
        return None

def _looks_numeric(series):
    if any(x in str(series.name).lower() for x in ['id', 'código', 'codigo', 'cep', 'telefone', 'cpf', 'cnpj']):
        return False
    s = series.astype(str).str.strip()
    s = s[s != ""]
    s = s.head(200)
    if len(s) < 3:
        return False
    ok = sum(1 for v in s if _to_float(v) is not None)
    return ok / len(s) >= 0.7

def _looks_date(series):
    s = series.astype(str).str.strip()
    s = s[s != ""].head(200)
    if len(s) < 2:
        return False
    ok = 0
    for v in s:
        try:
            pd.to_datetime(v, dayfirst=True, errors="raise")
            ok += 1
        except Exception:
            pass
    return ok / len(s) >= 0.7

def detect_column_types(df):
    cols = df.columns.tolist()
    numeric_cols = [c for c in cols if _looks_numeric(df[c])]
    date_cols = [c for c in cols if (c not in numeric_cols) and _looks_date(df[c])]
    text_cols = [c for c in cols if c not in numeric_cols and c not in date_cols]
    return date_cols, numeric_cols, text_cols

def build_suggestions(date_cols, numeric_cols, text_cols):
    sugs = []

    def add(title, desc, x, y, agg, chart, cat, icon):
        sugs.append({
            "title": title, "description": desc, "x_columns": x, "y_column": y,
            "aggregation": agg, "chart_type": chart, "category": cat, "icon": icon,
        })

    # 1. Evolução temporal (linha)
    if date_cols and numeric_cols:
        d, n = date_cols[0], numeric_cols[0]
        add(
            f"Evolução de {n} por {d}",
            f"Acompanhe o total de {n} ao longo do tempo para identificar tendências, picos e sazonalidade.",
            [d], n, "sum", "line", "Temporal", "trend",
        )
        if len(numeric_cols) > 1:
            add(
                f"Comportamento de {numeric_cols[1]} por {d}",
                f"Observe como {numeric_cols[1]} varia ao longo de {d} usando a média.",
                [d], numeric_cols[1], "mean", "line", "Temporal", "trend",
            )

    # 2. Comparação por categoria
    if text_cols and numeric_cols:
        t, n = text_cols[0], numeric_cols[0]
        add(
            f"Total de {n} por {t}",
            f"Compare o total de {n} entre as diferentes categorias de {t}.",
            [t], n, "sum", "bar", "Comparação", "bars",
        )
        add(
            f"Participação de cada {t} no total",
            f"Visualize a fatia que cada categoria de {t} representa no total de {n}.",
            [t], n, "sum", "doughnut", "Distribuição", "pie",
        )
        add(
            f"Média de {n} por {t}",
            f"Compare a média de {n} entre as categorias de {t} para nivelar volumes diferentes.",
            [t], n, "mean", "bar", "Estatística", "stats",
        )

    # 3. Frequência por categoria
    for t in text_cols[:2]:
        add(
            f"Frequência de registros por {t}",
            f"Quantos registros existem em cada categoria de {t}.",
            [t], t, "count", "bar", "Comparação", "count",
        )

    # 4. Ranking de clientes
    cliente_col = next((c for c in text_cols if "cliente" in str(c).lower()), None)
    if cliente_col and numeric_cols:
        n = numeric_cols[0]
        add(
            f"Top 10 {cliente_col} por {n}",
            f"Ranking dos 10 {cliente_col} que mais contribuem para {n}.",
            [cliente_col], n, "sum", "bar", "Ranking", "ranking",
        )

    # 5. Cruzamento de múltiplas colunas
    if text_cols and date_cols and numeric_cols:
        t, d, n = text_cols[0], date_cols[0], numeric_cols[0]
        add(
            f"Cruzamento de {t} × {d}",
            f"Combine {t} e {d} no eixo X para uma visão detalhada do {n} por período e categoria.",
            [t, d], n, "sum", "bar", "Cruzamento", "grid",
        )
    if len(text_cols) >= 2 and numeric_cols:
        t1, t2, n = text_cols[0], text_cols[1], numeric_cols[0]
        add(
            f"Cruzamento de {t1} × {t2}",
            f"Cruze duas dimensões categóricas simultaneamente para analisar {n} com profundidade.",
            [t1, t2], n, "sum", "bar", "Cruzamento", "grid",
        )

    return sugs[:8]

@app.post("/clear")
async def clear_data(payload: dict = Body(...)):
    """Remove os dados carregados em memória para a sessão informada."""
    session_id = payload.get("session_id")
    if session_id:
        dados_memoria.pop(session_id, None)
    return JSONResponse(content={"success": True, "message": "Dados removidos."})

@app.post("/suggestions")
async def get_suggestions(payload: dict = Body(...)):
    """
    Gera sugestões de análise automáticas com base nos dados da planilha.
    Aplica os mesmos ajustes de cabeçalho/linhas ignoradas do /process.
    """
    try:
        session_id = payload.get("session_id")
        session_data = dados_memoria.get(session_id) if session_id else None
        if not session_data:
            return JSONResponse(content={"success": False, "error": "Sessão expirada. Faça upload novamente."}, status_code=400)
            
        session_data["last_accessed"] = time.time()
        df = session_data["df"]

        ignored_indexes = payload.get("ignored_indexes", [])
        header_index = payload.get("header_index", -1)

        df_s = df.copy()
        if header_index >= 0 and header_index in df_s.index:
            new_columns = df_s.loc[header_index].astype(str).tolist()
            df_s.columns = new_columns
            df_s = df_s.drop(index=header_index)
        df_s = df_s.drop(index=ignored_indexes, errors="ignore")
        df_s = df_s.loc[:, ~df_s.columns.duplicated()]
        # Apenas para sugestões o fillna("") não afeta resultados matemáticos, mas evita erros no detetor
        df_s = df_s.fillna("")

        date_cols, numeric_cols, text_cols = detect_column_types(df_s)
        suggestions = build_suggestions(date_cols, numeric_cols, text_cols)

        return JSONResponse(content={
            "success": True,
            "suggestions": suggestions,
            "total_rows": len(df_s),
            "detected": {"date_cols": date_cols, "numeric_cols": numeric_cols, "text_cols": text_cols},
        })

    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        # Validação de Segurança via Rust
        if HAS_RUST_SECURITY:
            is_valid = rust_security.validate_excel_file(contents)
            if not is_valid:
                logging.error(f"SECURITY_BLOCK - Arquivo bloqueado por segurança: {file.filename}")
                return JSONResponse(content={"success": False, "error": "SECURITY_BLOCK: Formato de arquivo não reconhecido ou corrompido."}, status_code=400)
                
        df = pd.read_excel(io.BytesIO(contents))
        
        session_id = str(uuid.uuid4())
        dados_memoria[session_id] = {
            "df": df,
            "last_accessed": time.time()
        }
        
        logging.info(f"UPLOAD - Sessão: {session_id} - Arquivo: {file.filename} - Linhas: {len(df)}")
        
        columns = df.columns.tolist()
        
        df_preview = df.head(100).copy()
        df_preview["_index"] = df_preview.index.tolist()
        
        # Para enviar via JSON de forma segura
        df_preview = df_preview.fillna("")
        data_preview = df_preview.to_dict(orient="records")
        
        return JSONResponse(content={
            "success": True,
            "session_id": session_id,
            "columns": columns,
            "preview": data_preview,
            "total_rows": len(df)
        })
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

def prepare_data_for_processing(payload, df):
    ignored_indexes = payload.get("ignored_indexes", [])
    header_index = payload.get("header_index", -1)
    x_columns = payload.get("x_columns") or []
    
    legacy_x = payload.get("x_column")
    if legacy_x and legacy_x not in x_columns:
        x_columns.insert(0, legacy_x)
        
    y_column = payload.get("y_column")
    aggregation = payload.get("aggregation", "sum")
    cliente_column = payload.get("cliente_column")

    if not x_columns:
        raise ValueError("Selecione ao menos uma coluna para o eixo X.")

    df_filtered = df.copy()

    if header_index >= 0 and header_index in df_filtered.index:
        new_columns = df_filtered.loc[header_index].astype(str).tolist()
        df_filtered.columns = new_columns
        df_filtered = df_filtered.drop(index=header_index)

    df_filtered = df_filtered.drop(index=ignored_indexes, errors="ignore")

    for col in x_columns:
        if col not in df_filtered.columns:
            raise ValueError(f"Coluna X ({col}) inválida.")
    if y_column not in df_filtered.columns:
        raise ValueError(f"Coluna Y ({y_column}) inválida.")

    numeric_aggs = {"sum", "mean", "min", "max", "median"}
    if aggregation in numeric_aggs:
        df_filtered[y_column] = df_filtered[y_column].apply(clean_currency)
        df_filtered[y_column] = pd.to_numeric(df_filtered[y_column], errors="coerce")
        df_filtered = df_filtered.dropna(subset=[y_column])
    else:
        df_filtered[y_column] = df_filtered[y_column].fillna("").astype(str)
        df_filtered = df_filtered[df_filtered[y_column].str.strip() != ""]

    if df_filtered.empty:
        raise ValueError("Nenhum dado válido encontrado na célula selecionada após os filtros.")
        
    return df_filtered, x_columns, y_column, aggregation, cliente_column, numeric_aggs

@app.post("/process")
async def process_data(payload: dict = Body(...)):
    """Recebe as configurações do dashboard e retorna os cálculos."""
    try:
        session_id = payload.get("session_id")
        session_data = dados_memoria.get(session_id) if session_id else None
        if not session_data:
            return JSONResponse(content={"success": False, "error": "Sessão expirada. Faça upload novamente."}, status_code=400)
            
        session_data["last_accessed"] = time.time()
        df = session_data["df"]
        
        try:
            df_filtered, x_columns, y_column, aggregation, cliente_column, _ = prepare_data_for_processing(payload, df)
        except ValueError as ve:
            return JSONResponse(content={"success": False, "error": str(ve)}, status_code=400)

        agg_func = AGG_FUNCS.get(aggregation, "sum")
        grouped = df_filtered.groupby(x_columns)[y_column].agg(agg_func).rename("valor_agg").reset_index()
        grouped = grouped.sort_values(by=x_columns).reset_index(drop=True)

        if len(x_columns) > 1:
            labels = grouped[x_columns].apply(lambda r: " | ".join(r.astype(str)), axis=1).tolist()
        else:
            labels = grouped[x_columns[0]].astype(str).tolist()
        values = grouped["valor_agg"].tolist()

        cliente_labels = None
        cliente_values = None
        if cliente_column and cliente_column in df_filtered.columns:
            c_grouped = df_filtered.groupby(cliente_column)[y_column].agg(agg_func).rename("valor_agg").reset_index()
            c_grouped = c_grouped.sort_values(by="valor_agg", ascending=False).head(10)
            cliente_labels = c_grouped[cliente_column].astype(str).tolist()
            cliente_values = c_grouped["valor_agg"].tolist()

        total_rows = len(df_filtered)
        categories = len(grouped)

        # NaNs can break JSONResponse, ensure values are valid floats, replace NaNs with 0 or None
        def safe_val(v): return 0 if pd.isna(v) else v
        
        # Safe aggregation calls
        if aggregation == "sum":
            total_sum = safe_val(df_filtered[y_column].sum())
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": f"Valor Total · {y_column}", "value": fmt_currency(total_sum), "icon": "currency"},
                {"label": "Média por Registro", "value": fmt_currency(total_sum / total_rows if total_rows else 0), "icon": "average"},
            ]
        elif aggregation == "count":
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": "Contagem Total", "value": f"{total_rows}", "icon": "count"},
                {"label": "Categorias Analisadas", "value": f"{categories}", "icon": "tags"},
            ]
        elif aggregation == "count_distinct":
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": f"Valores Únicos · {y_column}", "value": f"{df_filtered[y_column].nunique()}", "icon": "count"},
                {"label": "Categorias Analisadas", "value": f"{categories}", "icon": "tags"},
            ]
        elif aggregation == "mean":
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": f"Média · {y_column}", "value": fmt_currency(safe_val(df_filtered[y_column].mean())), "icon": "average"},
                {"label": "Categorias Analisadas", "value": f"{categories}", "icon": "tags"},
            ]
        elif aggregation == "min":
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": f"Menor Valor · {y_column}", "value": fmt_currency(safe_val(df_filtered[y_column].min())), "icon": "currency"},
                {"label": "Categorias Analisadas", "value": f"{categories}", "icon": "tags"},
            ]
        elif aggregation == "max":
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": f"Maior Valor · {y_column}", "value": fmt_currency(safe_val(df_filtered[y_column].max())), "icon": "currency"},
                {"label": "Categorias Analisadas", "value": f"{categories}", "icon": "tags"},
            ]
        elif aggregation == "median":
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": f"Mediana · {y_column}", "value": fmt_currency(safe_val(df_filtered[y_column].median())), "icon": "average"},
                {"label": "Categorias Analisadas", "value": f"{categories}", "icon": "tags"},
            ]
        else:
            kpis = [
                {"label": "Registros Analisados", "value": f"{total_rows}", "icon": "rows"},
                {"label": f"Valor Total · {y_column}", "value": fmt_currency(safe_val(df_filtered[y_column].sum())), "icon": "currency"},
                {"label": "Categorias Analisadas", "value": f"{categories}", "icon": "tags"},
            ]

        # Ensure no NaNs in lists
        values = [safe_val(v) for v in values]
        if cliente_values:
            cliente_values = [safe_val(v) for v in cliente_values]

        logging.info(f"PROCESS - Sessão: {session_id} - Gráfico gerado: {aggregation}")

        return JSONResponse(content={
            "success": True,
            "labels": labels,
            "values": values,
            "x_label": " | ".join(x_columns),
            "agg_label": AGG_LABELS.get(aggregation, aggregation),
            "cliente_labels": cliente_labels,
            "cliente_values": cliente_values,
            "kpis": kpis
        })

    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)


@app.post("/download_data")
async def download_data(payload: dict = Body(...)):
    """Exporta os dados filtrados para CSV."""
    try:
        session_id = payload.get("session_id")
        session_data = dados_memoria.get(session_id) if session_id else None
        if not session_data:
            return JSONResponse(content={"success": False, "error": "Sessão expirada. Faça upload novamente."}, status_code=400)
            
        session_data["last_accessed"] = time.time()
        df = session_data["df"]
        
        try:
            df_filtered, _, _, _, _, _ = prepare_data_for_processing(payload, df)
        except ValueError as ve:
            return JSONResponse(content={"success": False, "error": str(ve)}, status_code=400)
            
        stream = io.StringIO()
        df_filtered.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=dados_filtrados.csv"
        return response
        
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=400)

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
