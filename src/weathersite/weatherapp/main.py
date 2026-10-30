import random
import httpx


def get_city_images(city_name):
    headers = {"User-Agent": "WeatherApp/1.0 (educational project)"}
    api_url = "https://commons.wikimedia.org/w/api.php"
    urls = []
    try:
        search_params = {
            "action": "query", "list": "search", "srnamespace": 6,
            "srsearch": f"{city_name} landmark OR skyline OR famous",
            "srlimit": 20, "format": "json",
        }
        res = httpx.get(api_url, params=search_params, headers=headers, timeout=10.0)
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
        info_params = {
            "action": "query", "titles": "|".join(titles),
            "prop": "imageinfo", "iiprop": "url", "iiurlwidth": 1920, "format": "json",
        }
        info_res = httpx.get(api_url, params=info_params, headers=headers, timeout=10.0)
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
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {"name": city_name, "count": 1, "language": "en", "format": "json"}
    geo_res = httpx.get(geo_url, params=geo_params, timeout=10.0)
    geo_res.raise_for_status()
    geo_data = geo_res.json()
    if not geo_data.get("results"):
        return {"error": f"Location not found: {city_name}"}
    location = geo_data["results"][0]
    lat, lon = location["latitude"], location["longitude"]
    country = location.get("country", "Unknown")
    weather_url = "https://api.open-meteo.com/v1/forecast"
    weather_params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
        "timezone": "auto", "forecast_days": 7,
    }
    weather_res = httpx.get(weather_url, params=weather_params, timeout=10.0)
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
        "city": city_name.title(), "country": country,
        "current": {
            "temp": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "wind": current.get("wind_speed_10m"),
            "code": current.get("weather_code"),
        },
        "days": days, "image_url": image_url,
    }
