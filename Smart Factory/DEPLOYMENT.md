# Инструкция по развертыванию Smart Factory в Production

## Системные требования

### Минимальные требования для 500 пользователей
- **CPU**: 2 vCPU (рекомендуется 4 vCPU)
- **RAM**: 8 GB (рекомендуется 16 GB)
- **Диск**: 100 GB SSD NVMe
- **ОС**: Ubuntu 22.04 LTS

### Рекомендуемые требования для высокой нагрузки
- **CPU**: 4-8 vCPU
- **RAM**: 16-32 GB
- **Диск**: 200 GB SSD NVMe + отдельный диск для БД
- **ОС**: Ubuntu 22.04 LTS

## Архитектура системы

```
Internet → Nginx → Gunicorn → Django → PostgreSQL
                    ↓
                Redis (кэш + сессии)
                    ↓
                Celery (фоновые задачи)
```

## Установка и настройка

### 1. Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y software-properties-common
```

### 2. Установка Python 3.11+
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv python3.11-dev
sudo apt install -y python3-pip
```

### 3. Установка PostgreSQL
```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Создание пользователя и БД
sudo -u postgres psql
CREATE DATABASE smart_factory;
CREATE USER smart_factory_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE smart_factory TO smart_factory_user;
ALTER USER smart_factory_user CREATEDB;
\q
```

### 4. Установка Redis
```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Настройка Redis для production
sudo nano /etc/redis/redis.conf
# Изменить:
# maxmemory 512mb
# maxmemory-policy allkeys-lru
# save ""  # Отключить сохранение на диск
```

### 5. Установка Nginx
```bash
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 6. Создание пользователя для приложения
```bash
sudo useradd -m -s /bin/bash smart_factory
sudo usermod -aG sudo smart_factory
```

## Развертывание приложения

### 1. Клонирование проекта
```bash
sudo -u smart_factory git clone <your-repo-url> /home/smart_factory/app
cd /home/smart_factory/app
```

### 2. Создание виртуального окружения
```bash
sudo -u smart_factory python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_production.txt
```

### 3. Настройка переменных окружения
```bash
sudo -u smart_factory nano /home/smart_factory/app/.env
```

Содержимое `.env`:
```env
# Database
DB_NAME=smart_factory
DB_USER=smart_factory_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Django
DJANGO_SETTINGS_MODULE=core.settings_production
SECRET_KEY=your_very_secure_secret_key_here

# Email (настройте под ваши нужды)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### 4. Настройка Django
```bash
sudo -u smart_factory python manage.py collectstatic --settings=core.settings_production
sudo -u smart_factory python manage.py migrate --settings=core.settings_production
sudo -u smart_factory python manage.py createsuperuser --settings=core.settings_production
```

### 5. Настройка Nginx
```bash
sudo cp nginx.conf /etc/nginx/sites-available/smart_factory
sudo ln -s /etc/nginx/sites-available/smart_factory /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Измените пути в конфигурации
sudo nano /etc/nginx/sites-available/smart_factory
# Замените /path/to/your/project/ на /home/smart_factory/app/

sudo nginx -t
sudo systemctl reload nginx
```

### 6. Настройка Gunicorn
```bash
sudo cp gunicorn.conf.py /home/smart_factory/app/
sudo nano /etc/systemd/system/smart_factory.service
```

Содержимое `smart_factory.service`:
```ini
[Unit]
Description=Smart Factory Gunicorn daemon
After=network.target

[Service]
User=smart_factory
Group=smart_factory
WorkingDirectory=/home/smart_factory/app
Environment="PATH=/home/smart_factory/app/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=/home/smart_factory/app/venv/bin/gunicorn --config gunicorn.conf.py core.wsgi_production:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### 7. Настройка Celery
```bash
sudo nano /etc/systemd/system/smart_factory_celery.service
```

Содержимое `smart_factory_celery.service`:
```ini
[Unit]
Description=Smart Factory Celery Worker
After=network.target

[Service]
Type=forking
User=smart_factory
Group=smart_factory
WorkingDirectory=/home/smart_factory/app
Environment="PATH=/home/smart_factory/app/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=/home/smart_factory/app/venv/bin/celery multi start worker1 -A core.celery --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO
ExecStop=/home/smart_factory/app/venv/bin/celery multi stopwait worker1 --pidfile=/var/run/celery/%n.pid
ExecReload=/home/smart_factory/app/venv/bin/celery multi restart worker1 -A core.celery --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO

[Install]
WantedBy=multi-user.target
```

```bash
sudo nano /etc/systemd/system/smart_factory_celerybeat.service
```

Содержимое `smart_factory_celerybeat.service`:
```ini
[Unit]
Description=Smart Factory Celery Beat
After=network.target

[Service]
Type=simple
User=smart_factory
Group=smart_factory
WorkingDirectory=/home/smart_factory/app
Environment="PATH=/home/smart_factory/app/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
ExecStart=/home/smart_factory/app/venv/bin/celery -A core.celery beat --loglevel=INFO
Restart=always

