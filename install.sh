#!/bin/bash

# ===============================================
# Автоматическая установка Domain to IP
# ===============================================

echo "🚀 Запуск установки dom2ip..."

# 1. Создаём папку
mkdir -p dom2ip
cd dom2ip || { echo "❌ Не удалось зайти в папку dom2ip"; exit 1; }

# 2. Скачиваем файлы с GitHub (raw-версии!)
echo "📥 Скачиваем dom2ip.py и domains.txt..."
curl -sSL -o dom2ip.py https://raw.githubusercontent.com/makdren/domain-to-ip/main/dom2ip.py
curl -sSL -o domains.txt https://raw.githubusercontent.com/makdren/domain-to-ip/main/domains.txt

# 3. Проверяем и устанавливаем Python3
if command -v python3 >/dev/null 2>&1; then
    echo "✅ Python3 уже установлен"
else
    echo "🐍 Python3 не найден. Устанавливаем..."
    
    if [ -f /etc/debian_version ] || [ -f /etc/lsb-release ]; then
        # Debian / Ubuntu / Mint
        sudo apt update -qq && sudo apt install -y python3
    elif [ -f /etc/redhat-release ] || [ -f /etc/fedora-release ]; then
        # Fedora / RHEL / CentOS
        if command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y python3
        else
            sudo yum install -y python3
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "🍎 macOS обнаружен."
        if command -v brew >/dev/null 2>&1; then
            brew install python3
        else
            echo "❌ Homebrew не установлен. Установите его вручную или Python3 с официального сайта."
            echo "    https://www.python.org/downloads/"
            exit 1
        fi
    else
        echo "❌ Неизвестная ОС. Установите Python3 вручную."
        exit 1
    fi
fi

# 4. Финальное сообщение
echo ""
echo "🎉 Установка успешно завершена!"
echo ""
echo "Чтобы запустить резолвер доменов:"
echo ""
echo "   cd dom2ip"
echo "   python3 dom2ip.py"
echo "Не забудьте добавить домены в domains.txt"
echo ""
echo "Готово! Можете сразу выполнить эти две команды."
echo "═══════════════════════════════════════════════"
