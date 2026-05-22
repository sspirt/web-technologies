import json
import logging
import sys
import time
import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, stdev
from typing import Optional
import requests
from geopy.geocoders import Nominatim

HAS_GEOPY = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

TIMEOUT = 15
TOMORROW = date.today() + timedelta(days=1)

@dataclass
class WeatherResult:
    source: str
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    description: str = ""
    error: Optional[str] = None

    @property
    def temp_avg(self) -> Optional[float]:
        if self.temp_min is not None and self.temp_max is not None:
            return (self.temp_min + self.temp_max) / 2
        return self.temp_min or self.temp_max


class WeatherSource(ABC):
    name: str = "Unknown"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WeatherAggregator/1.0"})

    def fetch(self, city: str, lat: float, lon: float) -> WeatherResult:
        try:
            return self._fetch(city, lat, lon)
        except requests.exceptions.Timeout:
            return WeatherResult(source=self.name, error="Таймаут")
        except requests.exceptions.ConnectionError:
            return WeatherResult(source=self.name, error="Ошибка соединения")
        except requests.exceptions.HTTPError as exc:
            return WeatherResult(source=self.name, error=f"HTTP {exc.response.status_code}")
        except (KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
            return WeatherResult(source=self.name, error=f"Ошибка разбора: {exc}")
        except Exception as exc:
            log.error("Неожиданная ошибка %s: %s", self.name, exc)
            return WeatherResult(source=self.name, error=str(exc))

    @abstractmethod
    def _fetch(self, city: str, lat: float, lon: float) -> WeatherResult: ...

class OpenMeteoSource(WeatherSource):
    name = "Open-Meteo"

    def _fetch(self, city, lat, lon):
        resp = self.session.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min",
                "timezone": "auto", "forecast_days": 2,
            },
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        d = resp.json()["daily"]
        return WeatherResult(self.name, temp_min=d["temperature_2m_min"][1],
                             temp_max=d["temperature_2m_max"][1])

class WttrInSource(WeatherSource):
    name = "wttr.in"

    def _fetch(self, city, lat, lon):
        resp = self.session.get(f"https://wttr.in/{lat},{lon}",
                                params={"format": "j1"}, timeout=TIMEOUT)
        resp.raise_for_status()
        w = resp.json()["weather"][1]
        return WeatherResult(
            self.name,
            temp_min=float(w["mintempC"]),
            temp_max=float(w["maxtempC"]),
            description=w["hourly"][4]["weatherDesc"][0]["value"]
        )

class Timer7Source(WeatherSource):
    name = "7Timer"

    def _fetch(self, city, lat, lon):
        resp = self.session.get(
            "http://www.7timer.info/bin/api.pl",
            params={"lon": lon, "lat": lat, "product": "civil", "output": "json"},
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        series = resp.json()["dataseries"]
        pts = [p for p in series if 8 <= p["timepoint"] <= 24] or series[:8]
        temps = [p["temp2m"] for p in pts]
        return WeatherResult(self.name, temp_min=min(temps), temp_max=max(temps))

class OpenWeatherMapSource(WeatherSource):
    name = "OpenWeatherMap"

    def _fetch(self, city, lat, lon):
        if not self.api_key:
            return WeatherResult(self.name, error="API-ключ не задан")
        resp = self.session.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"lat": lat, "lon": lon, "units": "metric", "appid": self.api_key},
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        target = TOMORROW.strftime("%Y-%m-%d")
        entries = [e for e in resp.json()["list"] if e["dt_txt"].startswith(target)]
        if not entries:
            return WeatherResult(self.name, error="Нет данных на завтра")
        temps = [e["main"]["temp"] for e in entries]
        desc = entries[len(entries) // 2]["weather"][0]["description"]
        return WeatherResult(self.name, temp_min=min(temps), temp_max=max(temps), description=desc)

class WeatherAPISource(WeatherSource):
    name = "WeatherAPI"

    def _fetch(self, city, lat, lon):
        if not self.api_key:
            return WeatherResult(self.name, error="API-ключ не задан")
        resp = self.session.get(
            "http://api.weatherapi.com/v1/forecast.json",
            params={"key": self.api_key, "q": f"{lat},{lon}", "days": 2},
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        day = resp.json()["forecast"]["forecastday"][1]["day"]
        return WeatherResult(self.name, temp_min=day["mintemp_c"], temp_max=day["maxtemp_c"],
                             description=day["condition"]["text"])

def geocode(city: str) -> tuple[float, float]:
    if HAS_GEOPY:
        loc = Nominatim(user_agent="weather-agg").geocode(city, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
        raise ValueError(f"Город не найден: {city}")
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "ru"}, timeout=TIMEOUT
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError(f"Город не найден: {city}")
    r = results[0]
    return r["latitude"], r["longitude"]


class WeatherAggregator:
    def __init__(self, owm_key: str = "", wapi_key: str = ""):
        self.sources: list[WeatherSource] = [
            OpenMeteoSource(),
            WttrInSource(),
            Timer7Source(),
            OpenWeatherMapSource(api_key=owm_key),
            WeatherAPISource(api_key=wapi_key),
        ]

    def aggregate(self, city: str) -> None:
        log.info("Гео: %s", city)
        try:
            lat, lon = geocode(city)
            log.info("Координаты: %.4f, %.4f", lat, lon)
        except Exception as exc:
            log.error("Геокодирование не удалось: %s", exc)
            sys.exit(1)
        results = []
        for source in self.sources:
            log.info("Запрос к %s...", source.name)
            results.append(source.fetch(city, lat, lon))
            time.sleep(0.3)
        self._report(city, results)

    @staticmethod
    def _report(city: str, results: list[WeatherResult]) -> None:
        print(f"\nПрогноз на {TOMORROW.strftime('%d.%m.%Y')} - {city}")
        valid = [r for r in results if r.temp_avg is not None]
        print(f"\n{'Источник':<20} {'Мин':>6} {'Макс':>6} {'Средн':>7}  Статус")
        for r in results:
            if r.error:
                print(f"{r.source:<20} {'—':>6} {'—':>6} {'—':>7}  {r.error}")
            else:
                print(f"{r.source:<20} {r.temp_min:>5.1f}° {r.temp_max:>5.1f}° "
                      f"{r.temp_avg:>6.1f}°  {r.description[:25]}")
        if valid:
            avgs = [r.temp_avg for r in valid]
            mins = [r.temp_min for r in valid if r.temp_min is not None]
            maxs = [r.temp_max for r in valid if r.temp_max is not None]
            print(f"\nУсреднённый прогноз ({len(valid)} источников):")
            print(f"   Средняя температура: {mean(avgs):+.1f} °C", end="")
            if len(avgs) > 1:
                print(f" (±{stdev(avgs):.1f} °C разброс)", end="")
            print()
            if mins: print(f"   Мин. температура   : {mean(mins):+.1f} °C")
            if maxs: print(f"   Макс. температура  : {mean(maxs):+.1f} °C")
        else:
            print("\nНи один источник не вернул данные.")

def main():
    parser = argparse.ArgumentParser(description="Агрегатор погодных данных")
    parser.add_argument("city", help="Название города")
    parser.add_argument("--owm-key", default="", help="API-ключ OpenWeatherMap")
    parser.add_argument("--wapi-key", default="", help="API-ключ WeatherAPI")
    args = parser.parse_args()
    WeatherAggregator(owm_key=args.owm_key, wapi_key=args.wapi_key).aggregate(args.city)

if __name__ == "__main__":
    main()