[Install]
WantedBy=multi-user.target
```

### 8. Создание директорий для логов
```bash
sudo mkdir -p /var/log/celery
sudo chown smart_factory:smart_factory /var/log/celery
sudo mkdir -p /var/run/celery
sudo chown smart_factory:smart_factory /var/run/celery
```

### 9. Запуск сервисов
```bash
sudo systemctl daemon-reload
sudo systemctl enable smart_factory
sudo systemctl start smart_factory
sudo systemctl enable smart_factory_celery
sudo systemctl start smart_factory_celery
sudo systemctl enable smart_factory_celerybeat
sudo systemctl start smart_factory_celerybeat
```

## Мониторинг и обслуживание

### 1. Проверка статуса сервисов
```bash
sudo systemctl status smart_factory
sudo systemctl status smart_factory_celery
sudo systemctl status smart_factory_celerybeat
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server
```

### 2. Просмотр логов
```bash
# Django/Gunicorn
sudo journalctl -u smart_factory -f

# Celery
sudo tail -f /var/log/celery/worker1.log
sudo journalctl -u smart_factory_celery -f

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### 3. Мониторинг производительности
```bash
# Системные ресурсы
htop
iotop
nethogs

# База данных
sudo -u postgres psql -d smart_factory -c "SELECT * FROM pg_stat_activity;"
sudo -u postgres psql -d smart_factory -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Redis
redis-cli info memory
redis-cli info stats
```

### 4. Резервное копирование
```bash
# Создание скрипта для бэкапа
sudo nano /home/smart_factory/backup.sh
```

Содержимое `backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/home/smart_factory/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="smart_factory"
DB_USER="smart_factory_user"

# Создание директории для бэкапов
mkdir -p $BACKUP_DIR

# Бэкап базы данных
pg_dump -h localhost -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

# Бэкап медиа файлов
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz -C /home/smart_factory/app media/

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
sudo chmod +x /home/smart_factory/backup.sh
sudo crontab -e
# Добавить строку для ежедневного бэкапа в 2:00
0 2 * * * /home/smart_factory/backup.sh
```

## Оптимизация производительности

### 1. Настройка PostgreSQL
```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Добавить/изменить:
```ini
# Memory settings
shared_buffers = 256MB          # 25% от RAM
effective_cache_size = 1GB      # 75% от RAM
work_mem = 4MB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 100
max_worker_processes = 4
max_parallel_workers_per_gather = 2

# Logging
log_statement = 'all'
log_min_duration_statement = 1000

# Performance
random_page_cost = 1.1
effective_io_concurrency = 200
```

### 2. Настройка Redis
```bash
sudo nano /etc/redis/redis.conf
```

Добавить/изменить:
```ini
# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save ""
appendonly no

# Performance
tcp-keepalive 300
timeout 0
```

### 3. Настройка Nginx
```bash
sudo nano /etc/nginx/nginx.conf
```

Добавить в http блок:
```nginx
# Gzip compression
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/atom+xml image/svg+xml;

# Client settings
client_max_body_size 10M;
client_body_timeout 30s;
client_header_timeout 30s;

# Proxy settings
proxy_connect_timeout 30s;
proxy_send_timeout 30s;
proxy_read_timeout 30s;
```

## Безопасность

### 1. Настройка файрвола
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 22
```

### 2. SSL сертификат (Let's Encrypt)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 3. Регулярные обновления
```bash
sudo apt update && sudo apt upgrade -y
sudo systemctl restart smart_factory
sudo systemctl restart nginx
sudo systemctl restart postgresql
sudo systemctl restart redis-server
```

## Troubleshooting

### 1. Проверка портов
```bash
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :5432
sudo netstat -tlnp | grep :6379
```

### 2. Проверка прав доступа
```bash
sudo chown -R smart_factory:smart_factory /home/smart_factory/app
sudo chmod -R 755 /home/smart_factory/app
sudo chmod 644 /home/smart_factory/app/.env
```

### 3. Перезапуск сервисов
```bash
sudo systemctl restart smart_factory
sudo systemctl restart smart_factory_celery
sudo systemctl restart smart_factory_celerybeat
sudo systemctl restart nginx
sudo systemctl restart postgresql
sudo systemctl restart redis-server
```

## Масштабирование

### 1. Горизонтальное масштабирование
- Добавление дополнительных серверов приложений
- Настройка балансировщика нагрузки
- Репликация базы данных

### 2. Вертикальное масштабирование
- Увеличение ресурсов сервера
- Оптимизация кода и запросов
- Настройка кэширования

### 3. Мониторинг нагрузки
- Использование Prometheus + Grafana
- Настройка алертов
- Анализ производительности

## Заключение

Данная конфигурация обеспечивает:
- Высокую производительность при нагрузке до 500+ пользователей
- Стабильную работу системы
- Автоматическое резервное копирование
- Мониторинг и логирование
- Возможность масштабирования

Для дальнейшей оптимизации рекомендуется:
- Анализ медленных запросов
- Настройка индексов базы данных
- Оптимизация шаблонов и JavaScript
- Использование CDN для статических файлов 