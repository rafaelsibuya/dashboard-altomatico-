#!/usr/bin/env ruby

require 'time'
require 'json'

log_file = File.join(__dir__, '..', 'system.log')

unless File.exist?(log_file)
  puts "Relatório de Uso - Sibuyatech"
  puts "------------------------------"
  puts "Nenhum arquivo de log encontrado (system.log)."
  exit
end

uploads = 0
security_blocks = 0
analyses = 0
errors = 0

File.foreach(log_file) do |line|
  begin
    # Exemplo de log: 2026-08-01 21:00:00 - INFO - UPLOAD - Sessão: 1234 - Arquivo: vendas.xlsx
    if line.include?("UPLOAD")
      uploads += 1
    elsif line.include?("SECURITY_BLOCK")
      security_blocks += 1
    elsif line.include?("PROCESS")
      analyses += 1
    elsif line.include?("ERROR")
      errors += 1
    end
  rescue StandardError => e
    # ignora linhas mal formatadas
  end
end

puts "============================================="
puts "      RELATÓRIO DE USO - SIBUYATECH          "
puts "============================================="
puts "Data da emissão: #{Time.now.strftime('%d/%m/%Y %H:%M')}"
puts "---------------------------------------------"
puts "Estatísticas Totais:"
puts " - Uploads de Planilhas: #{uploads}"
puts " - Análises Geradas:     #{analyses}"
puts " - Bloqueios de Segurança: #{security_blocks} (Rust Layer)"
puts " - Erros Detectados:     #{errors}"
puts "============================================="
