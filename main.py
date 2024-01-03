import yfinance as yf
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import tkinter as tk
from tkinter import simpledialog
import re
import threading
from telegram import Bot
from telegram import ParseMode
import datetime


# Função para verificar se o e-mail é válido
def email_valido(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# Função para enviar e-mail
def enviar_email(destinatario, assunto, corpo, remetente, senha_ou_token):
    mensagem = MIMEMultipart()
    mensagem['From'] = remetente
    mensagem['To'] = destinatario
    mensagem['Subject'] = assunto
    mensagem.attach(MIMEText(corpo, 'plain'))

    with smtplib.SMTP('smtp.gmail.com', 587) as servidor_smtp:
        servidor_smtp.starttls()
        servidor_smtp.login(remetente, senha_ou_token)
        servidor_smtp.send_message(mensagem)

# Função para enviar notificação por e-mail e no Telegram
def enviar_notificacao(destinatario, assunto, corpo, remetente, senha_ou_token, token_telegram):
    # Enviar e-mail
    enviar_email(destinatario, assunto, corpo, remetente, senha_ou_token)

    # Enviar mensagem no Telegram
    bot = Bot(token=token_telegram)
    chat_id = '-1002046197953'  # Substitua pelo seu ID de chat do Telegram
    mensagem_telegram = f"{corpo}\n\nMensagem do Compliance: Este é um aviso automático do Canal 1milhao."
    bot.send_message(chat_id=chat_id, text=mensagem_telegram, parse_mode=ParseMode.MARKDOWN)

# Função para solicitar informações do usuário usando Tkinter
def obter_informacoes_usuario():
    root = tk.Tk()
    root.withdraw()

    # Solicitar a operação desejada
    operacao = simpledialog.askstring("Operação", "Escolha a operação (compra, venda ou sair): ")
    if operacao is None or operacao.lower() == 'sair':
        return None

    while True:
        # Solicitar o símbolo do ticker
        ticker_symbol = simpledialog.askstring("Ticker Symbol", "Digite o símbolo do ticker da ação:")
        if ticker_symbol is None:
            return None

        # Adicionar automaticamente a extensão do mercado
        ticker_symbol_full = f"{ticker_symbol}.SA"

        # Solicitar o preço e o e-mail apenas se a operação for compra ou venda
        if operacao.lower() in ['compra', 'venda']:
            # Solicitar o preço alvo
            while True:
                try:
                    preco_alvo_str = simpledialog.askstring("Preço Alvo", "Digite o preço alvo para a ação:")
                    if preco_alvo_str is None:
                        return None
                    preco_alvo = float(preco_alvo_str.replace(',', '.'))
                    break
                except ValueError:
                    print("Por favor, digite um número válido para o preço alvo.")

            # Solicitar o endereço de e-mail
            while True:
                destinatario = simpledialog.askstring("Endereço de E-mail", "Digite o endereço de e-mail para notificação:")
                if destinatario is None:
                    return None
                if email_valido(destinatario):
                    break
                else:
                    print("Por favor, digite um endereço de e-mail válido.")

            return ticker_symbol_full, preco_alvo, destinatario, operacao.lower()

# Função para imprimir mensagens na janela Tkinter
def imprimir_mensagem(mensagem):
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, mensagem + "\n")
    output_text.config(state=tk.DISABLED)
    output_text.yview(tk.END)

# Função para verificar o preço-alvo
def verificar_preco_alvo(ticker_symbol, preco_alvo, destinatario, operacao, token_telegram):
    ticker_data = yf.Ticker(ticker_symbol)

    while True:
        try:
            # Obtém o preço atual
            preco_atual = ticker_data.history(period='30s')['Close'].iloc[-1]

            # Verifica se estamos dentro do horário do pregão
            horario_pregao = datetime.datetime.now().time()
            if horario_pregao < datetime.time(13, 0) or horario_pregao > datetime.time(21, 0):
                imprimir_mensagem("Fora do horário do pregão. Continuando verificação no dia seguinte.")
                # Aguardar até o próximo dia de negociação
                agora = datetime.datetime.now()
                proximo_dia = agora + datetime.timedelta(days=1)
                proximo_dia = proximo_dia.replace(hour=13, minute=0, second=0, microsecond=0)
                tempo_espera = (proximo_dia - agora).total_seconds()
                time.sleep(tempo_espera)
                continue

            # Verifica se o preço atingiu ou ultrapassou o alvo
            if (operacao == 'compra' and preco_atual >= preco_alvo) or (operacao == 'venda' and preco_atual <= preco_alvo):
                if ticker_symbol not in estados_tickers:
                    estados_tickers[ticker_symbol] = 1
                    imprimir_mensagem(f"Ticker {ticker_symbol} está sendo verificado pela primeira vez.")
                elif estados_tickers[ticker_symbol] == 1:
                    # Primeira verificação positiva
                    estados_tickers[ticker_symbol] = 2
                    imprimir_mensagem(f"Ticker {ticker_symbol} atingiu o preço-alvo pela primeira vez. Aguardando 25 minutos para a segunda verificação.")
                    tempo_segundos = 300  # Mudar aqui o tempo de espera deseja para a segunda verificacao.
                    while tempo_segundos > 0:
                        tempo_espera = min(60, tempo_segundos)  # Ajuste aqui para exibir a cada 300 segundos
                        imprimir_mensagem(f"Tempo restante para a segunda verificação de {ticker_symbol}: {tempo_segundos}s")
                        time.sleep(tempo_espera)
                        tempo_segundos -= tempo_espera

                    # Segunda verificação
                    preco_atual = ticker_data.history(period='1d')['Close'].iloc[-1]
                    if (operacao == 'compra' and preco_atual >= preco_alvo) or (operacao == 'venda' and preco_atual <= preco_alvo):
                        # Segunda verificação positiva
                        notificar_preco_alvo_alcancado(ticker_symbol, preco_alvo, preco_atual, destinatario, operacao, token_telegram)
                        imprimir_mensagem(f"Ticker {ticker_symbol} atingiu o preço-alvo pela segunda vez.")
                        break
                    else:
                        # Segunda verificação negativa
                        estados_tickers[ticker_symbol] = 0
                        #imprimir_mensagem(f"Ticker {ticker_symbol} não atingiu o preço-alvo pela segunda vez. Continuando a verificação.")
                elif estados_tickers[ticker_symbol] == 0:
                    # Segunda verificação negativa, continuar verificando
                    imprimir_mensagem(f"Ticker {ticker_symbol} está sendo verificado pela segunda vez.")
            else:
                # Preço não atingiu o alvo, continuar verificando
                imprimir_mensagem(f"Ticker {ticker_symbol} está sendo verificado pela primeira vez.")
        except Exception as e:
            imprimir_mensagem(f"Ocorreu um erro ao verificar o preço para {ticker_symbol}: {str(e)}")
            break

