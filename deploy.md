# Деплой на VPS (без CI/CD)

Сайт: **https://programism.ru/** — этот же домен используется во всех примерах ниже (Nginx, certbot, переменные Django). При другом домене замените `server_name`, `ALLOWED_HOSTS`, certbot `-d` и примеры `curl` на свой хост.

Стек: Django 5.x, Gunicorn, Nginx, systemd. Ручное обновление кода (`git pull` или копирование архива).

Структура репозитория: в корне **`manage.py`**, пакет настроек Django — **`config/`** (файл `config/settings.py`), приложение **`quiz/`**. После миграций в корне появится **`db.sqlite3`**; после `collectstatic` — каталог **`staticfiles/`** (см. `STATIC_ROOT` в `settings.py`). Отдельного `MEDIA_ROOT` в проекте нет — блок `/media/` в Nginx опционален.

---

## 1. VPS и DNS

- ОС: Ubuntu 22.04/24.04 LTS (или Debian).
- Открыть в фаерволе: **22** (SSH), **80**, **443**.
- DNS: записи **A** (и при необходимости **AAAA**) для **`programism.ru`** и при использовании **www** — для **`www.programism.ru`** → публичный IP VPS. В панели DNS указывают имя хоста без префикса `https://`.

---

## 2. Пакеты на сервере

Дальше команды рассчитаны на **сессию под root** (`ssh root@…` на VPS или `sudo -i`).

```bash
apt update && apt install -y python3-venv python3-dev build-essential nginx git
```

Код проекта — в **`/home/exam_up`** (корень репозитория с `manage.py`).

---

## 3. Код на сервер

Создайте каталог на VPS (если его ещё нет):

```bash
mkdir -p /home/exam_up
```

**Через Git:**

```bash
cd /home/exam_up
git clone https://github.com/nesrv/exam_ur.git .
```

Каталог `/home/exam_up` должен быть пустым (кроме скрытых служебных файлов), иначе клонируйте во временную папку и перенесите содержимое в `/home/exam_up`.

---

## 4. Виртуальное окружение и зависимости

```bash
cd /home/exam_up
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt gunicorn
```

---

## 5. Настройки Django для продакшена

В **`config/settings.py`** уже читаются переменные окружения (локально без них включён режим разработки). На VPS задайте их в unit-файле Gunicorn или в `/etc/environment`.

| Переменная | Продакшен (пример) |
|------------|-------------------|
| `DJANGO_SECRET_KEY` | Случайная строка (`openssl rand -hex 32`) |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_ALLOWED_HOSTS` | `programism.ru,www.programism.ru` (через запятую, без пробелов или с пробелами — обрежутся) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://programism.ru,https://www.programism.ru` (со схемой `https://`, иначе формы и админка за HTTPS выдадут ошибку CSRF) |
| `DJANGO_SECURE_SSL_REDIRECT` | По умолчанию `true` при `DEBUG=false`; можно `false`, если редирект HTTP→HTTPS делает только Nginx |
| `DJANGO_HSTS_SECONDS` | Опционально, например `31536000` (включит HSTS; включайте, когда уверены в HTTPS) |

База по умолчанию — SQLite (**`/home/exam_up/db.sqlite3`** — файл в корне проекта). Процесс Gunicorn должен иметь права на чтение/запись этого файла и каталога **`/home/exam_up`** (для журнала SQLite нужна запись в каталог, где лежит файл).

Миграции и статика (из **корня** репозитория, где `manage.py`):

```bash
cd /home/exam_up
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # по желанию
```

Статика собирается в **`/home/exam_up/staticfiles/`** (`STATIC_ROOT` в `config/settings.py`).

---

## 6. Gunicorn и systemd

Gunicorn слушает **только localhost** `127.0.0.1:8010` — Nginx проксирует на этот порт. Так не нужно настраивать права на Unix-сокет для пользователя `www-data`.

Файл `/etc/systemd/system/gunicorn-exam_up.service`:

```ini
[Unit]
Description=Gunicorn (exam_up Django)
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/home/exam_up
Environment="PATH=/home/exam_up/.venv/bin"
Environment="DJANGO_SECRET_KEY=ЗАМЕНИТЕ_СЛУЧАЙНЫМ_КЛЮЧОМ"
Environment="DJANGO_DEBUG=false"
Environment="DJANGO_ALLOWED_HOSTS=programism.ru,www.programism.ru"
Environment="DJANGO_CSRF_TRUSTED_ORIGINS=https://programism.ru,https://www.programism.ru"
ExecStart=/home/exam_up/.venv/bin/gunicorn \
  --workers 1 \
  --bind 127.0.0.1:8010 \
  config.wsgi:application

Restart=on-failure

[Install]
WantedBy=multi-user.target
```

`WorkingDirectory` — **корень репозитория** (где лежит `manage.py`). WSGI-модуль этого проекта — **`config.wsgi:application`**.

```bash
systemctl daemon-reload
systemctl enable gunicorn-exam_up
systemctl start gunicorn-exam_up
systemctl status gunicorn-exam_up
```

Логи: `journalctl -u gunicorn-exam_up -f`.

---

## 7. Nginx

`/etc/nginx/sites-available/programism.ru`:

```nginx
server {
    listen 80;
    server_name programism.ru www.programism.ru;

    client_max_body_size 20M;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/exam_up/staticfiles/;
    }

    # Раскомментируйте, если добавите MEDIA_ROOT в Django
    # location /media/ {
    #     alias /home/exam_up/media/;
    # }

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Включение и проверка:

```bash
ln -sf /etc/nginx/sites-available/programism.ru /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

## 8. HTTPS (Let’s Encrypt)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d programism.ru -d www.programism.ru
```

Certbot обновит конфиг Nginx на редирект и TLS. Имена в `-d` должны совпадать с `server_name` и с хостами в `DJANGO_ALLOWED_HOSTS` / `ALLOWED_HOSTS`.

---

## 9. Ручной деплой после изменений в коде

На VPS:

```bash
cd /home/exam_up
git pull   # или залить новые файлы вручную
source .venv/bin/activate && pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput
deactivate
systemctl restart gunicorn-exam_up
```

Если менялись только шаблоны/статика вне `collectstatic` — перезапуск Gunicorn всё равно не помешает.

---

## 10. Быстрая проверка

- С сервера (проверка виртуального хоста): `curl -I -H "Host: programism.ru" http://127.0.0.1/` (подставьте свой `server_name`, если домен другой).
- Снаружи: `curl -I https://programism.ru/` и при необходимости `curl -I https://www.programism.ru/`
- Админка: **https://programism.ru/admin/**
- `python manage.py check --deploy` на сервере с продакшен-настройками.

---

## Примечания

- Запуск приложения от **root** удобен для учебного VPS, но для публичного сервиса безопаснее отдельный системный пользователь и права на файлы.
- Текущий репозиторий может содержать небезопасный `SECRET_KEY` и `DEBUG = True` — для VPS это нужно исправить до выхода в интернет.
- SQLite подходит для небольшой нагрузки на одном сервере; при росте — PostgreSQL и отдельная настройка `DATABASES`.
- После обновления Python-кода без перезапуска Gunicorn воркеры продолжают отдавать старую версию приложения.
