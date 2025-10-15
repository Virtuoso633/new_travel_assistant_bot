# -------------------------
# actions.py (World-Class Version)
# -------------------------
"""
Custom Actions for Travel Assistant Bot - Yoliday Internship Assessment
This file contains custom actions using Open-Meteo free weather API with enhanced user guidance.
Author: Travel Assistant Bot Developer
"""

import logging
from typing import Any, Text, Dict, List
import requests
import ast

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.types import DomainDict

logger = logging.getLogger(__name__)

# --- HELPER FUNCTION TO GET WEATHER (to avoid code repetition) ---
def _get_weather_data(city: str, dispatcher: CollectingDispatcher) -> Dict[Text, Any]:
    try:
        formatted_city = city.title() if city else ""
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={formatted_city}&count=1"
        geo_response = requests.get(geo_url, timeout=10)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        if not geo_data.get("results"):
            dispatcher.utter_message(text=f"🔍 I couldn't find '{city}'. Please check the spelling.")
            return None
        
        loc = geo_data["results"][0]
        # FIXED: Changed ¤t= to &current= in the URL parameter
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={loc['latitude']}&longitude={loc['longitude']}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        weather_response = requests.get(weather_url, timeout=10)
        weather_response.raise_for_status()
        
        weather_data = weather_response.json()
        weather_data['location_name'] = f"{loc['name']}, {loc.get('country', '')}".strip()
        return weather_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        dispatcher.utter_message(text="🌐 Sorry, I'm having trouble connecting to the weather service right now.")
        return None

def _get_weather_description(code: int) -> str:
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
        55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    return weather_codes.get(code, "Unknown conditions")


class ActionGetWeather(Action):
    """Custom action to fetch weather information from Open-Meteo free API"""
    
    def name(self) -> Text:
        return "action_get_weather"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # --- ENHANCED "UN-STICK" LOGIC ---
        # If the user provides a new city, it should overwrite the old one.
        new_city_entity = next((e["value"] for e in tracker.latest_message.get("entities", []) if e["entity"] == "location"), None)
        city_to_check = new_city_entity or tracker.get_slot("destination_city")

        if not city_to_check:
            dispatcher.utter_message(response="utter_ask_destination_city")
            return []

        weather_data = _get_weather_data(city_to_check, dispatcher)
        if not weather_data:
            return [SlotSet("destination_city", None)] # Reset if city not found

        current = weather_data['current']
        report = (f"🌤️ **Current Weather for {weather_data['location_name']}**\n\n"
                  f"🌡️ **Temperature**: {current['temperature_2m']}°C\n"
                  f"🌫️ **Conditions**: {_get_weather_description(current['weather_code'])}\n"
                  f"💧 **Humidity**: {current['relative_humidity_2m']}%\n"
                  f"🌪️ **Wind Speed**: {current['wind_speed_10m']} km/h\n\n"
                  f"*Weather data provided by Open-Meteo*")
        dispatcher.utter_message(text=report)
        
        weather_info = {
            "temperature": current['temperature_2m'],
            "description": _get_weather_description(current['weather_code']).lower(),
            "humidity": current['relative_humidity_2m'],
            "wind_speed": current['wind_speed_10m']
        }
        
        dispatcher.utter_message(response="utter_after_weather", destination_city=city_to_check)
        return [SlotSet("destination_city", city_to_check), SlotSet("weather_info", str(weather_info))]

