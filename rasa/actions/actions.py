"""
Custom Actions for Travel Assistant Bot - Yoliday Internship Assessment
Enhanced with proper error handling, HEAD support, and robust slot management
Author: Travel Assistant Bot Developer
"""

import requests
import logging
import ast
import json
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from rasa_sdk.types import DomainDict

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Removed Sanic app creation and health endpoint ---

class ActionGetWeather(Action):
    """Custom action to fetch weather information from Open-Meteo free API"""
    
    def name(self) -> Text:
        return "action_get_weather"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Log current tracker state for debugging
        logger.debug(f"Tracker state: {json.dumps(tracker.current_state(), indent=2)}")
        
        # Extract city from entities or slot
        city = next(
            (e["value"] for e in tracker.latest_message.get("entities", [])
            if e["entity"] == "location"
        ), None) or tracker.get_slot("destination_city")
        
        # If no city found, prompt user
        if not city:
            dispatcher.utter_message(text="🏙️ I'd love to help you check the weather! Please specify which city you're interested in.")
            dispatcher.utter_message(response="utter_weather_options")
            return [SlotSet("destination_city", None), SlotSet("weather_info", None)]
        
        logger.info(f"Fetching weather for: {city}")
        events_to_return = [SlotSet("destination_city", city)]
        
        try:
            # Get coordinates for the city
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
            
            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            if not geo_data.get("results"):
                dispatcher.utter_message(text=f"🔍 Sorry, I couldn't find weather data for '{city.title()}'. Please check the spelling or try a different city name.")
                dispatcher.utter_message(response="utter_weather_options")
                return [SlotSet("destination_city", None), SlotSet("weather_info", None)]
            
            # Get coordinates and location details
            location = geo_data["results"][0]
            latitude = location["latitude"]
            longitude = location["longitude"]
            city_name = location["name"]
            country = location.get("country", "")
            
            # Get weather data
            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto"
            }
            
            weather_response = requests.get(weather_url, params=weather_params, timeout=10)
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            # Extract current weather information
            current = weather_data["current"]
            temperature = current["temperature_2m"]
            humidity = current["relative_humidity_2m"]
            wind_speed = current["wind_speed_10m"]
            weather_code = current["weather_code"]
            weather_description = self._get_weather_description(weather_code)
            
            # Format weather report
            location_display = f"{city_name}, {country}" if country else city_name
            weather_report = f"""
🌤️ **Current Weather for {location_display}**

🌡️ **Temperature**: {temperature}°C
🌫️ **Conditions**: {weather_description}
💧 **Humidity**: {humidity}%
🌪️ **Wind Speed**: {wind_speed} km/h

*Weather data provided by Open-Meteo*
            """
            
            dispatcher.utter_message(text=weather_report.strip())
            
            # Store weather info for packing recommendations
            weather_info = {
                "temperature": temperature,
                "description": weather_description.lower(),
                "humidity": humidity,
                "wind_speed": wind_speed
            }
            
            events_to_return.append(SlotSet("weather_info", str(weather_info)))
            
            # Provide guided next steps
            dispatcher.utter_message(response="utter_after_weather")
            
            return events_to_return
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            dispatcher.utter_message(text=f"🌐 Sorry, I'm having trouble connecting to the weather service right now. Please try again later.")
            return events_to_return
        
        except Exception as e:
            logger.exception(f"Unexpected error in ActionGetWeather: {e}")
            dispatcher.utter_message(text="⚠️ An unexpected error occurred while fetching weather data.")
            return events_to_return
    
    def _get_weather_description(self, code: int) -> str:
        """Convert WMO weather code to human-readable description"""
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
            55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        return weather_codes.get(code, "Unknown conditions")

