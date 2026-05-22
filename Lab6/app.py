from flask import Flask
from routes import init_routes
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
init_routes(app)

if __name__ == '__main__':
    app.run(debug=False, port=5000, host='0.0.0.0')
