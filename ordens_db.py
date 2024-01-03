import yfinance as yf
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import threading
from telegram import Bot
from telegram import ParseMode
import tkinter as tk
from tkinter import simpledialog
import datetime
import time
import sys
# Importe a função de inserção do módulo externo
from banco_dados import inserir_preco_atingido

# No início do script, adicione a seguinte função para exibir mensagens no widget `console_output`:
def exibir_mensagem(message, text_widget):
    text_widget.config(state=tk.NORMAL)
    text_widget.insert(tk.END, f"{message}\n")
    text_widget.config(state=tk.DISABLED)
    text_widget.yview(tk.END)

# Constantes
HORARIO_INICIO_PREGAO = datetime.time(13, 0, 0)
HORARIO_FIM_PREGAO = datetime.time(21, 0, 0)
INTERVALO_VERIFICACAO = 50
TEMPO_ACUMULADO_MAXIMO = 1500


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

def custom_print(message):
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, f"{message}\n")
    output_text.config(state=tk.DISABLED)
    output_text.yview(tk.END)
# Antes da função `verificar_preco_alvo`, adicione as seguintes linhas para criar o widget `console_output`:
console_output = None


# Função para verificar o preço-alvo
def verificar_preco_alvo(ticker_symbol, preco_alvo, destinatario, operacao, token_telegram):
    ticker_data = yf.Ticker(ticker_symbol)
    tempo_acumulado = 0
    dentro_do_pregao = False

    try:
        primeira_verificacao = False  # Adiciona uma flag para controlar a primeira verificação

        while True:
            # Obtém o preço atual
            preco_atual = ticker_data.history(period='60s')['Close'].iloc[-1]

            # Verifica se estamos dentro do horário do pregão
            horario_pregao = datetime.datetime.now().time()

            if HORARIO_INICIO_PREGAO <= horario_pregao <= HORARIO_FIM_PREGAO:
                # Coloque aqui o código que você deseja executar durante o pregão
                print("Dentro do horário do pregão. Realizando buscas...")
            else:
                print("Fora do horário do pregão. Aguardando até o início do pregão...")

                agora = datetime.datetime.now()
                inicio_pregao_hoje = agora.replace(hour=HORARIO_INICIO_PREGAO.hour, minute=0, second=0, microsecond=0)

                # Se o horário atual for antes do início do pregão, inicia as buscas hoje
                if agora < inicio_pregao_hoje:
                    proximo_dia = inicio_pregao_hoje
                    print("Início das buscas ocorrerá no mesmo dia.")
                else:
                    # Caso contrário, inicia as buscas no próximo dia
                    proximo_dia = agora + datetime.timedelta(hours=16)
                    proximo_dia = proximo_dia.replace(hour=HORARIO_INICIO_PREGAO.hour, minute=0, second=0,
                                                      microsecond=0)
                    print("Início das buscas ocorrerá no dia seguinte.")

                tempo_espera = (proximo_dia - agora).total_seconds()
                time.sleep(tempo_espera)

                continue  # Continua para o próximo ticker no mesmo dia ou no próximo dia

            # Verifica se o preço atingiu ou ultrapassou o alvo
            if (operacao == 'compra' and preco_atual >= preco_alvo) or (
                    operacao == 'venda' and preco_atual <= preco_alvo):
                if ticker_symbol not in estados_tickers:
                    estados_tickers[ticker_symbol] = 1
                    imprimir_mensagem(f"Ticker {ticker_symbol} atingiu o preço alvo pela primeira vez.")
                elif estados_tickers[ticker_symbol] == 1:
                    # Primeira verificação positiva
                    estados_tickers[ticker_symbol] = 2
                    dentro_do_pregao = True  # Indica que estamos dentro do pregão

                elif estados_tickers[ticker_symbol] == 2 and dentro_do_pregao:
                    # Segunda verificação durante o pregão
                    if (operacao == 'compra' and preco_atual >= preco_alvo) or (
                            operacao == 'venda' and preco_atual <= preco_alvo):

                        if not primeira_verificacao:
                            # Se for a primeira verificação positiva, inicia o tempo acumulado
                            primeira_verificacao = True
                            imprimir_mensagem(
                                f"Ticker {ticker_symbol} Aguardando contagem de tempo acumulado.")

                        if primeira_verificacao:

                            tempo_acumulado += (INTERVALO_VERIFICACAO + 10)  # Adiciona 60 segundos ao tempo acumulado
                            imprimir_mensagem(
                                f"Tempo acumulado para {ticker_symbol}: {tempo_acumulado}s")

                            # Verifica se o tempo acumulado atingiu 25 minutos
                            if tempo_acumulado >= TEMPO_ACUMULADO_MAXIMO:
                                notificar_preco_alvo_alcancado(ticker_symbol, preco_alvo, preco_atual, destinatario,
                                                               operacao, token_telegram)
                                imprimir_mensagem(f"Ticker {ticker_symbol} atingiu o tempo acumulado. Notificação enviada.")
                                # Não verifica mais o ticker no mesmo dia
                                break
                    else:
                        # Se não atender aos critérios, volta ao estado 0
                        estados_tickers[ticker_symbol] = 0
                        imprimir_mensagem(
                            f"Ticker {ticker_symbol} não atingiu o preço-alvo pela segunda vez. Continuando a verificação.")
                        break  # Não verifica mais o ticker no mesmo dia
                else:
                    # Se não estiver no estado 1 ou 2, continua verificando
                    imprimir_mensagem(f"Ticker {ticker_symbol} está sendo verificado pela segunda vez.")
                    break  # Não verifica mais o ticker no mesmo dia

            else:
                # Se não estiver no estado 1 ou 2, continua verificando
                imprimir_mensagem(f"Ticker {ticker_symbol} está sendo monitorado...")


            # Adiciona um intervalo de tempo para evitar verificações frequentes
            time.sleep(INTERVALO_VERIFICACAO)  # Aguarda 50 segundos entre as verificações

    except Exception as e:
        imprimir_mensagem(f"Ocorreu um erro ao verificar o preço para {ticker_symbol}: {str(e)}")

