#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import threading
import subprocess
import platform
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Caminho absoluto para o arquivo .json
JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'equipamentos.json')

# Carrega o arquivo JSON (ou cria um novo, se não existir)
def carregar_equipamentos():
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# Salva a lista de equipamentos no arquivo JSON
def salvar_equipamentos(equipamentos):
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(equipamentos, f, ensure_ascii=False, indent=4)

# Função para checar conectividade (ping) em cada IP a cada 5s
def monitorar_equipamentos():
    while True:
        equipamentos = carregar_equipamentos()
        for equip in equipamentos:
            ip = equip.get('ip')
            if ip:
                resultado_ping = ping_equipamento(ip)
                print(f"Pingando {ip}... Resultado: {'ATIVO' if resultado_ping else 'INATIVO'}")
                if resultado_ping:
                    equip['status'] = 'ATIVO'
                else:
                    equip['status'] = 'INATIVO'
        salvar_equipamentos(equipamentos)
        time.sleep(5)

# Ping simples (multiplataforma)
def ping_equipamento(ip):
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', ip]
    try:
        return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    except Exception as e:
        print(f"Erro ao tentar pingar {ip}: {e}")
        return False

# Thread que faz o monitoramento contínuo em segundo plano
monitor_thread = threading.Thread(target=monitorar_equipamentos, daemon=True)

@app.route('/')
def index():
    return render_template('index.html')  # index.html na pasta templates

@app.route('/api/equipamentos', methods=['GET', 'POST', 'DELETE'])
def api_equipamentos():
    """
    - GET: Retorna a lista de equipamentos (com status).
    - POST: Adiciona novo equipamento, salva no .json.
    - DELETE: Remove equipamento(s) com base em algum identificador.
    """
    if request.method == 'GET':
        equipamentos = carregar_equipamentos()
        return jsonify(equipamentos)

    elif request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({'erro': 'Dados inválidos'}), 400

        # Esperamos que o front envie algo como:
        # { "ip": "100.100.100.100", "nome": "Equipamento X", "endereco": "Endereço X" }
        novo_ip = data.get('ip')
        novo_nome = data.get('nome')
        novo_endereco = data.get('endereco')

        if not (novo_ip and novo_nome and novo_endereco):
            return jsonify({'erro': 'Campos obrigatórios estão faltando!'}), 400

        equipamentos = carregar_equipamentos()
        # Insere estado inicial (vamos deixar como INATIVO, o loop de monitoramento atualiza depois)
        equipamentos.append({
            'ip': novo_ip,
            'nome': novo_nome,
            'endereco': novo_endereco,
            'status': 'INATIVO'  # Inicializa como INATIVO
        })

        salvar_equipamentos(equipamentos)
        return jsonify({'mensagem': 'Equipamento adicionado com sucesso!'}), 201

    elif request.method == 'DELETE':
        data = request.json
        if not data or 'ips' not in data:
            return jsonify({'erro': 'Nenhum IP enviado para exclusão'}), 400

        equipamentos = carregar_equipamentos()
        excluir_ips = data['ips']  # lista de IPs a excluir

        # Remove equipamentos com base nos IPs recebidos
        equipamentos = [equip for equip in equipamentos if equip['ip'] not in excluir_ips]

        salvar_equipamentos(equipamentos)
        return jsonify({'mensagem': 'Equipamentos excluídos com sucesso!'}), 200

# Iniciar a thread de monitoramento antes de rodar o servidor
monitor_thread.start()

if __name__ == '__main__':
    # Aguardar 5 segundos e abrir o navegador automaticamente (opcional)
    def abrir_navegador():
        time.sleep(5)
        # Em SOs Linux com ambiente gráfico, xdg-open é comum.
        # subprocess.Popen(['xdg-open', 'http://localhost:5050'])

    threading.Thread(target=abrir_navegador, daemon=True).start()

    # Executa o Flask na porta 5500
    app.run(host='0.0.0.0', port=5500, debug=False)
