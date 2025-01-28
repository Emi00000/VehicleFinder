from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urljoin
import pandas as pd
import re
import os
from django.conf import settings
from django.conf.urls.static import static
import openpyxl
# Create your views here.
def home_view(request):
    return render(request, "home.html")

chat_state = {
    "current_question": None,
    "questions": [
        "What is the Make of the car you are looking for?",
        "What is the Model of the car?",
        "What is the lowest Engine Power (in hp)?",
        "What is the highest Engine Power (in hp)?",
        "What is the Fuel Type (e.g., petrol, diesel)?",
        "What is the Cylindric Capacity (in cc)?",
        "What is the Color of the car?",
        "What is the Traction type (e.g., FWD, RWD, AWD)?",
        "What is the lowest Price?",
        "What is the highest Price?"
    ],
    "responses": {},
    "retry_count": 0,
    "specific_question": False,
    "current_attribute": None,
    "site_question_asked": False,
    "default_sites": ["https://example.com", "https://carsite.com", "https://autotrader.com"]
}

@csrf_exempt
def chat_view(request):
    global chat_state

    if request.method == "POST":
        user_input = json.loads(request.body).get("message", "").strip()

        # Handle "end chat"
        if user_input.lower() == "end chat":
            chat_state.update({
                "current_question": None,
                "questions": [
                    "What is the Make of the car you are looking for?",
                    "What is the Model of the car?",
                    "What is the lowest Engine Power (in hp)?",
                    "What is the highest Engine Power (in hp)?",
                    "What is the Fuel Type (e.g., petrol, diesel)?",
                    "What is the Cylindric Capacity (in cc)?",
                    "What is the Color of the car?",
                    "What is the Traction type (e.g., FWD, RWD, AWD)?",
                    "What is the lowest Price?",
                    "What is the highest Price?"
                ],
                "responses": {},
                "retry_count": 0,
                "specific_question": False,
                "current_attribute": None,
                "site_question_asked": False
            })
            return JsonResponse({"bot_response": "Sorry to see you go. Feel free to restart the process anytime!"})

        # Handle current question initialization
        if chat_state["current_question"] is None and chat_state["questions"]:
            chat_state["current_question"] = chat_state["questions"].pop(0)
            return JsonResponse({"bot_response": chat_state["current_question"]})

        # Handle responses to specific questions
        if chat_state["specific_question"]:
            valid_attributes = ["Make", "Model", "Engine Power", "Price", "Fuel Type", "Cylindric Capacity", "Color", "Traction"]
            if user_input not in valid_attributes:
                return JsonResponse({"bot_response": "Invalid attribute. Please choose one of the following: Make, Model, Engine Power, Price, Fuel Type, Cylindric Capacity, Color, Traction."})
            chat_state["current_attribute"] = user_input
            chat_state["specific_question"] = False
            return JsonResponse({"bot_response": f"Please provide the value for {user_input}."})

        # Handle attribute value input
        if chat_state["current_attribute"]:
            if chat_state["current_attribute"] in ["Make", "Model", "Fuel Type", "Color", "Traction"]:
                if not user_input.isalpha():
                    chat_state["retry_count"] += 1
                    if chat_state["retry_count"] >= 3:
                        chat_state["retry_count"] = 0
                        chat_state["specific_question"] = True
                        return JsonResponse({"bot_response": "Too many invalid attempts. Let's go back. Which specific attribute would you like to specify?"})
                    return JsonResponse({"bot_response": f"Invalid input for {chat_state['current_attribute']}. Please try again."})
            elif chat_state["current_attribute"] in ["Engine Power", "Price", "Cylindric Capacity"]:
                if not user_input.replace('.', '', 1).isdigit():
                    chat_state["retry_count"] += 1
                    if chat_state["retry_count"] >= 3:
                        chat_state["retry_count"] = 0
                        chat_state["specific_question"] = True
                        return JsonResponse({"bot_response": "Too many invalid attempts. Let's go back. Which specific attribute would you like to specify?"})
                    return JsonResponse({"bot_response": f"Invalid input for {chat_state['current_attribute']}. Please try again."})

            # Valid attribute input
            chat_state["responses"][chat_state["current_attribute"]] = user_input
            chat_state["current_attribute"] = None
            return JsonResponse({"bot_response": "Thank you. Would you like to provide your own websites for the search? (yes/no)"})

        # Handle general question responses
        if chat_state["current_question"]:
            if chat_state["current_question"] in ["What is the Make of the car you are looking for?",
                                                  "What is the Model of the car?",
                                                  "What is the Fuel Type (e.g., petrol, diesel)?",
                                                  "What is the Color of the car?",
                                                  "What is the Traction type (e.g., FWD, RWD, AWD)?"]:
                if not user_input.isalpha():
                    chat_state["retry_count"] += 1
                    return JsonResponse({"bot_response": "Invalid input. Please enter a valid text or leave it blank."})

            if chat_state["current_question"] in ["What is the lowest Engine Power (in hp)?",
                                                  "What is the highest Engine Power (in hp)?",
                                                  "What is the lowest Price?",
                                                  "What is the highest Price?",
                                                  "What is the Cylindric Capacity (in cc)?"]:
                if not user_input.replace('.', '', 1).isdigit():
                    chat_state["retry_count"] += 1
                    return JsonResponse({"bot_response": "Invalid input. Please enter a valid number or leave it blank."})

            # Valid input handling
            chat_state["responses"][chat_state["current_question"]] = user_input
            chat_state["retry_count"] = 0
            if chat_state["questions"]:
                chat_state["current_question"] = chat_state["questions"].pop(0)
                return JsonResponse({"bot_response": chat_state["current_question"]})
            else:
                chat_state["current_question"] = None
                return JsonResponse({"bot_response": "Would you like to provide your own websites for the search? (yes/no)"})


        if not chat_state["site_question_asked"]:
            if user_input.lower() in ["yes", "no"]:
                chat_state["site_question_asked"] = True if user_input.lower() == "yes" else False
                if chat_state["site_question_asked"]:
                    return JsonResponse({"bot_response": "Please provide the websites (comma-separated, starting with https://)."})
                return JsonResponse({
                    "bot_response": f"Search will be conducted on default sites: {', '.join(chat_state['default_sites'])}. Thank you! Your search will begin shortly!"
                })
            return JsonResponse({"bot_response": "Invalid response. Please answer 'yes' or 'no'."})

        # Handle website URLs
        if chat_state["site_question_asked"]:
            urls = user_input.split(",")
            valid_urls = [url.strip() for url in urls if url.strip().startswith("https://")]
            invalid_urls = [url for url in urls if not url.strip().startswith("https://")]

            if invalid_urls:
                chat_state["retry_count"] += 1
                if chat_state["retry_count"] >= 3:
                    chat_state["retry_count"] = 0
                    chat_state["site_question_asked"] = False
                    return JsonResponse({"bot_response": "Too many invalid attempts. Would you like to provide your own websites for the search? (yes/no)"})
                return JsonResponse({"bot_response": f"Invalid URLs detected: {', '.join(invalid_urls)}. Please provide valid HTTPS URLs."})

            chat_state["responses"]["websites"] = valid_urls
            chat_state["retry_count"] = 0
            return JsonResponse({"bot_response": "Thank you. Your search will begin shortly!"})

    elif request.method == "GET":
        return render(request, "chat.html")

    return JsonResponse({"bot_response": "Please provide a valid response or type 'end chat' to finish."})
