with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: ensure columns are strings
text = text.replace('df.columns = df.iloc[0]', 'df.columns = df.iloc[0].astype(str)')

# Fix 2: smart numeric detection
smart_numeric = '''def _looks_numeric(series):
    if any(x in str(series.name).lower() for x in ['id', 'código', 'codigo', 'cep', 'telefone', 'cpf', 'cnpj']):
        return False
    s = series.astype(str).str.strip()
    s = s[s != ""]
    s = s.head(200)
    if len(s) < 3:
        return False
    ok = sum(1 for v in s if _to_float(v) is not None)
    return ok / len(s) >= 0.7'''

text = text.replace('''def _looks_numeric(series):
    s = series.astype(str).str.strip()
    s = s[s != ""].head(200)
    if len(s) < 3:
        return False
    ok = sum(1 for v in s if _to_float(v) is not None)
    return ok / len(s) >= 0.7''', smart_numeric)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Fix 3: x_columns being numeric instead of string causing Set.has() to fail
js_fix = '''        function applySuggestion(idx) {
            const sug = currentSuggestions[idx];
            if (!sug) return;

            selectedXCols = new Set((sug.x_columns || []).map(String));
            document.querySelectorAll('#multi-x-list .x-col-cb').forEach(cb => {
                cb.checked = selectedXCols.has(cb.value);
            });
            renderXChips(getEffectiveColumns());
            syncXTrigger();

            document.getElementById('select-y').value = String(sug.y_column);
            document.getElementById('select-agg').value = sug.aggregation;
            document.getElementById('select-chart-type').value = sug.chart_type;

            document.getElementById('btn-generate').click();
        }'''

html = html.replace('''        function applySuggestion(idx) {
            const sug = currentSuggestions[idx];
            if (!sug) return;

            selectedXCols = new Set(sug.x_columns || []);
            document.querySelectorAll('#multi-x-list .x-col-cb').forEach(cb => {
                cb.checked = selectedXCols.has(cb.value);
            });
            renderXChips(getEffectiveColumns());
            syncXTrigger();

            document.getElementById('select-y').value = sug.y_column;
            document.getElementById('select-agg').value = sug.aggregation;
            document.getElementById('select-chart-type').value = sug.chart_type;

            document.getElementById('btn-generate').click();
        }''', js_fix)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
