with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

csv_btn = '''
                    <button onclick="exportDataCSV()"
                        class="inline-flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-600 hover:text-emerald-700 hover:border-emerald-300 shadow-sm transition-colors">
                        <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                        Baixar CSV
                    </button>
'''
content = content.replace('Exportar PDF\n                    </button>', 'Exportar PDF\n                    </button>' + csv_btn)

csv_fn = '''
        async function exportDataCSV() {
            const cols = getEffectiveColumns();
            const clienteCol = cols.find(c => String(c).toLowerCase().includes('cliente'));
            const payload = {
                ignored_indexes: Array.from(ignoredRows),
                header_index: currentHeaderIndex,
                x_columns: Array.from(selectedXCols),
                y_column: document.getElementById('select-y').value,
                aggregation: document.getElementById('select-agg').value,
                cliente_column: clienteCol || null,
                session_id: currentSessionId
            };
            
            try {
                const response = await fetch('/download_data', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'dados_filtrados.csv';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                } else {
                    const result = await response.json();
                    showToast(result.error);
                }
            } catch (e) {
                showToast("Erro ao baixar CSV.");
            }
        }
'''
content = content.replace('function exportToPDF() {', csv_fn + '\n        function exportToPDF() {')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done adding CSV button")