def init_webdriver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=Service(), options=options)

# Detect if site is dynamic or static
def is_dynamic_site(url):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        if not soup.find() or "javascript" in response.text.lower():
            return True
        return False
    except Exception:
        return False

# Handle HTTP flags
def handle_http_flags(response, url):
    if 200 <= response.status_code < 300:
        return response
    elif 300 <= response.status_code < 400:
        if "Location" in response.headers:
            new_url = urljoin(url, response.headers["Location"])
            print(f"Redirected to {new_url}")
            return requests.get(new_url, timeout=10)
        else:
            print(f"Redirection with no Location header for {url}")
            return None
    elif 400 <= response.status_code < 500:
        print(f"Client error {response.status_code} for {url}")
        return None
    elif response.status_code >= 500:
        print(f"Server error {response.status_code} for {url}")
        return None
    return None

# Determine if a page describes a car
def is_car_page(url):
    keywords = ["cardetails", "car-details", "automobile-details", "vehicle-info", "car-specs"]
    return any(keyword in url.lower() for keyword in keywords)

# Extract specifics from HTML
def extract_specifics(soup, criteria):
    specifics = {}
    for keyword in criteria:
        # Search HTML tags and their attributes
        for tag in soup.find_all(True):
            for attr, value in tag.attrs.items():
                if keyword.lower() in str(value).lower():
                    # Check text within tag or its children
                    value_text = tag.get_text(strip=True)
                    if value_text:
                        specifics[keyword] = value_text
                        break
            if keyword in specifics:
                break

        # Search text directly between tags if not found in attributes
        if keyword not in specifics:
            for element in soup.find_all(string=re.compile(fr"\b{keyword}\b", re.IGNORECASE)):
                parent = element.find_parent()
                if parent:
                    value_text = parent.find_next_sibling() or parent.find_next()
                    if value_text:
                        specifics[keyword] = value_text.get_text(strip=True)
                        break
    return specifics

