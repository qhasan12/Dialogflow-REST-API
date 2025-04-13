from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import requests
import dateparser

app = Flask(__name__)
API_KEY = 'f5281b34c2c2c8585c0d6568973cf737'

def parse_date(date_str):
    try:
        if not date_str or date_str.strip().lower() in ['now', 'today']:
            return datetime.now()
        if date_str.lower() == 'tomorrow':
            return datetime.now() + timedelta(days=1)
        return dateparser.parse(date_str)
    except:
        return None

def format_date_with_day(date_obj):
    return date_obj.strftime("%A, %B %d, %Y")

def get_city_coordinates(city):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    response = requests.get(url).json()
    if response:
        return response[0]["lat"], response[0]["lon"]
    return None, None

@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json()
    parameters = req.get("queryResult", {}).get("parameters", {})
    city = parameters.get("geo-city", "")
    date_str = parameters.get("date-time", "") or parameters.get("date", "")

    if not city:
        return jsonify({"fulfillmentText": "Please specify a city to get the weather information."})

    forecast_date = parse_date(date_str)
    today = datetime.now().date()

    #Current Weather -----------------------
    if not forecast_date or forecast_date.date() == today:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            weather = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]["speed"]
            date_today = format_date_with_day(datetime.now())

            reply = f"Current weather in {city} on {date_today}:\n{weather}, temperature: {temp}°C, humidity: {humidity}%, wind speed: {wind} km/h."
            return jsonify({'fulfillmentText': reply})
        else:
            return jsonify({'fulfillmentText': "Sorry, I couldn't fetch the current weather data for that city."})

    # Forecast ----------------------
    lat, lon = get_city_coordinates(city)
    if lat is None:
        return jsonify({'fulfillmentText': "Sorry, I couldn't find the location you mentioned."})

    one_call_url = (
        f"https://api.openweathermap.org/data/3.0/onecall?"
        f"lat={lat}&lon={lon}&exclude=minutely,hourly,current,alerts&units=metric&appid={API_KEY}"
    )
    response = requests.get(one_call_url)
    if response.status_code != 200:
        return jsonify({'fulfillmentText': "Sorry, I couldn't fetch weather forecast data."})

    forecast_data = response.json()
    daily_data = forecast_data.get("daily", [])

    if not daily_data:
        return jsonify({'fulfillmentText': "Forecast data is not available right now."})

    # Get start and end dates
    start_date = format_date_with_day(datetime.fromtimestamp(daily_data[0]["dt"]))
    end_date = format_date_with_day(datetime.fromtimestamp(daily_data[min(7, len(daily_data)-1)]["dt"]))

    reply_lines = []
    for day in daily_data[:8]:
        date_obj = datetime.fromtimestamp(day["dt"])
        desc = day["weather"][0]["description"].capitalize()
        temp = day["temp"]["day"]
        wind = day["wind_speed"]
        humidity = day["humidity"]
        reply_lines.append(
            f"{format_date_with_day(date_obj)}:\n"
            f"{desc}, temperature: {temp:.1f}°C, humidity: {humidity}%, wind speed: {wind} km/h."
        )

    reply = (
        f"The weather forecast from {start_date} to {end_date} for {city} is:\n\n" +
        "\n\n".join(reply_lines)
    )
    return jsonify({'fulfillmentText': reply})

if __name__ == "__main__":
    app.run(debug=True)
