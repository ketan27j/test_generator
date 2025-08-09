from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# This will download the matching version automatically
service = Service(ChromeDriverManager(version="138.0.7204.183").install())
driver = webdriver.Chrome(service=service)