class ActionRecommendPacking(Action):
    """Custom action to provide intelligent packing recommendations"""
    
    def name(self) -> Text:
        return "action_recommend_packing"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get city from slot or entities
        city = tracker.get_slot("destination_city") or next(
            (e["value"] for e in tracker.latest_message.get("entities", [])
            if e["entity"] == "location"), None
        )
        
        if not city:
            dispatcher.utter_message(text="🎒 I'd love to help you pack smart! Which destination do you need packing advice for?")
            dispatcher.utter_message(response="utter_packing_options")
            return [SlotSet("destination_city", None)]
            
        # Get current weather info
        weather_info_str = tracker.get_slot("weather_info")
        
        # If no weather data, try to fetch it
        if not weather_info_str or weather_info_str == "None":
            logger.info(f"No weather data found for {city}, fetching now...")
            weather_action = ActionGetWeather()
            weather_events = weather_action.run(dispatcher, tracker, domain)
            
            # Update weather info from events
            for event in weather_events:
                if isinstance(event, SlotSet) and event.key == "weather_info":
                    weather_info_str = event.value
                    break
        
        # Generate packing recommendations
        packing_list = self._generate_packing_recommendations(weather_info_str, city)
        dispatcher.utter_message(text=packing_list)
        
        # Provide guided next steps
        dispatcher.utter_message(response="utter_after_packing")
        
        return [
            SlotSet("destination_city", city),
            SlotSet("packing_suggestions", packing_list)
        ]
    
    def _generate_packing_recommendations(self, weather_info_str: str, city: str) -> str:
        """Generate packing recommendations with weather context"""
        
        # Initialize with default recommendations
        recommendations = {
            "essentials": [
                "Valid ID/passport and travel documents",
                "Phone charger and portable power bank",
                "Basic first aid kit with personal medications",
                "Comfortable walking shoes",
                "Travel insurance documents",
                "Emergency contact information"
            ],
            "clothing": [
                "Versatile layers (t-shirts, light sweater, jacket)",
                "Comfortable pants and shorts",
                "Versatile footwear for walking"
            ],
            "accessories": [
                "Universal travel adapter",
                "Reusable water bottle",
                "Day backpack or travel bag"
            ],
            "weather_specific": [
                "Check weather for specific recommendations"
            ]
        }
        
        temperature = None
        weather_desc = ""
        
        # Parse weather info if available
        if weather_info_str and weather_info_str != "None":
            try:
                weather_dict = ast.literal_eval(weather_info_str)
                temperature = weather_dict.get("temperature")
                weather_desc = weather_dict.get("description", "").lower()
                logger.info(f"Using weather data: temp={temperature}, desc={weather_desc}")
            except Exception as e:
                logger.error(f"Could not parse weather_info: {e}")
        
        # Temperature-based recommendations
        if temperature is not None:
            if temperature < 5:
                recommendations["clothing"] = [
                    "Heavy winter jacket or down coat",
                    "Thermal underwear and warm layers",
                    "Woolen sweaters and fleece",
                    "Insulated winter boots"
                ]
                recommendations["weather_specific"] = [
                    "Warm gloves, scarf, and beanie",
                    "Thick wool socks",
                    "Hand and foot warmers"
                ]
                
            elif 5 <= temperature < 15:
                recommendations["clothing"] = [
                    "Warm jacket or windcheater",
                    "Long-sleeve shirts and sweaters",
                    "Jeans or warm pants",
                    "Closed-toe shoes or boots"
                ]
                
            elif 15 <= temperature < 25:
                recommendations["clothing"] = [
                    "Light cardigan or thin jacket",
                    "Mix of cotton t-shirts and long sleeves",
                    "Comfortable jeans or cotton pants",
                    "Sneakers or comfortable walking shoes"
                ]
                
            elif 25 <= temperature < 35:
                recommendations["clothing"] = [
                    "Cotton t-shirts and breathable fabrics",
                    "Shorts, cotton pants, or light dresses",
                    "Comfortable sandals or breathable shoes",
                    "Light cotton shirts for sun protection"
                ]
                
            else:  # temperature >= 35 (hot weather)
                recommendations["clothing"] = [
                    "Lightweight cotton or linen clothing",
                    "Loose-fitting shirts and breathable fabrics",
                    "Cotton shorts and comfortable sandals",
                    "Wide-brimmed hat or cap"
                ]
                recommendations["weather_specific"] = [
                    "High SPF sunscreen (30+ recommended)",
                    "Cooling towel or neck wrap",
                    "Extra water bottle"
                ]
        
        # Weather condition-specific additions
        if "rain" in weather_desc or "drizzle" in weather_desc:
            recommendations["weather_specific"].extend([
                "Waterproof rain jacket or poncho",
                "Compact umbrella",
                "Waterproof shoes or boots"
            ])
            
        elif "snow" in weather_desc:
            recommendations["weather_specific"].extend([
                "Waterproof snow boots with good grip",
                "Insulated gloves and warm socks",
                "Waterproof outer layer"
            ])
            
        elif "sun" in weather_desc or "clear" in weather_desc:
            recommendations["weather_specific"].extend([
                "UV protection sunglasses",
                "Broad-spectrum sunscreen",
                "Sun hat or cap with UV protection"
            ])
        
        # Format the comprehensive packing message
        packing_message = f"🧳 **Smart Packing Recommendations for {city.title()}**\n\n"
        
        if temperature is not None:
            packing_message += f"*Customized for current weather: {temperature}°C, {weather_desc.title()}*\n\n"
        else:
            packing_message += "*General recommendations (check weather for more specific advice)*\n\n"
        
        # Add each category
        category_titles = {
            "essentials": "🎯 Essentials",
            "clothing": "👕 Clothing", 
            "accessories": "🔧 Accessories",
            "weather_specific": "🌤️ Weather Specific"
        }
        
        for category, items in recommendations.items():
            if items:
                packing_message += f"**{category_titles.get(category, category.title())}:**\n"
                for item in items:
                    packing_message += f"• {item}\n"
                packing_message += "\n"
        
        packing_message += "*💡 Pro Tip: Pack light and check airline baggage policies!*"
        
        return packing_message

