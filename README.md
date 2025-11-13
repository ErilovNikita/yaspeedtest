# yaspeedtest
YaSpeedTest — это **асинхронный клиент Python**, который точно измеряет скорость интернета, используя те же общедоступные конечные точки, что и официальный [Yandex Internet Speed ​​Test](https://yandex.ru/internet).

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI Version](https://img.shields.io/pypi/pyversions/yaspeedtest?logo=python&label=Python)](https://pypi.org/project/yaspeedtest)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/yaspeedtest?logo=pypi&label=PyPI%20-%20Downloads)](https://pypi.org/project/yaspeedtest)

![preview](docs/preview.png)

> [!WARNING]  
> Данная библиотека НЕ является официальной, и не пытается ей казаться. Данная библиотека разрабатывается исключительно в личных интересах, и использует только общедоступные endpoint'ы.

## Возможности
- Асинхронная архитектура (`asyncio`, `aiohttp`)
- Поддержка пикового измерения скорости (реальные пиковые Mbps, как в браузере)
- Умное использование проб (probes) с серверов Яндекса
- Полная типизация (через `pydantic`)
- Поддержка измерений **Download**, **Upload**, **Latency**
- Совместимость с Python 3.11+
- Возможность интеграции в любые системы мониторинга или DevOps пайплайны

## Установка
Установите библиотеку с помощью pip:

```bash
pip install yaspeedtest
```

Или скачайте последнюю версию из репозитория:

```bash
git clone https://github.com/ErilovNikita/yaspeedtest
cd yaspeedtest
```

## Пример использования
```python
import asyncio
from yaspeedtest.client import YaSpeedTest

async def main():
    ya = await YaSpeedTest.create()
    result = await ya.run()

    print(f"Ping: {result.ping_ms:.2f} ms")
    print(f"Download: {result.download_mbps:.2f} Mbps")
    print(f"Upload: {result.upload_mbps:.2f} Mbps")

asyncio.run(main())

# Ping: 1.84 ms
# Download: 939.17 Mbps
# Upload: 870.29 Mbps
```

Больше примеров в папке [examples](/examples)

## Режим пикового измерения скорости
Методы `measure_download_peak()` и `measure_upload_peak()` фиксируют пиковую скорость передачи данных за секунду, а не усреднённое значение по всему файлу.

Это позволяет получить результаты, максимально близкие к официальному тесту Яндекса, где скорость отображается на основе коротких всплесков трафика.

## Как это работает
1. Клиент делает запрос к Яндекс
1. Сервер возвращает набор доступных probe-серверов (latency, download, upload)
1. Для каждого типа выполняются асинхронные измерения:
   - Latency — последовательные пинги к малым ресурсам (latency probes)
   - Download — скачивание файлов
   - Upload — отправка данных
1. Результаты агрегируются в объект SpeedResult, содержащий:
   - Минимальный пинг
   - Пиковую скорость загрузки
   - Пиковую скорость отдачи

## Струкрура
### Класс YaSpeedTest
| Метод | Описание |
|-------|-------|
| `run()` | Основной метод запуска теста скорости |
| `measure_latency(url: str, timeout: int)` | *Измеряет пинг в миллисекундах* |
| `measure_download(url: str, timeout: int)` | *Классическое измерение скорости загрузки* |
| `measure_download_peak(url: str, timeout: int)` | *Измеряет пиковую скорость загрузки* |
| `measure_upload(url: str, size: int, timeout: int)` | *Классическое измерение скорости отдачи* |
| `measure_upload_peak(url: str, size: int, timeout: int)` | *Измеряет пиковую скорость отдачи* |

### Класс SpeedResult
| Поле | Тип | Описание |
|-------|----|-----|
| **ping_ms** | float | *Средний пинг в миллисекундах* |
| **download_mbps** | float | *Скорость загрузки в мегабитах в секунду* |
| **upload_mbps** | float | *Скорость отдачи в мегабитах в секунду* |

Пример результата SpeedResult:
```python
SpeedResult(
    ping_ms=1.37,
    download_mbps=950.42,
    upload_mbps=870.10
)
```

## Советы по производительности
- Избегайте слишком большого числа одновременных проб — оптимально 3–5 в каждой категории.
- Устанавливайте timeout не менее 30 секунд для стабильных замеров.
- Используйте aiohttp.TCPConnector(limit_per_host=2) для балансировки нагрузки.
- На системах с нестабильным NAT возможно повышение пинга из-за соединений TLS.