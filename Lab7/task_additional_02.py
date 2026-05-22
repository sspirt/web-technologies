import json
import logging
import time
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from statistics import mean, median
from typing import Optional
import requests
import argparse

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(message)s",
                    handlers=[logging.StreamHandler()])
log = logging.getLogger(__name__)

TIMEOUT = 15
HEADERS = {"User-Agent": "CurrencyAggregator/1.0"}

@dataclass
class RateResult:
    source: str
    base: str
    target: str
    rate: Optional[float] = None
    error: Optional[str] = None

class CurrencySource(ABC):
    name: str = "Unknown"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, base: str, target: str) -> RateResult:
        try:
            return self._fetch(base.upper(), target.upper())
        except requests.exceptions.Timeout:
            return RateResult(self.name, base, target, error="Таймаут")
        except requests.exceptions.ConnectionError:
            return RateResult(self.name, base, target, error="Ошибка соединения")
        except requests.exceptions.HTTPError as e:
            return RateResult(self.name, base, target, error=f"HTTP {e.response.status_code}")
        except (KeyError, IndexError, ValueError, json.JSONDecodeError, ET.ParseError) as e:
            return RateResult(self.name, base, target, error=f"Ошибка разбора: {e}")
        except Exception as e:
            return RateResult(self.name, base, target, error=str(e))

    @abstractmethod
    def _fetch(self, base: str, target: str) -> RateResult: ...

    def _get_json(self, url: str, **kwargs) -> dict:
        r = self.session.get(url, timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r.json()

class FrankfurterSource(CurrencySource):
    name = "Frankfurter (ECB)"

    def _fetch(self, base, target):
        data = self._get_json("https://api.frankfurter.app/latest",
                              params={"from": base, "to": target})
        return RateResult(self.name, base, target, rate=data["rates"][target])

class JsdelivrCurrencySource(CurrencySource):
    name = "jsDelivr Currency"

    def _fetch(self, base, target):
        b, t = base.lower(), target.lower()
        data = self._get_json(f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{b}.json")
        return RateResult(self.name, base, target, rate=data[b][t])

class CBRFSource(CurrencySource):
    name = "ЦБ РФ"

    def _fetch(self, base, target):
        resp = self.session.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = "windows-1251"
        root = ET.fromstring(resp.text)

        def to_rub(cur: str) -> float:
            if cur == "RUB": return 1.0
            for v in root.findall("Valute"):
                if v.find("CharCode").text.strip() == cur:
                    return float(v.find("Value").text.replace(",", ".")) / int(v.find("Nominal").text)
            raise ValueError(f"{cur} не найдена в ЦБ РФ")

        if target == "RUB":
            rate = to_rub(base)
        elif base == "RUB":
            rate = 1.0 / to_rub(target)
        else:
            rate = to_rub(base) / to_rub(target)
        return RateResult(self.name, base, target, rate=rate)

class NBUSource(CurrencySource):
    name = "НБУ"

    def _fetch(self, base, target):
        data = self._get_json("https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json")

        def to_uah(cur: str) -> float:
            if cur == "UAH": return 1.0
            for item in data:
                if item["cc"] == cur:
                    return item["rate"]
            raise ValueError(f"{cur} не найдена в НБУ")

        if target == "UAH":
            rate = to_uah(base)
        elif base == "UAH":
            rate = 1.0 / to_uah(target)
        else:
            rate = to_uah(base) / to_uah(target)
        return RateResult(self.name, base, target, rate=rate)

class NBPSource(CurrencySource):
    name = "НБП (Польша)"

    def _fetch(self, base: str, target: str) -> RateResult:
        def to_pln(currency: str) -> float:
            if currency == "PLN":
                return 1.0
            resp = self.session.get(
                f"https://api.nbp.pl/api/exchangerates/rates/A/{currency}/",  # https!
                params={"format": "json"},
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()["rates"][0]["mid"]

        if target == "PLN":
            rate = to_pln(base)
        elif base == "PLN":
            rate = 1.0 / to_pln(target)
        else:
            rate = to_pln(base) / to_pln(target)
        return RateResult(self.name, base, target, rate=rate)

class ExchangeRateAPISource(CurrencySource):
    name = "ExchangeRate-API"

    def _fetch(self, base, target):
        if not self.api_key:
            return RateResult(self.name, base, target, error="Нет API-ключа")
        data = self._get_json(f"https://v6.exchangerate-api.com/v6/{self.api_key}/pair/{base}/{target}")
        return RateResult(self.name, base, target, rate=data["conversion_rate"])

class OpenExchangeRatesSource(CurrencySource):
    name = "OpenExchangeRates"

    def _fetch(self, base, target):
        if not self.api_key:
            return RateResult(self.name, base, target, error="Нет API-ключа")
        data = self._get_json("https://openexchangerates.org/api/latest.json",
                              params={"app_id": self.api_key, "symbols": f"{base},{target}"})
        rates = data["rates"]
        usd_base = rates.get(base, 1.0) if base != "USD" else 1.0
        usd_target = rates.get(target, 1.0) if target != "USD" else 1.0
        return RateResult(self.name, base, target, rate=usd_target / usd_base)

class FixerSource(CurrencySource):
    name = "Fixer.io"

    def _fetch(self, base, target):
        if not self.api_key:
            return RateResult(self.name, base, target, error="Нет API-ключа")
        data = self._get_json("http://data.fixer.io/api/latest",
                              params={"access_key": self.api_key, "base": "EUR",
                                      "symbols": f"{base},{target}"})
        rates = data["rates"]
        eur_base = rates.get(base, 1.0) if base != "EUR" else 1.0
        eur_target = rates.get(target, 1.0) if target != "EUR" else 1.0
        return RateResult(self.name, base, target, rate=eur_target / eur_base)

class CurrencyAPISource(CurrencySource):
    name = "CurrencyAPI.com"

    def _fetch(self, base, target):
        if not self.api_key:
            return RateResult(self.name, base, target, error="Нет API-ключа")
        data = self._get_json("https://api.currencyapi.com/v3/latest",
                              params={"apikey": self.api_key,
                                      "base_currency": base, "currencies": target})
        return RateResult(self.name, base, target, rate=data["data"][target]["value"])

class ExchangeRatesAPIIoSource(CurrencySource):
    name = "ExchangeRatesAPI.io"

    def _fetch(self, base, target):
        if not self.api_key:
            return RateResult(self.name, base, target, error="Нет API-ключа")
        data = self._get_json("https://api.exchangeratesapi.io/v1/latest",
                              params={"access_key": self.api_key,
                                      "base": base, "symbols": target})
        return RateResult(self.name, base, target, rate=data["rates"][target])

class CurrencyAggregator:
    def __init__(self, er_key="", oxr_key="", fixer_key="", capi_key="", erapi_key=""):
        self.sources: list[CurrencySource] = [
            FrankfurterSource(),
            JsdelivrCurrencySource(),
            CBRFSource(),
            NBUSource(),
            NBPSource(),
            ExchangeRateAPISource(api_key=er_key),
            OpenExchangeRatesSource(api_key=oxr_key),
            FixerSource(api_key=fixer_key),
            CurrencyAPISource(api_key=capi_key),
            ExchangeRatesAPIIoSource(api_key=erapi_key),
        ]

    def analyze(self, base: str, target: str) -> None:
        print(f"\nЗапрашиваю курс {base} → {target} у {len(self.sources)} источников...\n")
        results = []
        for src in self.sources:
            log.info("Запрос к %s...", src.name)
            results.append(src.fetch(base, target))
            time.sleep(0.2)
        self._report(results, base, target)

    def _report(self, results: list[RateResult], base: str, target: str) -> None:
        valid = sorted([r for r in results if r.rate is not None],
                       key=lambda r: r.rate, reverse=True)
        failed = [r for r in results if r.error]
        print(f"\nКурс {base} → {target}")
        print(f"{'#':<3} {'Источник':<25} {'Курс':>12}  Статус")
        for i, r in enumerate(valid, 1):
            mark = " Лучший" if i == 1 else ""
            print(f"{i:<3} {r.source:<25} {r.rate:>12.6f}  {mark}")
        for r in failed:
            print(f"{'—':<3} {r.source:<25} {'—':>12}  {r.error}")
        if valid:
            rates = [r.rate for r in valid]
            best, worst = valid[0], valid[-1]
            spread = (best.rate - worst.rate) / worst.rate * 100
            print(f"\nСтатистика ({len(valid)} источников):")
            print(f"   Лучший курс  : {best.rate:.6f}  ({best.source})")
            print(f"   Худший курс  : {worst.rate:.6f}  ({worst.source})")
            print(f"   Средний курс : {mean(rates):.6f}")
            print(f"   Медиана      : {median(rates):.6f}")
            print(f"   Разброс      : {spread:.2f}%")
            print(f"\nНаиболее выгодный: 1 {base} = {best.rate:.6f} {target} ({best.source})")
        else:
            print("\n  Нет данных ни от одного источника.")

def main():
    parser = argparse.ArgumentParser(description="Агрегатор курсов валют")
    parser.add_argument("base", help="Базовая валюта, напр. USD")
    parser.add_argument("target", help="Целевая валюта, напр. EUR")
    parser.add_argument("--er-key", default="", help="ExchangeRate-API key")
    parser.add_argument("--oxr-key", default="", help="OpenExchangeRates key")
    parser.add_argument("--fixer-key", default="", help="Fixer.io key")
    parser.add_argument("--capi-key", default="", help="CurrencyAPI.com key")
    parser.add_argument("--erapi-key", default="", help="ExchangeRatesAPI.io key")
    args = parser.parse_args()
    CurrencyAggregator(args.er_key, args.oxr_key, args.fixer_key,
                       args.capi_key, args.erapi_key).analyze(args.base, args.target)

if __name__ == "__main__":
    main()