class ActionRecommendPacking(Action):
    """Custom action to provide intelligent packing recommendations based on weather conditions"""
    
    def name(self) -> Text:
        return "action_recommend_packing"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        new_city_entity = next((e["value"] for e in tracker.latest_message.get("entities", []) if e["entity"] == "location"), None)
        city = new_city_entity or tracker.get_slot("destination_city")

        if not city:
            dispatcher.utter_message(text="I can give you packing tips, but I need to know which city you're traveling to first.")
            return [SlotSet("destination_city", None)]
                
        # If we have a city but no weather info, get weather first using FollowupAction
        weather_info_str = tracker.get_slot("weather_info")
        if not weather_info_str:
            dispatcher.utter_message(text=f"To give you the best packing advice for {city.title()}, I'll check the weather first.")
            return [SlotSet("destination_city", city), FollowupAction("action_get_weather")]

        # With weather data, generate packing recommendations
        packing_list = self._generate_packing_recommendations(weather_info_str, city)
        dispatcher.utter_message(text=packing_list)
        
        # Using response selector instead of direct utterance
        dispatcher.utter_message(response="utter_after_packing", destination_city=city)
        return []

    def _generate_packing_recommendations(self, weather_info_str: str, city: str) -> str:
        recommendations = {
            "essentials": [], "clothing": [], "accessories": [], "weather_specific": []
        }
        temperature = None
        weather_desc = ""
        
        if weather_info_str and weather_info_str != "None":
            try:
                weather_dict = ast.literal_eval(weather_info_str)
                temperature = weather_dict.get("temperature")
                weather_desc = weather_dict.get("description", "").lower()
            except (ValueError, SyntaxError) as e:
                logger.error(f"Could not parse weather_info slot: {weather_info_str}. Error: {e}")
                pass
        
        if temperature is not None:
            if temperature < 5:
                recommendations["clothing"].extend(["Heavy winter jacket or down coat", "Thermal underwear and warm layers", "Woolen sweaters and fleece", "Insulated winter boots", "Warm gloves, scarf, and beanie", "Thick wool socks"])
                recommendations["weather_specific"].extend(["Hand and foot warmers", "Lip balm for cold weather", "Moisturizing cream for dry skin"])
            elif 5 <= temperature < 15:
                recommendations["clothing"].extend(["Warm jacket or windcheater", "Long-sleeve shirts and sweaters", "Jeans or warm pants", "Closed-toe shoes or boots", "Light jacket for layering"])
            elif 15 <= temperature < 25:
                recommendations["clothing"].extend(["Light cardigan or thin jacket", "Mix of cotton t-shirts and long sleeves", "Comfortable jeans or cotton pants", "Sneakers or comfortable walking shoes", "Light sweater for evenings"])
            elif 25 <= temperature < 35:
                recommendations["clothing"].extend(["Cotton t-shirts and breathable fabrics", "Shorts, cotton pants, or light dresses", "Comfortable sandals or breathable shoes", "Light cotton shirts for sun protection", "Thin cardigan for air-conditioned places"])
            else:
                recommendations["clothing"].extend(["Lightweight cotton or linen clothing", "Loose-fitting shirts and breathable fabrics", "Cotton shorts and comfortable sandals", "Wide-brimmed hat or cap", "Light-colored clothing to reflect heat"])
                recommendations["weather_specific"].extend(["High SPF sunscreen (30+ recommended)", "Cooling towel or neck wrap", "Extra water bottle and electrolyte drinks", "Portable fan or cooling spray"])
        else:
            recommendations["clothing"].extend(["Versatile layers (t-shirts, light sweater, jacket)", "Comfortable pants and shorts", "Versatile footwear for walking"])
        
        if "rain" in weather_desc or "drizzle" in weather_desc:
            recommendations["weather_specific"].extend(["Waterproof rain jacket or poncho", "Compact umbrella", "Waterproof shoes or boots", "Quick-dry clothing and plastic bags for electronics"])
        elif "snow" in weather_desc:
            recommendations["weather_specific"].extend(["Waterproof snow boots with good grip", "Insulated gloves and warm socks", "Waterproof outer layer", "Warm scarf and thermal wear"])
        elif "sun" in weather_desc or "clear" in weather_desc:
            recommendations["weather_specific"].extend(["UV protection sunglasses", "Broad-spectrum sunscreen", "Sun hat or cap with UV protection", "Light, long-sleeved shirt for sun protection"])
        
        recommendations["essentials"] = ["Valid ID/passport and travel documents", "Phone charger and portable power bank", "Basic first aid kit with personal medications", "Comfortable walking shoes", "Travel insurance documents", "Emergency contact information"]
        recommendations["accessories"] = ["Universal travel adapter (for international trips)", "Reusable water bottle", "Day backpack or travel bag", "Travel pillow for long journeys", "Entertainment (books, downloaded content)", "Camera or smartphone for memories"]
        
        packing_message = f"🧳 **Smart Packing Recommendations for {city.title()}**\n\n"
        if temperature is not None:
            packing_message += f"*Customized for current weather: {temperature}°C, {weather_desc.title()}*\n\n"
        else:
            packing_message += "*General recommendations (check weather for more specific advice)*\n\n"
        
        category_emojis = {"essentials": "🎯", "clothing": "👕", "accessories": "🔧", "weather_specific": "🌤️"}
        for category, items in recommendations.items():
            if items:
                category_title = category.replace("_", " ").title()
                emoji = category_emojis.get(category, "📋")
                packing_message += f"**{emoji} {category_title}:**\n"
                for item in items:
                    packing_message += f"• {item}\n"
                packing_message += "\n"
        
        packing_message += "*💡 Pro Tip: Pack light and check airline baggage policies. Safe travels!*"
        return packing_message