# Função para notificar o preço-alvo atingido
def notificar_preco_alvo_alcancado(ticker_symbol, preco_alvo, preco_atual, destinatario, operacao, token_telegram):
    ticker_symbol_sem_extensao = ticker_symbol.replace('.SA', '')
    preco_atual_formatado = "{:.2f}".format(preco_atual)

    # Altere a linha abaixo para incluir apenas data_atual, ticker_simbol, preco_alvo e preco_atual
    inserir_preco_atingido(operacao.upper(), ticker_symbol, preco_alvo, preco_atual, data_saida='', stop_loss=0)
    print(f"Dados inseridos no banco de dados para {ticker_symbol}, Preço Atual: {preco_atual}")

    if (operacao == 'compra' and preco_atual >= preco_alvo) or (operacao == 'venda' and preco_atual <= preco_alvo):
        mensagem = f"Operaçao de {operacao.upper()} na ação {ticker_symbol_sem_extensao} foi axantivada, conforme nossa Lista Semanal! Preço alvo de {preco_alvo:.2f} foi atingido ou ultrapassado. Preço atual: {preco_atual_formatado}\n\n\n\n\n"
        mensagem_compliance = "COMPLIANCE: Este mensagem é uma sugestão de compra/venda baseada em nossa lista semanal. A compra ou venda é de total decisão e responsabilidade do Destinatário. Este e-mail contém informação CONFIDENCIAL de propriedade do Canal 1milhao e de seu DESTINATÁRIO tão somente. Se você NÃO for DESTINATÁRIO ou pessoa autorizada a recebê-lo, NÃO PODE usar, copiar, transmitir, retransmitir ou divulgar seu conteúdo (no todo ou em partes), estando sujeito às penalidades da LEI. A Lista de Ações do Canal 1milhao é devidamente REGISTRADA."
        mensagem += mensagem_compliance
        imprimir_mensagem(mensagem)

        assunto = f"Notificação Canal 1 Milhão de Preço Alvo Atingido para {ticker_symbol_sem_extensao}"
        remetente = 'testeestudos2024@gmail.com'
        senha_ou_token = 'dxjz bkse kyyb htvh'  # ou seu token, se estiver usando

        # Chamar a função enviar_notificacao apenas uma vez
        try:
            enviar_notificacao(destinatario, assunto, mensagem, remetente, senha_ou_token, token_telegram)
            imprimir_mensagem("Notificação enviada com sucesso e atualizada no banco de dados!")
        except Exception as e:
            imprimir_mensagem(f"Erro ao enviar notificação: {str(e)}")

