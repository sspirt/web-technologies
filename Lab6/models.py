import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': os.getenv("MYSQL_PASSWORD"),
    'database': 'filemanager',
    'charset': 'utf8mb4',
}

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip',
                      'py', 'docx', 'xlsx', 'csv', 'json', 'xml', 'mp3', 'mp4'}

class Database:
    def __enter__(self):
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            return self.cursor, self.conn
        except Error as e:
            raise ConnectionError(f"Ошибка подключения к БД: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cursor.close()
        self.conn.close()

class UserModel:
    def register(self, username: str, password: str) -> None:
        username = username.strip()
        if not username or not password:
            raise ValueError("Логин и пароль не могут быть пустыми")
        if len(username) < 3:
            raise ValueError("Логин должен содержать минимум 3 символа")
        if len(password) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        with Database() as (cur, _):
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                raise ValueError(f"Пользователь «{username}» уже существует")
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, generate_password_hash(password)))

    def authenticate(self, username: str, password: str) -> dict | None:
        with Database() as (cur, _):
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
        if user and check_password_hash(user['password'], password):
            return user
        return None

    def get_by_id(self, user_id: int) -> dict | None:
        with Database() as (cur, _):
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()

    def save_remember_token(self, user_id: int, token: str) -> None:
        with Database() as (cur, _):
            cur.execute("UPDATE users SET remember_token = %s, "
                        "token_expires = DATE_ADD(NOW(), INTERVAL 1 DAY) WHERE id = %s",
                        (token, user_id))

    def get_by_token(self, token: str) -> dict | None:
        with Database() as (cur, _):
            cur.execute("SELECT * FROM users WHERE remember_token = %s AND token_expires > NOW()",
                        (token,))
            return cur.fetchone()

    def clear_token(self, user_id: int) -> None:
        with Database() as (cur, _):
            cur.execute("UPDATE users SET remember_token = NULL, token_expires = NULL WHERE id = %s",
                        (user_id,))

class FileModel:
    def __init__(self, upload_folder: str = 'uploads'):
        self.upload_folder = upload_folder
        os.makedirs(self.upload_folder, exist_ok=True)

    def _allowed(self, filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def _fmt_size(size: int) -> str:
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} ТБ"

    def list_files(self, user_id: int) -> list[dict]:
        with Database() as (cur, _):
            cur.execute("SELECT * FROM files WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
            rows = cur.fetchall()
        for r in rows:
            p = os.path.join(self.upload_folder, r['filename'])
            r['size'] = self._fmt_size(os.path.getsize(p)) if os.path.isfile(p) else '—'
        return rows

    def save_file(self, file, user_id: int) -> str:
        if not file or not file.filename:
            raise ValueError("Файл не выбран")
        original = file.filename
        filename = secure_filename(original)
        if not filename:
            raise ValueError("Некорректное имя файла")
        if not self._allowed(filename):
            raise ValueError("Тип файла не поддерживается")
        dest = os.path.join(self.upload_folder, filename)
        if os.path.exists(dest):
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{uuid.uuid4().hex[:6]}{ext}"
            dest = os.path.join(self.upload_folder, filename)
        file.save(dest)
        with Database() as (cur, _):
            cur.execute("INSERT INTO files (filename, original_name, user_id, uploaded_at) "
                        "VALUES (%s, %s, %s, NOW())", (filename, original, user_id))
        return original

    def get_file_path(self, file_id: int, user_id: int) -> tuple[str, str] | None:
        with Database() as (cur, _):
            cur.execute("SELECT * FROM files WHERE id = %s AND user_id = %s", (file_id, user_id))
            row = cur.fetchone()
        if row:
            path = os.path.join(self.upload_folder, row['filename'])
            if os.path.isfile(path):
                return path, row['original_name']
        return None

    def delete_file(self, file_id: int, user_id: int) -> bool:
        with Database() as (cur, _):
            cur.execute("SELECT * FROM files WHERE id = %s AND user_id = %s", (file_id, user_id))
            row = cur.fetchone()
        if not row:
            return False
        path = os.path.join(self.upload_folder, row['filename'])
        if os.path.isfile(path):
            os.remove(path)
        with Database() as (cur, _):
            cur.execute("DELETE FROM files WHERE id = %s AND user_id = %s", (file_id, user_id))
        return True
