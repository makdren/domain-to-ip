import socket
import os
import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse


RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BLUE = "\033[94m"

# ====================== КОНСТАНТЫ ======================
SCRIPT_DIR = Path(__file__).parent.absolute()
DOMAINS_FILE = SCRIPT_DIR / "domains.txt"
IPS_FILE = SCRIPT_DIR / "ips.txt"
DOMAIN_IP_FILE = SCRIPT_DIR / "domain_ip.txt"

DEFAULT_MAX_WORKERS = 50
DEFAULT_TIMEOUT = 8


def print_banner() -> None:
    """Выводит красивый баннер при запуске"""
    banner = f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗
                           {GREEN}dom2ip{RESET}{BOLD}{CYAN}                                 
           Массовое разрешение доменов в IP-адреса                
╚══════════════════════════════════════════════════════════╝{RESET}
"""
    print(banner)


def normalize_domain(raw_domain: str) -> Optional[str]:
    """
    Приводит входную строку к доменному имени:
    - поддерживает URL (https://example.com/path)
    - убирает порт (:443), путь, query/fragment
    - поддерживает IDN через punycode
    Возвращает None, если домен невалидный.
    """
    value = raw_domain.strip()
    if not value:
        return None

    # Если строка похожа на URL — парсим корректно.
    if "://" in value:
        parsed = urlparse(value)
        value = parsed.hostname or ""
    else:
        # На случай записей вида "example.com/path" или "example.com:443"
        value = value.split("/")[0].split("?")[0].split("#")[0]
        if ":" in value:
            value = value.split(":", 1)[0]

    value = value.strip().strip(".").lower()
    if not value:
        return None

    # Удаляем недопустимые символы, которые могут попасть из текста/CSV.
    value = value.strip("\"'`()[]{}<>")
    if not value:
        return None

    try:
        # Нормализуем IDN в ascii-представление.
        ascii_domain = value.encode("idna").decode("ascii")
    except Exception:
        return None

    # Базовая проверка формата доменного имени.
    if "." not in ascii_domain:
        return None

    labels = ascii_domain.split(".")
    for label in labels:
        if not label or len(label) > 63:
            return None
        if label.startswith("-") or label.endswith("-"):
            return None

    if len(ascii_domain) > 253:
        return None

    return ascii_domain


def load_domains(file_path: Path) -> Tuple[List[str], List[str]]:
    """Загружает и нормализует домены из файла."""
    if not file_path.exists():
        print(f"{RED}❌ Файл {file_path.name} не найден!{RESET}")
        print(f"   Создайте {file_path.name} и добавьте домены.")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    raw_domains = [d.strip() for d in content.replace(",", " ").split() if d.strip()]
    normalized_domains: List[str] = []
    skipped_raw: List[str] = []

    for raw_domain in raw_domains:
        normalized = normalize_domain(raw_domain)
        if normalized:
            normalized_domains.append(normalized)
        else:
            skipped_raw.append(raw_domain)

    # Удаляем дубликаты, сохраняя порядок появления
    domains = list(dict.fromkeys(normalized_domains))

    if not domains:
        print(f"{RED}❌ В файле {file_path.name} нет доменов.{RESET}")
        sys.exit(1)

    return domains, skipped_raw


def resolve_domain(domain: str, retries: int = 1, retry_delay: float = 0.25) -> Tuple[str, Optional[str], Optional[str]]:
    last_error = None
    attempts = max(retries, 1)
    for attempt in range(1, attempts + 1):
        try:
            ip = socket.gethostbyname(domain)
            return domain, ip, None
        except Exception as e:
            last_error = str(e)
            if attempt < attempts:
                time.sleep(retry_delay)

    return domain, None, last_error


def delete_old_files() -> None:
    print(f"{YELLOW}🗑️  Удаляем старые списки IP...{RESET}")
    for filepath in (IPS_FILE, DOMAIN_IP_FILE):
        if filepath.exists():
            try:
                filepath.unlink()
                print(f"{GREEN}   ✅ Удалён: {filepath.name}{RESET}")
            except Exception as e:
                print(f"{YELLOW}   ⚠️  Не удалось удалить {filepath.name}: {e}{RESET}")


def write_results(domains: List[str], resolved: Dict[str, str]) -> int:
    success_count = 0

    # ips.txt — только IP
    with open(IPS_FILE, "w", encoding="utf-8") as f:
        for domain in domains:
            if domain in resolved:
                f.write(f"{resolved[domain]}\n")
                success_count += 1

    # domain_ip.txt — домен → IP
    with open(DOMAIN_IP_FILE, "w", encoding="utf-8") as f:
        for domain in domains:
            if domain in resolved:
                f.write(f"{domain} → {resolved[domain]}\n")

    return success_count


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="dom2ip — быстрый резолвер доменов в IP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Количество потоков (по умолчанию: {DEFAULT_MAX_WORKERS})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Таймаут DNS-запроса в секундах (по умолчанию: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--domains",
        type=Path,
        default=DOMAINS_FILE,
        help="Путь к файлу с доменами (по умолчанию: domains.txt)"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Количество попыток DNS-резолва для каждого домена (по умолчанию: 2)"
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=0.25,
        help="Пауза между повторными попытками в секундах (по умолчанию: 0.25)"
    )
    return parser.parse_args()


def main() -> None:
    start_time = time.time()
    print_banner()

    args = parse_arguments()

    # Устанавливаем таймаут
    socket.setdefaulttimeout(args.timeout)

    domains, skipped_raw = load_domains(args.domains)

    print(f"{GREEN}✅ Найдено {len(domains)} уникальных доменов.{RESET}")
    if skipped_raw:
        print(f"{YELLOW}⚠️  Пропущено невалидных записей: {len(skipped_raw)}{RESET}")
    print(f"{BLUE}   Запускаем параллельное разрешение ({args.threads} потоков)...{RESET}\n")

    resolved: Dict[str, str] = {}
    failed: List[Tuple[str, str]] = []
    completed = 0
    total = len(domains)

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        future_to_domain = {
            executor.submit(resolve_domain, d, args.retries, args.retry_delay): d
            for d in domains
        }

        for future in as_completed(future_to_domain):
            domain, ip, error = future.result()

            if ip:
                resolved[domain] = ip
            else:
                failed.append((domain, error))

            completed += 1
            progress = int(completed / total * 100)
            print(
                f"\r{GREEN}Прогресс: [{progress:3d}%] {completed}/{total} доменов{RESET}",
                end="",
                flush=True,
            )

    print("\n")  # новая строка после прогресс-бара

    # Выводим ошибки (если есть)
    if failed:
        print(f"{YELLOW}⚠️  Не удалось обработать {len(failed)} доменов:{RESET}")
        for d, err in failed:
            print(f"   • {d} → {RED}{err}{RESET}")
    if skipped_raw:
        print(f"{YELLOW}⚠️  Пропущенные записи (невалидный формат):{RESET}")
        for raw in skipped_raw:
            print(f"   • {raw}")

    # Удаляем старые файлы и создаём новые
    delete_old_files()
    success_count = write_results(domains, resolved)

    # Итоговое время
    elapsed = time.time() - start_time

    # Финальное сообщение
    print(f"\n{BOLD}{GREEN}🎉 ГОТОВО!{RESET}")
    print(f"   Успешно обработано: {GREEN}{success_count}/{len(domains)}{RESET} доменов")
    print(f"   Время выполнения: {YELLOW}{elapsed:.2f} сек{RESET}")
    print()
    print(f"   📄 Только IP          → {IPS_FILE}")
    print(f"   📄 Домен → IP         → {DOMAIN_IP_FILE}")
    print(f"\n{BOLD}{CYAN}Спасибо за использование dom2ip!{RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠️  Выполнение прервано пользователем.{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}❌ Критическая ошибка: {e}{RESET}")
        sys.exit(1)