# Variáveis compartilhadas para o estado de cada ticker
estados_tickers = {}
estados_tickers_var = {}
output_text = None

# Função para criar a janela Tkinter
def criar_janela(token_telegram):
    global output_text
    global estados_tickers_var
    global ativos_e_precos  # Adicione esta linha
    global console_output

    # Função para atualizar o estado do ticker na interface
    def atualizar_estado_ticker_interface():
        global estados_tickers_var

        for ticker, estado_var in estados_tickers_var.items():
            estado = estados_tickers.get(ticker, "0")  # Obtém o estado do ticker do dicionário
            estado_var.set(estado)

        # Chama a função novamente após 60.000 milisegundos (60 segundo)
        output_text.after(60000, atualizar_estado_ticker_interface)


    janela = tk.Tk()
    janela.title("ORDENS DE COMPRA E VENDA - ACOMPANHAMENTO")

    # Configuração de cores
    janela.configure(bg='black')  # Define a cor de fundo para preto

    output_text = tk.Text(janela, state=tk.DISABLED, wrap=tk.WORD, height=20, width=80, bg='black', fg='white')
    output_text.pack(padx=10, pady=10)

    # Inicializa variáveis compartilhadas para o estado de cada ticker
    for ativo, _, _, _ in ativos_e_precos:
        estados_tickers_var[ativo] = tk.StringVar()
        estados_tickers_var[ativo].set("0")

    # Cria rótulos para cada ticker na interface do Tkinter
    for ativo, preco_alvo, destinatario, operacao in ativos_e_precos:
        label_text = f"Operação: {operacao.capitalize()} / Ticker: {ativo} / Preço: {preco_alvo:.2f}"
        tk.Label(janela, text=label_text, bg='black', fg='yellow').pack()  # Define a cor de fundo e de texto para preto e branco

    # Adiciona um novo widget Text para exibir os prints
    tk.Label(janela, text=" ROBOT DE ALERTA CANAL DO MILHÃO", bg='black', fg='green').pack()
    console_output = tk.Text(janela, state=tk.DISABLED, wrap=tk.WORD, height=10, width=80)
    console_output.pack(padx=10, pady=10)

    # Substitui a função print para redirecionar para o novo widget Text
    def custom_print(message):
        exibir_mensagem(message, console_output)

    # Substitui a função print
    sys.modules['__main__'].print = custom_print


    # Inicia a atualização contínua da interface
    janela.after(60000, lambda: atualizar_interface(output_text))

    threads = []
    for ativo, preco_alvo, destinatario, operacao in ativos_e_precos:
        thread = threading.Thread(target=verificar_preco_alvo, args=(ativo, preco_alvo, destinatario, operacao, token_telegram))
        threads.append(thread)
        thread.start()

    janela.mainloop()

# Função para atualizar a interface do Tkinter
def atualizar_interface(output_text):
    global estados_tickers_var

    for ticker, estado in estados_tickers_var.items():
        output_text.config(state=tk.NORMAL)
        #output_text.insert(tk.END, f"Ticker {ticker}: Estado {estado.get()}\n")
        output_text.config(state=tk.DISABLED)
        output_text.yview(tk.END)

    # Chama a função novamente após 60000 milissegundos (60 segundo)
    output_text.after(60000, lambda: atualizar_interface(output_text))


# Lista para armazenar os ativos e preços
ativos_e_precos = []

# Loop para obter informações do usuário
while True:
    info_usuario = obter_informacoes_usuario()
    if info_usuario is None:
        break

    ativos_e_precos.append(info_usuario)

# Cria a janela Tkinter
token_telegram = '6750587978:AAG-kPsoLKaL0tTebyc-JCZ-bkG9jZbN7fs'  # Substitua pelo seu token do Telegram
criar_janela(token_telegram)

