#!/bin/bash
set -euo pipefail

# ====================== ЦВЕТА И ЛОГИРОВАНИЕ ======================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' 

print_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                      🚀 УСТАНОВКА dom2ip                             ║"
    echo "║                    Domain → IP Resolver                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log()    { echo -e "${GREEN}[✓]${NC} $1"; }
info()   { echo -e "${BLUE}[i]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
error()  { echo -e "${RED}[✗]${NC} $1" >&2; }

# ====================== СТАРТ ======================
print_header
info "Запуск установки dom2ip..."

# 1. Создаём и переходим в папку
info "1. Создание рабочей директории..."
mkdir -p dom2ip
cd dom2ip || { error "Не удалось зайти в папку dom2ip"; exit 1; }
log "Директория готова → $(pwd)"

# 2. Скачиваем файлы (с проверкой)
info "2. Скачивание актуальных файлов с GitHub..."

curl -sSL -o dom2ip.py \
    https://raw.githubusercontent.com/makdren/domain-to-ip/main/dom2ip.py || \
    { error "Не удалось скачать dom2ip.py"; exit 1; }
log "✅ dom2ip.py успешно скачан"

curl -sSL -o domains.txt \
    https://raw.githubusercontent.com/makdren/domain-to-ip/main/domains.txt || \
    { error "Не удалось скачать domains.txt"; exit 1; }
log "✅ domains.txt успешно скачан"

# 3. Проверка и установка Python 3
info "3. Проверка Python 3..."

if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    log "Python 3 уже установлен (${PYTHON_VERSION})"
else
    warn "Python 3 не найден. Выполняем установку..."

    if [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
        # Debian / Ubuntu / Mint / Pop!_OS и т.д.
        sudo apt-get update -qq && sudo apt-get install -y python3
        log "Python 3 установлен (Debian/Ubuntu)"

    elif [ -f /etc/redhat-release ] || [ -f /etc/fedora-release ]; then
        # Fedora / RHEL / CentOS / Rocky / Alma
        if command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y python3
        else
            sudo yum install -y python3
        fi
        log "Python 3 установлен (RedHat/Fedora)"

    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        info "🍎 Обнаружена macOS"
        if command -v brew >/dev/null 2>&1; then
            brew install python3
            log "Python 3 установлен через Homebrew"
        else
            error "Homebrew не установлен!"
            echo -e "   Установите его: ${CYAN}https://brew.sh/${NC}"
            exit 1
        fi

    else
        error "Неизвестная операционная система."
        echo "   Установите Python 3 вручную и запустите скрипт снова."
        exit 1
    fi
fi

# ====================== ФИНАЛЬНЫЙ БЛОК ======================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     🎉 УСТАНОВКА УСПЕШНО ЗАВЕРШЕНА!                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "📌 ${CYAN}Чтобы запустить резолвер:${NC}"
echo -e "   ${GREEN}cd dom2ip${NC}"
echo -e "   ${GREEN}python3 dom2ip.py${NC}"
echo ""

info "Не забудьте добавить свои домены в файл domains.txt"