# Função para notificar o preço-alvo atingido
def notificar_preco_alvo_alcancado(ticker_symbol, preco_alvo, preco_atual, destinatario, operacao, token_telegram):
    ticker_symbol_sem_extensao = ticker_symbol.replace('.SA', '')
    preco_atual_formatado = "{:.2f}".format(preco_atual)

    if (operacao == 'compra' and preco_atual >= preco_alvo) or (operacao == 'venda' and preco_atual <= preco_alvo):
        mensagem = f"Operaçao de {operacao.upper()} na ação {ticker_symbol_sem_extensao} foi ativada, conforme nossa Lista Semanal! Preço alvo de {preco_alvo:.2f} foi atingido ou ultrapassado. Preço atual: {preco_atual_formatado}\n\n\n\n\n"
        mensagem_compliance = "COMPLIANCE: Este mensagem é uma sugestão de compra/venda baseada em nossa lista semanal. A compra ou venda é de total decisão e responsabilidade do Destinatário. Este e-mail contém informação CONFIDENCIAL de propriedade do Canal 1milhao e de seu DESTINATÁRIO tão somente. Se você NÃO for DESTINATÁRIO ou pessoa autorizada a recebê-lo, NÃO PODE usar, copiar, transmitir, retransmitir ou divulgar seu conteúdo (no todo ou em partes), estando sujeito às penalidades da LEI. A Lista de Ações do Canal 1milhao é devidamente REGISTRADA."
        mensagem += mensagem_compliance
        imprimir_mensagem(mensagem)

        assunto = f"Notificação Canal 1 Milhão de Preço Alvo Atingido para {ticker_symbol_sem_extensao}"
        remetente = 'testeestudos2024@gmail.com'
        senha_ou_token = 'dxjz bkse kyyb htvh'  # ou seu token, se estiver usando

        # Chamar a função enviar_notificacao apenas uma vez
        try:
            enviar_notificacao(destinatario, assunto, mensagem, remetente, senha_ou_token, token_telegram)
            imprimir_mensagem("Notificação enviada com sucesso!")
        except Exception as e:
            imprimir_mensagem(f"Erro ao enviar notificação: {str(e)}")

# Função para criar a janela Tkinter
def criar_janela(token_telegram):
    global output_text
    janela = tk.Tk()
    janela.title("Acompanhamento do Processo Lista Semanal")

    output_text = tk.Text(janela, state=tk.DISABLED, wrap=tk.WORD, height=20, width=80)
    output_text.pack(padx=10, pady=10)

    threads = []
    for ativo, preco_alvo, destinatario, operacao in ativos_e_precos:
        thread = threading.Thread(target=verificar_preco_alvo, args=(ativo, preco_alvo, destinatario, operacao, token_telegram))
        threads.append(thread)
        thread.start()

    janela.mainloop()

# Inicializa uma lista para armazenar os ativos e preços
ativos_e_precos = []

# Dicionário para rastrear o estado de cada ticker
estados_tickers = {}

# Loop para obter informações do usuário
while True:
    info_usuario = obter_informacoes_usuario()
    if info_usuario is None:
        break

    ativos_e_precos.append(info_usuario)

# Cria a janela Tkinter
token_telegram = '6750587978:AAG-kPsoLKaL0tTebyc-JCZ-bkG9jZbN7fs'  # Substitua pelo seu token do Telegram
criar_janela(token_telegram)
