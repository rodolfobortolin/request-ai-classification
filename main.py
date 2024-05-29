import requests
from requests.auth import HTTPBasicAuth
import logging
import os
import csv
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Import configurations
#from config import cloud
#from config import OPENAI_API_KEY, ORG

cloud = {
    "username" :  "",
    "token" : "",
    "base_URL" : ""
}

OPENAI_API_KEY = ""

BASE_URL = cloud['base_URL']


def process_catalog(writer):
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
  
    summary = "I need new internet access for my guest."
    description = ""

    request_1 = f"I will need to know based on this list of Request Types and Request Type Description which one would you chose in order to open a ticket in this Jira Service Management Portal. This are the Request Types and Request Type Description that you will need to check: {writer}"

    try:
        response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            { "role": "system", "content": "You are an assistent that knows how to classify information for Service Desk Portals" },
            { "role": "user", "content": request_1},
            { "role": "assistant", "content": "Ok" },
            { "role": "user", "content": f"I need to know based on this summary: {summary} and this descrition: {description} what Request Type would you chose. \n Asnwer me using this format: Request Type [Request Type] with Description [Request Type Description] Proposed new Summary for this issue in Jira: [the proposed summary]"}
        ],
        temperature=0, 
        max_tokens=150,
        top_p=1, 
        frequency_penalty=0,
        presence_penalty=0 
        )

        response = response.choices[0].message.content
        return response

    except Exception as e:
        logging.info(f"An error occurred: {e}")
        return []
    
def fetch_service_catalog():
    project_start = 0
    service_catalog = []

    while True:
        # Fetch projects
        project_response = requests.get(
            f'{BASE_URL}/rest/servicedeskapi/servicedesk?start={project_start}',
            auth=HTTPBasicAuth(cloud['username'], cloud['token']),
            headers={"Accept": "application/json"}
        )

        if project_response.status_code != 200:
            logging.error("Failed to fetch projects")
            break

        json_projects = project_response.json()

        for json_project in json_projects["values"]:
            request_type_start = 0
            while True:
                # Fetch request types for the project
                request_type_response = requests.get(
                    f'{BASE_URL}/rest/servicedeskapi/servicedesk/{json_project["id"]}/requesttype?start={request_type_start}',
                    auth=HTTPBasicAuth(cloud['username'], cloud['token']),
                    headers={"Accept": "application/json"}
                )

                if request_type_response.status_code != 200:
                    logging.error(f"Failed to fetch request types for project {json_project['id']}")
                    break

                json_request_types = request_type_response.json()

                for json_request_type in json_request_types["values"]:
                    service_catalog.append({
                        "Request Type": json_request_type["name"],
                        "Request Type Description": json_request_type.get("description", "")
                    })

                if json_request_types["isLastPage"]:
                    break
                else:
                    request_type_start += 50

        if json_projects["isLastPage"]:
            break
        else:
            project_start += 50

    # Save data to a CSV file
    csv_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Service Catalog.csv')
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Request Type", "Request Type Description"])
        writer.writeheader()
        for item in service_catalog:
            writer.writerow(item)

    logging.info("Service catalog saved successfully in CSV format.")
    return csv_file_path

def get_csv_content_as_text(csv_file_path):
    """Reads the content of the CSV file as text."""
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return None

# Execute the fetch and then read the CSV content
csv_path = fetch_service_catalog()
csv_content = get_csv_content_as_text(csv_path)
if csv_content:
    logging.info("CSV content successfully retrieved.")
    response = process_catalog(csv_content)
    logging.info(response)
else:
    logging.error("Failed to retrieve CSV content.")
