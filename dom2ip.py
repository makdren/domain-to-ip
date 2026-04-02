import socket
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# Пути к файлам
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOMAINS_FILE = os.path.join(SCRIPT_DIR, 'domains.txt')
IPS_FILE = os.path.join(SCRIPT_DIR, 'ips.txt')
DOMAIN_IP_FILE = os.path.join(SCRIPT_DIR, 'domain_ip.txt')


def resolve_domain(domain):
    """Разрешаем домен в IP с обработкой ошибок"""
    try:
        ip = socket.gethostbyname(domain)
        return domain, ip, None
    except Exception as e:
        return domain, None, str(e)


def main():
    # Устанавливаем таймаут
    socket.setdefaulttimeout(8)

    if not os.path.exists(DOMAINS_FILE):
        print(f"❌ Файл {DOMAINS_FILE} не найден!")
        print("Создайте его и добавьте домены (поддерживаются разные форматы).")
        sys.exit(1)

    # Читаем домены (поддержка всех форматов)
    with open(DOMAINS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    domains = [d.strip() for d in content.replace(',', ' ').split() if d.strip()]

    if not domains:
        print("❌ В файле domains.txt нет доменов.")
        sys.exit(1)

    print(f"✅ Найдено {len(domains)} доменов. Запускаем обработку...")

    # Параллельное разрешение
    resolved_dict = {}
    failed = []
    completed = 0
    total = len(domains)

    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_domain = {executor.submit(resolve_domain, d): d for d in domains}
        for future in as_completed(future_to_domain):
            domain, ip, error = future.result()
            if ip:
                resolved_dict[domain] = ip
            else:
                failed.append((domain, error))
            completed += 1

            progress = int(completed / total * 100)
            print(f"\rПрогресс: [{progress:3d}%] {completed}/{total} доменов обработано", end='', flush=True)

    print()  # новая строка после прогресс-бара

    # Выводим ошибки
    if failed:
        print(f"\n⚠️  Не удалось обработать {len(failed)} доменов:")
        for d, err in failed:
            print(f"   • {d} → {err}")

    success_count = len(resolved_dict)

    # === НОВОЕ: Явное удаление старых файлов ===
    print("\n🗑️  Удаляем старые списки IP (если существуют)...")
    for filepath in [IPS_FILE, DOMAIN_IP_FILE]:
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                print(f"   ✅ Удалён: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"   ⚠️  Не удалось удалить {os.path.basename(filepath)}: {e}")

    # Создаём полностью новые файлы
    with open(IPS_FILE, 'w', encoding='utf-8') as f:
        for domain in domains:
            if domain in resolved_dict:
                f.write(resolved_dict[domain] + '\n')

    with open(DOMAIN_IP_FILE, 'w', encoding='utf-8') as f:
        for domain in domains:
            if domain in resolved_dict:
                f.write(f"{domain}   {resolved_dict[domain]}\n")

    print(f"\n🎉 Готово! Успешно обработано {success_count} из {len(domains)} доменов.")
    print(f"   • Только IP → {IPS_FILE}  (создан заново)")
    print(f"   • Домен + IP → {DOMAIN_IP_FILE}  (создан заново)")


if __name__ == "__main__":
    main()