class ActionProvideWeatherOptions(Action):
    """Provide weather checking options to guide users"""
    
    def name(self) -> Text:
        return "action_provide_weather_options"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(response="utter_weather_options")
        return []

class ActionProvidePackingOptions(Action):
    """Provide packing options to guide users"""
    
    def name(self) -> Text:
        return "action_provide_packing_options"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(response="utter_packing_options")
        return []

class ValidateTravelInfoForm(FormValidationAction):
    """Custom form validation for travel information"""
    
    def name(self) -> Text:
        return "validate_travel_info_form"
    
    def validate_destination_city(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate destination city input"""
        
        if not slot_value:
            dispatcher.utter_message(text="🏙️ Please provide a valid city name for your destination.")
            return {"destination_city": None}
        
        city_name = str(slot_value).strip()
        
        if len(city_name) < 2:
            dispatcher.utter_message(text="🔍 Please provide a city name with at least 2 characters.")
            return {"destination_city": None}
        
        return {"destination_city": city_name.title()}
    
    def validate_start_date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate start date input"""
        
        if not slot_value:
            dispatcher.utter_message(text="📅 Please provide your travel start date (e.g., 'next week', 'December 15th').")
            return {"start_date": None}
        
        date_str = str(slot_value).strip()
        
        if len(date_str) < 3:
            dispatcher.utter_message(text="📅 Please provide a valid start date with more detail.")
            return {"start_date": None}
        
        return {"start_date": date_str}
    
    def validate_end_date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate end date input"""
        
        if not slot_value:
            dispatcher.utter_message(text="🔙 Please provide your return date or trip duration.")
            return {"end_date": None}
        
        date_str = str(slot_value).strip()
        
        if len(date_str) < 3:
            dispatcher.utter_message(text="🔙 Please provide more details about your return date.")
            return {"end_date": None}
        
        return {"end_date": date_str}