# Memorize cars with all specifics
def memorize_car(url, specifics):
    print(f"Memorized car at {url} with specifics: {specifics}")

def crawl_and_scrape(url, criteria, visited=None):
    if visited is None:
        visited = set()
    if url in visited or not url.startswith("https://"):
        return []
    visited.add(url)

    print(f"Scraping {url}")
    try:
        # Determine if the site is dynamic or static
        if is_dynamic_site(url):
            driver = init_webdriver()
            driver.get(url)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            driver.quit()
        else:
            response = requests.get(url, timeout=10)
            response = handle_http_flags(response, url)
            if not response:
                return []
            soup = BeautifulSoup(response.text, "html.parser")

        # Check if the current page showcases a car
        if is_car_page(url):
            specifics = extract_specifics(soup, criteria)
            if all(criteria.get(key, None) == specifics.get(key, None) for key in criteria):
                memorize_car(url, specifics)
        else:
            # Crawl only links containing car-related keywords
            car_keywords = ["car", "cars", "automobile", "vehicle", "vehicles", "automobiles"]
            links = [urljoin(url, a.get("href")) for a in soup.find_all("a", href=True)]
            filtered_links = [link for link in links if any(keyword in link.lower() for keyword in car_keywords)]

            for link in filtered_links:
                crawl_and_scrape(link, criteria, visited)
    except Exception as e:
        print(f"Error scraping {url}: {e}")


# Main scraping function
def scrape_websites(websites, criteria):
    for site in websites:
        crawl_and_scrape(site, criteria)

# Export to Excel
def export_to_excel(data, filename="car_results.xlsx"):
    # Ensure the file is saved in a directory accessible for downloads
    output_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)

    # Save the data to Excel
    df = pd.DataFrame(data, columns=["Car Information"])
    df.to_excel(file_path, index=False)
    print(f"Data exported to {file_path}")

    return file_path  # Return the path for serving the file

def scraping_view(request):
    if request.method == "POST":
        try:
            user_criteria = chat_state["responses"]

            # Ensure criteria_values are strings and lowercase them
            criteria_values = {
                key: (value.lower() if isinstance(value, str) else value)
                for key, value in user_criteria.items() if value
            }

            provided_websites = user_criteria.get("websites", [])
            if isinstance(provided_websites, list):
                provided_websites = [url.strip() for url in provided_websites if url.strip().startswith("https://")]
            else:
                provided_websites = []

            websites = provided_websites if provided_websites else chat_state["default_sites"]
            print("Using websites for scraping:", websites)

            if not websites:
                return JsonResponse({"error": "No valid websites provided or available for scraping."})

            # Perform the scraping
            results = scrape_websites(websites, criteria_values)

            # Export results to Excel
            file_path = export_to_excel(results)
            relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
            download_url = f"{settings.MEDIA_URL}exports/{os.path.basename(file_path)}"

            return JsonResponse({"message": "Scraping completed successfully!", "download_url": download_url})
        except Exception as e:
            print(f"Error during scraping: {e}")
            return JsonResponse({"error": "An error occurred while scraping. Please try again later."})
    return JsonResponse({"error": "Invalid request method."})
