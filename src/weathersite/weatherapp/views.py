from django.shortcuts import render
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