class ActionAskForNewCity(Action):
    """Resets key slots and asks the user for a new city."""
    
    def name(self) -> Text:
        return "action_ask_for_new_city"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(response="utter_ask_destination_city")
        # Reset slots to ensure a clean slate for the new city
        return [SlotSet("destination_city", None), SlotSet("weather_info", None)]

class ActionResetSlotsAndAsk(Action):
    """Resets key slots and asks the user for a new city."""
    
    def name(self) -> Text:
        return "action_reset_slots_and_ask"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(response="utter_ask_destination_city")
        return [SlotSet("destination_city", None), SlotSet("weather_info", None)]

class ActionClarifyCityUsage(Action):
    """Fires when user just says a city name, to ask what they want to do."""
    
    def name(self) -> Text:
        return "action_clarify_city_usage"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        city = tracker.get_slot("destination_city") or next((e["value"] for e in tracker.latest_message.get("entities", []) if e["entity"] == "location"), "that city")
        dispatcher.utter_message(response="utter_clarify_city_usage", destination_city=city.title())
        return [SlotSet("destination_city", city)]

class ValidateTravelInfoForm(FormValidationAction):
    """Custom form validation for travel information with enhanced user guidance"""
    
    def name(self) -> Text:
        return "validate_travel_info_form"
    
    def validate_destination_city(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if not slot_value:
            dispatcher.utter_message(text="🏙️ Please provide a valid city name for your destination.")
            return {"destination_city": None}
        city_name = str(slot_value).strip()
        if len(city_name) < 2:
            dispatcher.utter_message(text="🔍 Please provide a city name with at least 2 characters.")
            return {"destination_city": None}
        return {"destination_city": city_name.title()}
    
    def validate_start_date(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if not slot_value:
            dispatcher.utter_message(text="📅 Please provide your travel start date (e.g., 'next week', 'December 15th', or '2024-12-15').")
            return {"start_date": None}
        date_str = str(slot_value).strip()
        if len(date_str) < 3:
            dispatcher.utter_message(text="📅 Please provide a valid start date with more detail.")
            return {"start_date": None}
        return {"start_date": date_str}
    
    def validate_end_date(self, slot_value: Any, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Dict[Text, Any]:
        if not slot_value:
            dispatcher.utter_message(text="🔙 Please provide your return date or trip duration (e.g., 'same day', 'one week', 'December 20th').")
            return {"end_date": None}
        date_str = str(slot_value).strip()
        if len(date_str) < 3:
            dispatcher.utter_message(text="🔙 Please provide more details about your return date or trip duration.")
            return {"end_date": None}
        return {"end_date": date_str}