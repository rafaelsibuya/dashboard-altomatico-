import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('let uploadedFileName = \'\';', 'let uploadedFileName = \'\';\n        let currentSessionId = \'\';')

toast_html = '''
    <!-- Toasts Container -->
    <div id="toast-container" class="fixed bottom-4 right-4 z-50 flex flex-col gap-2"></div>
'''
content = content.replace('<footer', toast_html + '\n    <footer')

toast_js = '''
        function showToast(message, type = 'error') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            
            let bgClass = type === 'error' ? 'bg-red-50 border-red-200 text-red-800 dark:bg-red-900/50 dark:border-red-800 dark:text-red-200' : 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-900/50 dark:border-emerald-800 dark:text-emerald-200';
            let iconHtml = type === 'error' ? 
                '<svg class="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>' :
                '<svg class="h-5 w-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
            
            toast.className = `flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg transform transition-all duration-300 translate-y-full opacity-0 ${bgClass}`;
            toast.innerHTML = `${iconHtml}<span class="text-sm font-medium">${message}</span>`;
            
            container.appendChild(toast);
            
            setTimeout(() => {
                toast.classList.remove('translate-y-full', 'opacity-0');
            }, 10);
            
            setTimeout(() => {
                toast.classList.add('translate-y-full', 'opacity-0');
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        function toggleDarkMode() {
            document.documentElement.classList.toggle('dark');
        }
        
        function exportToPDF() {
            const dashboard = document.getElementById('step-dashboard');
            html2pdf().from(dashboard).set({
                margin: 1,
                filename: 'dashboard.pdf',
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'in', format: 'a4', orientation: 'landscape' }
            }).save();
        }
'''
content = content.replace('let uploadedFileName = \'\';', 'let uploadedFileName = \'\';\n' + toast_js)

# Replace alerts with showToast
content = content.replace('alert("Por favor, envie um arquivo .xlsx");', 'showToast("Por favor, envie um arquivo .xlsx");')
content = content.replace('alert("Erro ao processar: " + result.error);', 'showToast(result.error);')
content = content.replace('alert("Erro ao conectar com o servidor.");', 'showToast("Erro ao conectar com o servidor.");')
content = content.replace('alert("Por favor, faça upload de um arquivo primeiro.");', 'showToast("Por favor, faça upload de um arquivo primeiro.");')
content = content.replace('alert("Por favor, selecione ao menos uma coluna para o eixo X.");', 'showToast("Por favor, selecione ao menos uma coluna para o eixo X.");')
content = content.replace('alert("Erro: " + result.error);', 'showToast(result.error);')

# Add session_id storing
content = content.replace('if (result.success) {', 'if (result.success) {\n                    currentSessionId = result.session_id;')

# Add session_id to payloads
content = content.replace('body: JSON.stringify(payload)', 'body: JSON.stringify({...payload, session_id: currentSessionId})')

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
