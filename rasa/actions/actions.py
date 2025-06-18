"""
Custom Actions for Travel Assistant Bot - Yoliday Internship Assessment
This file contains custom actions using Open-Meteo free weather API with enhanced user guidance.
Author: Travel Assistant Bot Developer
"""

import requests
import logging
import ast
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from rasa_sdk.types import DomainDict

# Set up logging
logger = logging.getLogger(__name__)

class ActionGetWeather(Action):
    """Custom action to fetch weather information from Open-Meteo free API"""
    
    def name(self) -> Text:
        return "action_get_weather"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        city = next((e["value"] for e in tracker.latest_message.get("entities", [])
                    if e["entity"] == "location"), None)
        
        if city:
            logger.info(f"Found city '{city}' from new entity.")
        
        
        # 2. If no new entity was found, fall back to the slot value
        if not city:
            city = tracker.get_slot("destination_city")
            if city:
                logger.info(f"Using city '{city}' from existing slot.")
        
        # 3. If no city is found in either, provide guidance
        if not city:
            dispatcher.utter_message(text="🏙️ I'd love to help you check the weather! Please specify which city you're interested in.")
            dispatcher.utter_message(response="utter_weather_options")
            return []
        
        ### IMPORTANT: Update the slot with the correct city ###
        events_to_return = [SlotSet("destination_city", city)]
        
        try:
            # Get coordinates for the city using Open-Meteo's geocoding
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
            
            geo_response = requests.get(geo_url, params=geo_params, timeout=10)
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            
            if not geo_data.get("results"):
                dispatcher.utter_message(text=f"🔍 Sorry, I couldn't find weather data for '{city.title()}'. Please check the spelling or try a different city name.")
                dispatcher.utter_message(response="utter_weather_options")
                return [SlotSet("destination_city", None)]
            
            # Get coordinates and location details
            location = geo_data["results"][0]
            latitude = location["latitude"]
            longitude = location["longitude"]
            city_name = location["name"]
            country = location.get("country", "")
            
            # Get weather data from Open-Meteo
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
            
            # Format weather report with enhanced presentation
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
            logger.error(f"API request failed: {e}")
            dispatcher.utter_message(text=f"🌐 Sorry, I'm having trouble connecting to the weather service right now. Please try again in a moment.")
            dispatcher.utter_message(response="utter_weather_options")
            return events_to_return
        
        except Exception as e:
            logger.error(f"An unexpected error occurred in ActionGetWeather: {e}")
            dispatcher.utter_message(text="⚠️ An unexpected error occurred while fetching weather data. Please try again.")
            dispatcher.utter_message(response="utter_weather_options")
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
    """Custom action to provide intelligent packing recommendations based on weather conditions"""
    
    def name(self) -> Text:
        return "action_recommend_packing"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        ### CORRECTED LOGIC TO PRIORITIZE NEW ENTITIES ###
        city = None
        
        # 1. First, try to get the city from the latest user message's entities
        entities = tracker.latest_message.get("entities", [])
        for entity in entities:
            if entity.get("entity") == "location":
                city = entity.get("value")
                logger.info(f"Found city '{city}' from new entity for packing.")
                break
        
        # 2. If no new entity was found, fall back to the slot value
        if not city:
            city = tracker.get_slot("destination_city")
            if city:
                logger.info(f"Using city '{city}' from existing slot for packing.")

        # 3. If no city is found, provide guidance
        if not city:
            dispatcher.utter_message(text="🎒 I'd love to help you pack smart! Which destination do you need packing advice for?")
            dispatcher.utter_message(response="utter_packing_options")
            return []
            
        # Get current weather info for this city if available
        weather_info_str = tracker.get_slot("weather_info")
        
        # If we don't have weather info for this city, fetch it first
        if not weather_info_str:
            # Try to get weather data first
            weather_action = ActionGetWeather()
            weather_events = weather_action.run(dispatcher, tracker, domain)
            
            # Get updated weather info after fetching
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
        """Generate intelligent packing recommendations based on weather conditions"""
        
        recommendations = {
            "essentials": [],
            "clothing": [],
            "accessories": [],
            "weather_specific": []
        }
        
        temperature = None
        weather_desc = ""
        
        # Parse weather info if available
        if weather_info_str and weather_info_str != "None":
            try:
                weather_dict = ast.literal_eval(weather_info_str)
                temperature = weather_dict.get("temperature")
                weather_desc = weather_dict.get("description", "").lower()
            except (ValueError, SyntaxError) as e:
                logger.error(f"Could not parse weather_info slot: {weather_info_str}. Error: {e}")
                pass
        
        # Temperature-based recommendations with Indian context
        if temperature is not None:
            if temperature < 5:
                recommendations["clothing"].extend([
                    "Heavy winter jacket or down coat",
                    "Thermal underwear and warm layers",
                    "Woolen sweaters and fleece",
                    "Insulated winter boots",
                    "Warm gloves, scarf, and beanie",
                    "Thick wool socks"
                ])
                recommendations["weather_specific"].extend([
                    "Hand and foot warmers",
                    "Lip balm for cold weather",
                    "Moisturizing cream for dry skin"
                ])
                
            elif 5 <= temperature < 15:
                recommendations["clothing"].extend([
                    "Warm jacket or windcheater",
                    "Long-sleeve shirts and sweaters",
                    "Jeans or warm pants",
                    "Closed-toe shoes or boots",
                    "Light jacket for layering"
                ])
                
            elif 15 <= temperature < 25:
                recommendations["clothing"].extend([
                    "Light cardigan or thin jacket",
                    "Mix of cotton t-shirts and long sleeves",
                    "Comfortable jeans or cotton pants",
                    "Sneakers or comfortable walking shoes",
                    "Light sweater for evenings"
                ])
                
            elif 25 <= temperature < 35:
                recommendations["clothing"].extend([
                    "Cotton t-shirts and breathable fabrics",
                    "Shorts, cotton pants, or light dresses",
                    "Comfortable sandals or breathable shoes",
                    "Light cotton shirts for sun protection",
                    "Thin cardigan for air-conditioned places"
                ])
                
            else:  # temperature >= 35 (hot weather)
                recommendations["clothing"].extend([
                    "Lightweight cotton or linen clothing",
                    "Loose-fitting shirts and breathable fabrics",
                    "Cotton shorts and comfortable sandals",
                    "Wide-brimmed hat or cap",
                    "Light-colored clothing to reflect heat"
                ])
                recommendations["weather_specific"].extend([
                    "High SPF sunscreen (30+ recommended)",
                    "Cooling towel or neck wrap",
                    "Extra water bottle and electrolyte drinks",
                    "Portable fan or cooling spray"
                ])
        else:
            # Default recommendations when no weather data available
            recommendations["clothing"].extend([
                "Versatile layers (t-shirts, light sweater, jacket)",
                "Comfortable pants and shorts",
                "Versatile footwear for walking"
            ])
        
        # Weather condition-specific recommendations
        if "rain" in weather_desc or "drizzle" in weather_desc:
            recommendations["weather_specific"].extend([
                "Waterproof rain jacket or poncho",
                "Compact umbrella",
                "Waterproof shoes or boots",
                "Quick-dry clothing and plastic bags for electronics"
            ])
            
        elif "snow" in weather_desc:
            recommendations["weather_specific"].extend([
                "Waterproof snow boots with good grip",
                "Insulated gloves and warm socks",
                "Waterproof outer layer",
                "Warm scarf and thermal wear"
            ])
            
        elif "sun" in weather_desc or "clear" in weather_desc:
            recommendations["weather_specific"].extend([
                "UV protection sunglasses",
                "Broad-spectrum sunscreen",
                "Sun hat or cap with UV protection",
                "Light, long-sleeved shirt for sun protection"
            ])
        
        # Essential travel items
        recommendations["essentials"] = [
            "Valid ID/passport and travel documents",
            "Phone charger and portable power bank",
            "Basic first aid kit with personal medications",
            "Comfortable walking shoes",
            "Travel insurance documents",
            "Emergency contact information"
        ]
        
        # Travel accessories
        recommendations["accessories"] = [
            "Universal travel adapter (for international trips)",
            "Reusable water bottle",
            "Day backpack or travel bag",
            "Travel pillow for long journeys",
            "Entertainment (books, downloaded content)",
            "Camera or smartphone for memories"
        ]
        
        # Format the comprehensive packing message
        packing_message = f"🧳 **Smart Packing Recommendations for {city.title()}**\n\n"
        
        if temperature is not None:
            packing_message += f"*Customized for current weather: {temperature}°C, {weather_desc.title()}*\n\n"
        else:
            packing_message += "*General recommendations (check weather for more specific advice)*\n\n"
        
        # Add each category with emojis and formatting
        category_emojis = {
            "essentials": "🎯",
            "clothing": "👕", 
            "accessories": "🔧",
            "weather_specific": "🌤️"
        }
        
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

