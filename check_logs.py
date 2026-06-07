from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

options = Options()
options.add_argument('--headless')
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

driver = webdriver.Chrome(options=options)
driver.get("http://localhost:5000") # or whatever the flask port is

# Wait for page to load
import time
time.sleep(2)

for entry in driver.get_log('browser'):
    print(entry)

driver.quit()
