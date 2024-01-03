from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import sqlite3


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/User/pythonProject2/banco_dados.db'
app.config['UPLOAD_FOLDER'] = 'static'

db = SQLAlchemy(app)

# Crie uma classe de modelo para a tabela
class PrecosAtingidos(db.Model):
    __tablename__ = 'precos_atingidos'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(255))  # Adicione mais campos conforme necessário
    ticker_symbol = db.Column(db.String(255))
    preco_alvo = db.Column(db.Float)
    preco_atual = db.Column(db.Float)
    data_saida = db.Column(db.String(255))
    stop_loss = db.Column(db.Float)
    operacao = db.Column(db.String(255))


@app.route('/')
def index():
    try:
        # Recupere dados do banco de dados
        data = PrecosAtingidos.query.all()
        print(data)
    except Exception as e:
        print(f"Erro ao recuperar dados do banco de dados: {e}")
    return render_template('index.html', data=data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)






