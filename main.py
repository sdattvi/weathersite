import os
import subprocess
import sys

PROJECT_NAME = "weathersite"
APP_NAME = "weatherapp"

# ---------- محتوای فایل‌ها ----------

MAIN_PY = '''import random
import requests


def get_city_images(city_name):
    """Return a list of landmark photo URLs for the city from Wikimedia Commons."""
    headers = {
        "User-Agent": "WeatherApp/1.0 (educational project; contact@example.com)"
    }
    api_url = "https://commons.wikimedia.org/w/api.php"
    urls = []

    try:
        search_params = {
            "action": "query",
            "list": "search",
            "srnamespace": 6,
            "srsearch": f"{city_name} landmark OR skyline OR famous",
            "srlimit": 20,
            "format": "json",
        }
        res = requests.get(api_url, params=search_params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()

        hits = data.get("query", {}).get("search", [])
        if not hits:
            return urls

        skip_ext = (".svg", ".pdf", ".webm", ".ogv", ".djvu", ".tif", ".tiff")
        titles = []
        for hit in hits:
            title = hit.get("title", "")
            if not any(title.lower().endswith(ext) for ext in skip_ext):
                titles.append(title)
            if len(titles) >= 5:
                break

        if not titles:
            return urls

        # Get direct URLs for all chosen titles in one request
        info_params = {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 1920,
            "format": "json",
        }
        info_res = requests.get(api_url, params=info_params, headers=headers, timeout=10)
        info_res.raise_for_status()
        info_data = info_res.json()

        pages = info_data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            imageinfo = page_info.get("imageinfo", [])
            if imageinfo:
                url = imageinfo[0].get("thumburl") or imageinfo[0].get("url")
                if url:
                    urls.append(url)

    except Exception as e:
        print(f"[DEBUG] Wikimedia error: {e}")

    return urls


def fetch_weather(city_name):
    """Fetch 7-day weather forecast + a random city image."""
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {"name": city_name, "count": 1, "language": "en", "format": "json"}
    geo_res = requests.get(geo_url, params=geo_params, timeout=10)
    geo_res.raise_for_status()
    geo_data = geo_res.json()

    if not geo_data.get("results"):
        return {"error": f"Location not found: {city_name}"}

    location = geo_data["results"][0]
    lat, lon = location["latitude"], location["longitude"]
    country = location.get("country", "Unknown")

    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 7,
    }
    weather_res = requests.get(weather_url, params=weather_params, timeout=10)
    weather_res.raise_for_status()
    data = weather_res.json()

    current = data.get("current", {})
    daily = data.get("daily", {})
    days = []
    for i in range(len(daily.get("time", []))):
        days.append({
            "date": daily["time"][i],
            "max": daily["temperature_2m_max"][i],
            "min": daily["temperature_2m_min"][i],
            "rain": daily["precipitation_probability_max"][i],
            "code": daily["weather_code"][i],
        })

    images = get_city_images(city_name)
    image_url = random.choice(images) if images else None

    return {
        "city": city_name.title(),
        "country": country,
        "current": {
            "temp": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "wind": current.get("wind_speed_10m"),
            "code": current.get("weather_code"),
        },
        "days": days,
        "image_url": image_url,
    }
'''

VIEWS_PY = '''from django.shortcuts import render
from .main import fetch_weather


def weather_view(request):
    city = request.GET.get("city", "").strip()
    context = {}

    if city:
        try:
            result = fetch_weather(city)
            if "error" in result:
                context["error"] = result["error"]
            else:
                context["weather"] = result
        except Exception as e:
            context["error"] = f"Request failed: {e}"

    return render(request, "weatherapp/weather.html", context)
'''

APP_URLS_PY = '''from django.urls import path
from . import views

urlpatterns = [
    path("", views.weather_view, name="weather"),
]
'''

PROJECT_URLS_PY = '''from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("weatherapp.urls")),
]
'''

