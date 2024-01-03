from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from telegram import Bot
import pdfkit
import os
import schedule
import time
import smtplib

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/User/pythonProject2/banco_dados.db'
app.config['UPLOAD_FOLDER'] = 'static'

db = SQLAlchemy(app)


class PrecosAtingidos(db.Model):
    __tablename__ = 'precos_atingidos'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(255))
    ticker_symbol = db.Column(db.String(255))
    preco_alvo = db.Column(db.Float)
    preco_atual = db.Column(db.Float)
    data_saida = db.Column(db.String(255))
    stop_loss = db.Column(db.Float)
    operacao = db.Column(db.String(255))


# Função para gerar o PDF
def gerar_pdf(data):
    print("Gerando PDF...")
    wkhtmltopdf_path = 'C:\\Users\\User\\pythonProject2\\wkhtmltopdf.exe'
    pdfkit_options = {
        'page-size': 'A4',
        'encoding': 'UTF-8',
        'no-images': '',  # Evita o download de imagens externas
        'disable-external-links': '',  # Desativa os links externos
    }

    with app.app_context():
        with app.test_request_context('/'):
            html_content = render_template('index.html', data=data)
            pdfkit.from_string(html_content, 'relatorio.pdf', options=pdfkit_options, configuration=pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path))







# Função para enviar e-mail
def enviar_email():
    print("Enviando e-mail...")

    with app.app_context():
        email_from = 'testeestudos2024@gmail.com'
        email_password = 'dxjz bkse kyyb htvh'
        email_to = 'xande5@hotmail.com'  # Substitua pelo e-mail do destinatário

        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = 'Relatório Semanal'

        # Corpo do e-mail
        body = 'Olá, segue o relatório semanal em anexo.'
        msg.attach(MIMEText(body, 'plain'))

        # Anexar o PDF ao e-mail
        with open('relatorio.pdf', 'rb') as attachment:
            part = MIMEApplication(attachment.read(), Name='relatorio.pdf')
            part['Content-Disposition'] = 'attachment; filename=relatorio.pdf'
            msg.attach(part)

        # Configurações do servidor SMTP do Gmail
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_from, email_password)
            server.send_message(msg)


# Função para enviar mensagem pelo Telegram
def enviar_telegram():
    print("Enviando mensagem pelo Telegram...")

    chat_id = '-1002046197953'
    token_telegram = '6750587978:AAG-kPsoLKaL0tTebyc-JCZ-bkG9jZbN7fs'

    bot = Bot(token_telegram)
    with open('relatorio.pdf', 'rb') as pdf_file:
        bot.send_document(chat_id, document=pdf_file)


# Função para tarefa agendada
def tarefa_agendada():
    with app.app_context():
        try:
            print("Iniciando tarefa agendada...")
            data = PrecosAtingidos.query.all()
            gerar_pdf(data)
            enviar_email()
            enviar_telegram()
            print('Relatório enviado com sucesso!')
        except Exception as e:
            print(f"Erro ao processar tarefa agendada: {e}")


# Agendar tarefa para todas as terças-feiras às 21:30
#schedule.every().tuesday.at('22:17').do(tarefa_agendada)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    while True:
        schedule.run_pending()
        time.sleep(1)







