import argparse
import logging
import smtplib
import sys
import time
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error as MySQLError
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

load_dotenv()

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": "mailer",
}

SMTP_CONFIG = {
    "host": "smtp.gmail.com",
    "port": 465,
    "username": os.getenv("EMAIL_USER"),
    "password": os.getenv("EMAIL_PASSWORD"),
    "sender_name": "Рассылка",
    "use_tls": True,
}

@dataclass
class Recipient:
    id: int
    email: str
    name: str

class RecipientRepository:
    CREATE_RECIPIENTS = """
    CREATE TABLE IF NOT EXISTS recipients (
        id     INT AUTO_INCREMENT PRIMARY KEY,
        email  VARCHAR(255) NOT NULL UNIQUE,
        name   VARCHAR(255) NOT NULL DEFAULT '',
        active TINYINT(1)   NOT NULL DEFAULT 1
    )
    """
    CREATE_LOG = """
    CREATE TABLE IF NOT EXISTS send_log (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        recipient_id INT NOT NULL,
        subject      VARCHAR(255),
        sent_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
        success      TINYINT(1) NOT NULL DEFAULT 1,
        error_msg    TEXT,
        FOREIGN KEY (recipient_id) REFERENCES recipients(id)
    )
    """

    def __init__(self):
        self._conn = None

    def __enter__(self):
        try:
            self._conn = mysql.connector.connect(**DB_CONFIG)
            cur = self._conn.cursor()
            cur.execute(self.CREATE_RECIPIENTS)
            cur.execute(self.CREATE_LOG)
            self._conn.commit()
            cur.close()
        except MySQLError as exc:
            log.error("Не удалось подключиться к MySQL: %s", exc)
            raise
        return self

    def __exit__(self, *_):
        if self._conn and self._conn.is_connected():
            self._conn.close()

    def get_active_recipients(self) -> list[Recipient]:
        cur = self._conn.cursor(dictionary=True)
        cur.execute("SELECT id, email, name FROM recipients WHERE active = 1")
        rows = cur.fetchall()
        cur.close()
        return [Recipient(r["id"], r["email"], r["name"]) for r in rows]

    def log_send(self, recipient_id: int, subject: str, success: bool, error_msg: str = "") -> None:
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO send_log (recipient_id, subject, success, error_msg)"
            "VALUES (%s, %s, %s, %s)",
            (recipient_id, subject, int(success), error_msg)
        )
        self._conn.commit()
        cur.close()

    def seed(self, samples: list[tuple[str, str]]) -> None:
        cur = self._conn.cursor()
        cur.executemany("INSERT IGNORE INTO recipients (email, name) VALUES (%s, %s)", samples)
        self._conn.commit()
        cur.close()
        log.info("Добавлено %d тестовых адресатов", len(samples))

class Mailer:
    def send(self, recipient: Recipient, subject: str,
             body_text: str, body_html: Optional[str] = None) -> bool:
        cfg = SMTP_CONFIG
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{cfg['sender_name']} <{cfg['username']}>"
        msg["To"] = (f"{recipient.name} <{recipient.email}>" if recipient.name else recipient.email)
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        try:
            if cfg["use_tls"]:
                server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=15)
            else:
                server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=15)
                server.starttls()
            with server:
                server.login(cfg["username"], cfg["password"])
                server.sendmail(cfg["username"], recipient.email, msg.as_bytes())
            log.info("Отправлено → %s <%s>", recipient.name, recipient.email)
            return True
        except smtplib.SMTPAuthenticationError:
            log.error("Ошибка авторизации SMTP")
        except smtplib.SMTPRecipientsRefused:
            log.error("Адрес отклонён сервером: %s", recipient.email)
        except smtplib.SMTPException as exc:
            log.error("SMTP ошибка для %s: %s", recipient.email, exc)
        except OSError as exc:
            log.error("Ошибка соединения с SMTP: %s", exc)
        return False

class MailingService:
    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.mailer = Mailer()

    def run(self, subject: str, body_text: str, body_html: Optional[str] = None) -> None:
        with RecipientRepository() as repo:
            recipients = repo.get_active_recipients()
            if not recipients:
                log.warning("В базе нет активных адресатов.")
                return
            log.info("Начало рассылки: %d адресатов", len(recipients))
            sent = failed = 0
            for r in recipients:
                name = r.name or "Уважаемый получатель"
                text = body_text.replace("{name}", name)
                html = body_html.replace("{name}", name) if body_html else None
                ok = self.mailer.send(r, subject, text, html)
                repo.log_send(r.id, subject, ok)
                if ok:
                    sent += 1
                else:
                    failed += 1
                time.sleep(self.delay)
        log.info("Отправлено: %d, Ошибок: %d", sent, failed)

def main():
    parser = argparse.ArgumentParser(description="Почтовая рассылка из MySQL")
    parser.add_argument("--subject", default="Рассылка", help="Тема письма")
    parser.add_argument("--body", default="Здравствуйте, {name}!\n\nЭто тестовое письмо",
                        help="Текст письма")
    parser.add_argument("--html", help="Путь к HTML файлу письма")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Задержка между письмами в сек (по умолчанию 0.5)")
    parser.add_argument("--init-db", action="store_true",
                        help="Создать таблицы и добавить тестовых адресатов")
    args = parser.parse_args()
    if args.init_db:
        with RecipientRepository() as repo:
            repo.seed([
                ("steshitz.jora2017@yandex.by", "George")
            ])
        log.info("БД инициализирована")
        sys.exit(0)
    body_html = None
    if args.html:
        try:
            from pathlib import Path
            body_html = Path(args.html).read_text(encoding="utf-8")
        except OSError as exc:
            log.error("Не удалось прочитать HTML-файл: %s", exc)
            sys.exit(1)
    MailingService(delay=args.delay).run(args.subject, args.body, body_html)

if __name__ == "__main__":
    main()