TEMPLATE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atmosphere — Weather Forecast</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        html, body {
            min-height: 100vh;
        }

        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            background: #0f1524;
            color: #e8e8e8;
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 40px 20px;
            position: relative;
            overflow-x: hidden;
        }

        /* Clear background image, blurred only at the edges via mask */
        body::before {
            content: '';
            position: fixed;
            inset: 0;
            z-index: -2;
            background-image: url('{{ weather.image_url|default:"" }}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            /* Very light overall blur, keep the image recognizable */
            filter: blur(2px) brightness(0.85);
            /* Fade out only near the edges */
            -webkit-mask-image: radial-gradient(
                ellipse at center,
                rgba(0,0,0,1) 55%,
                rgba(0,0,0,0.6) 80%,
                rgba(0,0,0,0.15) 100%
            );
            mask-image: radial-gradient(
                ellipse at center,
                rgba(0,0,0,1) 55%,
                rgba(0,0,0,0.6) 80%,
                rgba(0,0,0,0.15) 100%
            );
        }

        /* Gentle dark gradient overlay so the text stays readable */
        body::after {
            content: '';
            position: fixed;
            inset: 0;
            z-index: -1;
            background: linear-gradient(
                135deg,
                rgba(10, 10, 25, 0.35),
                rgba(10, 25, 45, 0.45)
            );
        }

        .container {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 880px;
            background: rgba(15, 20, 35, 0.55);
            backdrop-filter: blur(20px) saturate(140%);
            -webkit-backdrop-filter: blur(20px) saturate(140%);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 24px;
            padding: 48px;
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5),
                        inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }

        h1 {
            font-size: 2.4rem;
            font-weight: 400;
            letter-spacing: 3px;
            text-align: center;
            text-transform: uppercase;
            color: #f5e6c8;
            margin-bottom: 8px;
            text-shadow: 0 2px 20px rgba(245, 230, 200, 0.3);
        }

        .subtitle {
            text-align: center;
            font-size: 0.85rem;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: rgba(232, 232, 232, 0.55);
            margin-bottom: 40px;
        }

        form {
            display: flex;
            gap: 12px;
            justify-content: center;
            margin-bottom: 40px;
            flex-wrap: wrap;
        }

        input[type="text"] {
            flex: 1;
            min-width: 220px;
            max-width: 420px;
            padding: 14px 20px;
            font-size: 1rem;
            font-family: inherit;
            color: #e8e8e8;
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 50px;
            outline: none;
            transition: all 0.35s ease;
        }

        input[type="text"]::placeholder {
            color: rgba(232, 232, 232, 0.4);
            font-style: italic;
        }

        input[type="text"]:focus {
            border-color: rgba(245, 230, 200, 0.7);
            background: rgba(0, 0, 0, 0.45);
            box-shadow: 0 0 0 4px rgba(245, 230, 200, 0.1);
        }

        button {
            padding: 14px 36px;
            font-size: 0.95rem;
            font-family: inherit;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: #1a1a2e;
            background: linear-gradient(135deg, #f5e6c8, #d4b896);
            border: none;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.35s ease;
            box-shadow: 0 8px 24px rgba(245, 230, 200, 0.25);
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 32px rgba(245, 230, 200, 0.4);
        }

        button:active { transform: translateY(0); }

        .error {
            text-align: center;
            color: #ff8a8a;
            font-style: italic;
            padding: 16px;
            background: rgba(255, 100, 100, 0.1);
            border: 1px solid rgba(255, 100, 100, 0.25);
            border-radius: 12px;
            margin-bottom: 24px;
        }

        .city-title {
            text-align: center;
            font-size: 1.8rem;
            font-weight: 400;
            color: #f5e6c8;
            margin-bottom: 4px;
            letter-spacing: 1px;
            text-shadow: 0 2px 12px rgba(0,0,0,0.5);
        }

        .city-country {
            text-align: center;
            font-size: 0.8rem;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: rgba(232, 232, 232, 0.55);
            margin-bottom: 32px;
        }

        .current-card {
            display: flex;
            justify-content: space-around;
            align-items: center;
            flex-wrap: wrap;
            gap: 20px;
            padding: 32px 24px;
            margin-bottom: 40px;
            background: linear-gradient(135deg, rgba(100, 180, 255, 0.12), rgba(245, 230, 200, 0.10));
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 20px;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        .current-item { text-align: center; min-width: 120px; }

        .current-value {
            font-size: 2rem;
            font-weight: 300;
            color: #f5e6c8;
            line-height: 1.2;
            text-shadow: 0 2px 10px rgba(0,0,0,0.4);
        }

        .current-value .unit {
            font-size: 1rem;
            color: rgba(245, 230, 200, 0.7);
        }

        .current-label {
            font-size: 0.7rem;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: rgba(232, 232, 232, 0.55);
            margin-top: 6px;
        }

        .forecast-title {
            font-size: 0.85rem;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: rgba(232, 232, 232, 0.6);
            text-align: center;
            margin-bottom: 20px;
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 8px;
        }

        thead th {
            font-size: 0.7rem;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: rgba(232, 232, 232, 0.55);
            font-weight: 400;
            padding: 8px 12px;
            text-align: center;
        }

        tbody tr {
            background: rgba(255, 255, 255, 0.06);
            transition: all 0.3s ease;
        }

        tbody tr:hover {
            background: rgba(255, 255, 255, 0.12);
            transform: scale(1.01);
        }

        tbody td {
            padding: 16px 12px;
            text-align: center;
            font-size: 0.95rem;
            color: #e8e8e8;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        tbody td:first-child {
            border-left: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px 0 0 12px;
            color: #f5e6c8;
            font-weight: 500;
        }

        tbody td:last-child {
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 0 12px 12px 0;
        }

        .temp-max { color: #ffcf8a; }
        .temp-min { color: #8ab4ff; }
        .rain     { color: #8ae0ff; }

        footer {
            text-align: center;
            margin-top: 36px;
            font-size: 0.7rem;
            letter-spacing: 2px;
            text-transform: uppercase;
            color: rgba(232, 232, 232, 0.35);
        }

        @media (max-width: 600px) {
            .container { padding: 28px 20px; }
            h1 { font-size: 1.6rem; letter-spacing: 2px; }
            .current-value { font-size: 1.5rem; }
            tbody td, thead th { padding: 10px 6px; font-size: 0.8rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Atmosphere</h1>
        <p class="subtitle">Seven-Day Weather Forecast</p>

        <form method="get">
            <input type="text" name="city" placeholder="Enter a city name…" value="{{ request.GET.city }}">
            <button type="submit">Search</button>
        </form>

        {% if error %}
            <p class="error">{{ error }}</p>
        {% endif %}

        {% if weather %}
            <h2 class="city-title">{{ weather.city }}</h2>
            <p class="city-country">{{ weather.country }}</p>

            <div class="current-card">
                <div class="current-item">
                    <div class="current-value">{{ weather.current.temp }}<span class="unit">°C</span></div>
                    <div class="current-label">Temperature</div>
                </div>
                <div class="current-item">
                    <div class="current-value">{{ weather.current.humidity }}<span class="unit">%</span></div>
                    <div class="current-label">Humidity</div>
                </div>
                <div class="current-item">
                    <div class="current-value">{{ weather.current.wind }}<span class="unit">km/h</span></div>
                    <div class="current-label">Wind</div>
                </div>
                <div class="current-item">
                    <div class="current-value">{{ weather.current.code }}</div>
                    <div class="current-label">Condition</div>
                </div>
            </div>

            <p class="forecast-title">Next Seven Days</p>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Max</th>
                        <th>Min</th>
                        <th>Rain</th>
                        <th>Code</th>
                    </tr>
                </thead>
                <tbody>
                    {% for day in weather.days %}
                    <tr>
                        <td>{{ day.date }}</td>
                        <td class="temp-max">{{ day.max }}°</td>
                        <td class="temp-min">{{ day.min }}°</td>
                        <td class="rain">{{ day.rain }}%</td>
                        <td>{{ day.code }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endif %}

        <footer>Powered by Open-Meteo &amp; Wikimedia Commons</footer>
    </div>
</body>
</html>
'''


# ---------- توابع کمکی ----------

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  created: {path}")


def run(cmd, cwd=None):
    print(f"  running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"ERROR: command failed -> {' '.join(cmd)}")
        sys.exit(1)


# ---------- اجرای اصلی ----------

def main():
    inner_dir = os.path.join(PROJECT_NAME, PROJECT_NAME)
    settings_path = os.path.join(inner_dir, "settings.py")
    project_urls_path = os.path.join(inner_dir, "urls.py")
    app_path = os.path.join(PROJECT_NAME, APP_NAME)

    print("Step 1: Creating Django project...")
    if not os.path.exists(settings_path):
        run([sys.executable, "-m", "django", "startproject", PROJECT_NAME])
    else:
        print(f"  {PROJECT_NAME}/ already exists, skipping.")

    print("Step 2: Creating Django app...")
    if not os.path.exists(app_path):
        run(
            [sys.executable, "-m", "django", "startapp", APP_NAME],
            cwd=PROJECT_NAME,
        )
        print(f"  app created: {app_path}")
    else:
        print(f"  {app_path}/ already exists, skipping.")

    print("Step 3: Writing app files...")
    write_file(os.path.join(app_path, "main.py"), MAIN_PY)
    write_file(os.path.join(app_path, "views.py"), VIEWS_PY)
    write_file(os.path.join(app_path, "urls.py"), APP_URLS_PY)
    write_file(
        os.path.join(app_path, "templates", APP_NAME, "weather.html"),
        TEMPLATE_HTML,
    )

    print("Step 4: Updating project urls.py...")
    write_file(project_urls_path, PROJECT_URLS_PY)

    print("Step 5: Registering app in settings.py...")
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = f.read()

    if f"'{APP_NAME}'" not in settings:
        settings = settings.replace(
            "INSTALLED_APPS = [",
            f"INSTALLED_APPS = [\n    '{APP_NAME}',",
            1,
        )
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(settings)
        print(f"  added '{APP_NAME}' to INSTALLED_APPS")
    else:
        print(f"  '{APP_NAME}' already in INSTALLED_APPS")

    print("\nDone!")
    print("\nNext steps:")
    print(f"  cd {PROJECT_NAME}")
    print(f"  py manage.py runserver")
    print(f"  Open http://127.0.0.1:8000/ in your browser")


if __name__ == "__main__":
    main()