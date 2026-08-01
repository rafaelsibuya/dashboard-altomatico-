with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix the suggestions bug overriding session_id
text = text.replace('currentSessionId = result.session_id;\n                    renderSuggestions(result.suggestions || []);', 'renderSuggestions(result.suggestions || []);')
text = text.replace('currentSessionId = result.session_id;\n                    renderKpis(result.kpis);', 'renderKpis(result.kpis);')

# Also fix the alert for dashboard generation to use toast
text = text.replace('alert("Erro ao gerar dashboard: " + result.error);', 'showToast("Erro ao gerar dashboard: " + result.error);')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed session_id bug')
