import uuid
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, send_file, session, make_response)
from models import UserModel, FileModel

user_model = UserModel()
file_model = FileModel()

_COOKIE = 'remember_token'
_COOKIE_AGE = 86400

def current_user() -> dict | None:
    if 'user_id' in session:
        return user_model.get_by_id(session['user_id'])
    token = request.cookies.get(_COOKIE)
    if token:
        user = user_model.get_by_token(token)
        if user:
            session['user_id'] = user['id']
            return user
    return None

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash('Необходима авторизация', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def init_routes(app: Flask) -> None:
    @app.route('/')
    def index():
        return redirect(url_for('dashboard') if current_user() else url_for('login'))
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user():
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'
            if not username or not password:
                flash('Введите логин и пароль', 'error')
            else:
                try:
                    user = user_model.authenticate(username, password)
                    if user:
                        session['user_id'] = user['id']
                        resp = make_response(redirect(url_for('dashboard')))
                        if remember:
                            token = uuid.uuid4().hex
                            user_model.save_remember_token(user['id'], token)
                            resp.set_cookie(_COOKIE, token, max_age=_COOKIE_AGE,
                                            httponly=True, samesite='Lax')
                        flash(f'Привет, {username}!', 'success')
                        return resp
                    flash('Неверный логин или пароль', 'error')
                except ConnectionError as e:
                    flash(str(e), 'error')
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user():
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            try:
                user_model.register(username, password)
                flash('Регистрация успешна. Войдите в систему', 'success')
                return redirect(url_for('login'))
            except (ValueError, ConnectionError) as e:
                flash(str(e), 'error')
        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        user = current_user()
        if user:
            user_model.clear_token(user['id'])
        session.pop('user_id', None)
        resp = make_response(redirect(url_for('login')))
        resp.delete_cookie(_COOKIE)
        flash('Вы вышли из системы', 'success')
        return resp

    @app.route('/dashboard')
    @login_required
    def dashboard():
        user = current_user()
        files = file_model.list_files(user['id'])
        return render_template('dashboard.html', files=files, username=user['username'])

    @app.route('/files', methods=['POST'])
    @login_required
    def upload():
        user = current_user()
        if 'file' not in request.files:
            flash('Файл не найден в запросе', 'error')
            return redirect(url_for('dashboard'))
        try:
            name = file_model.save_file(request.files['file'], user['id'])
            flash(f'Файл «{name}» успешно загружен', 'success')
        except (ValueError, ConnectionError) as e:
            flash(str(e), 'error')
        except Exception:
            flash('Ошибка при загрузке файла', 'error')
        return redirect(url_for('dashboard'))

    @app.route('/files/<int:file_id>')
    @login_required
    def download(file_id: int):
        user = current_user()
        result = file_model.get_file_path(file_id, user['id'])
        if result:
            path, original = result
            return send_file(path, as_attachment=True, download_name=original)
        flash('Файл не найден', 'error')
        return redirect(url_for('dashboard'))

    @app.route('/files/<int:file_id>/delete', methods=['POST'])
    @login_required
    def delete_file(file_id: int):
        user = current_user()
        if file_model.delete_file(file_id, user['id']):
            flash('Файл успешно удалён', 'success')
        else:
            flash('Файл не найден', 'error')
        return redirect(url_for('dashboard'))
