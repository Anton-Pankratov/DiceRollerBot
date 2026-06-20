# Инструкция по деплою DiceRollerBot на сервер (VPS)

В данном руководстве описано, как настроить сервер для работы Telegram Mini App (Web App) с поддержкой безопасного соединения HTTPS (требование Telegram).

---

## Вариант 1. Запуск через Docker Compose (Рекомендуемый)

Это самый простой и быстрый способ развернуть бота и веб-приложение на сервере.

### 1. Установите Docker и Docker Compose
Если на сервере еще нет Docker, установите его (для Ubuntu/Debian):
```bash
sudo apt update
sudo apt install docker.io docker-compose -y
```

### 2. Подготовьте конфигурацию `.env`
Создайте `.env` файл на сервере со следующими параметрами:
```env
BOT_MODE=prod
BOT_TOKEN=8975175639:AAHT-gU2mLeE8MQ5MdRZfBIpU__JVZAagJY
THROTTLING_RATE=1.0
DB_SALT=super_secret_dnd_salt_value_123456

# Настройки для сервера
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8000
WEBAPP_URL=https://yourdomain.com # Укажите ваш домен с HTTPS
```

### 3. Запустите контейнеры
Перейдите в папку проекта и выполните команду:
```bash
sudo docker-compose up --build -d
```
Бот и Mini App запустятся в фоновом режиме. Порт `8000` будет проброшен наружу на хост-машину.

---

## Вариант 2. Запуск без Docker (через systemd)

### 1. Установка зависимостей и окружения
```bash
sudo apt update
sudo apt install python3-pip python3-venv git -y

# Создание виртуального окружения
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Настройка systemd службы
Создайте файл службы, чтобы бот автоматически запускался после перезагрузки сервера:
```bash
sudo nano /etc/systemd/system/dice_bot.service
```

Вставьте следующее содержимое (замените `/path/to/project` на реальный путь к проекту):
```ini
[Unit]
Description=DiceRollerBot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/project
ExecStart=/path/to/project/.venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Запустите и активируйте автозапуск:
```bash
sudo systemctl daemon-reload
sudo systemctl start dice_bot
sudo systemctl enable dice_bot
```

---

## Настройка Nginx и SSL (HTTPS) для обоих вариантов

Чтобы Telegram Mini App открывался внутри клиента Telegram, обязательно нужен HTTPS. Настроим проксирование через Nginx с бесплатным сертификатом Let's Encrypt.

### 1. Установка Nginx и Certbot
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

### 2. Настройка конфигурации Nginx
Создайте новый конфигурационный файл:
```bash
sudo nano /etc/nginx/sites-available/dice_bot
```

Вставьте конфигурацию (замените `yourdomain.com` на ваш домен/поддомен):
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте сайт и перезапустите Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/dice_bot /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### 3. Получение SSL-сертификата
Запустите выпуск сертификата от Let's Encrypt:
```bash
sudo certbot --nginx -d yourdomain.com
```
*Certbot автоматически изменит файл конфигурации Nginx, настроит перенаправление с HTTP на HTTPS и установит сертификат.*

---

## Проверка работы

После настройки:
1. Перейдите по адресу `https://yourdomain.com` в браузере — вы должны увидеть интерфейс листа персонажа.
2. В Telegram напишите боту `/webapp` или нажмите кнопку меню «🎲 Лист героя» — Mini App должен открыться внутри мессенджера.