class ActionProvideWeatherOptions(Action):
    """Provide weather checking options to guide users"""
    
    def name(self) -> Text:
        return "action_provide_weather_options"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(response="utter_weather_options")
        return []

class ActionProvidePagingOptions(Action):
    """Provide packing options to guide users"""
    
    def name(self) -> Text:
        return "action_provide_packing_options"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(response="utter_packing_options")
        return []

class ValidateTravelInfoForm(FormValidationAction):
    """Custom form validation for travel information with enhanced user guidance"""
    
    def name(self) -> Text:
        return "validate_travel_info_form"
    
    def validate_destination_city(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate destination city input with helpful guidance"""
        
        if not slot_value:
            dispatcher.utter_message(text="🏙️ Please provide a valid city name for your destination.")
            return {"destination_city": None}
        
        city_name = str(slot_value).strip()
        
        if len(city_name) < 2:
            dispatcher.utter_message(text="🔍 Please provide a city name with at least 2 characters.")
            return {"destination_city": None}
        
        # Clean up and format the city name
        city_name = city_name.title()
        
        return {"destination_city": city_name}
    
    def validate_start_date(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate start date input with helpful guidance"""
        
        if not slot_value:
            dispatcher.utter_message(text="📅 Please provide your travel start date (e.g., 'next week', 'December 15th', or '2024-12-15').")
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
        """Validate end date input with helpful guidance"""
        
        if not slot_value:
            dispatcher.utter_message(text="🔙 Please provide your return date or trip duration (e.g., 'same day', 'one week', 'December 20th').")
            return {"end_date": None}
        
        date_str = str(slot_value).strip()
        
        if len(date_str) < 3:
            dispatcher.utter_message(text="🔙 Please provide more details about your return date or trip duration.")
            return {"end_date": None}
        
        return {"end_date": date_str}
