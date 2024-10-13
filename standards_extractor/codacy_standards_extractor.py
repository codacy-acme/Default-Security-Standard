import requests
import json
import os
import argparse
from typing import List, Dict
from tqdm import tqdm

# Codacy API configuration
CODACY_API_TOKEN = os.environ.get("CODACY_API_TOKEN")
CODACY_API_BASE_URL = "https://app.codacy.com/api/v3"
PROVIDER = "gh"  # Assuming GitHub, change if different

def get_codacy_headers() -> Dict[str, str]:
    return {
        "api-token": CODACY_API_TOKEN,
        "Accept": "application/json"
    }

def get_coding_standards(organization: str) -> List[Dict]:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    all_standards = response.json()['data']
    
    # Filter out draft standards
    active_standards = [standard for standard in all_standards if not standard.get('isDraft', False)]
    return active_standards

def select_coding_standard(coding_standards: List[Dict]) -> Dict:
    print("\nAvailable coding standards:")
    for i, standard in enumerate(coding_standards, 1):
        print(f"{i}. {standard['name']}")
    
    while True:
        try:
            selection = int(input("\nEnter the number of the coding standard you want to extract: "))
            if 1 <= selection <= len(coding_standards):
                return coding_standards[selection - 1]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def get_coding_standard_details(organization: str, coding_standard_id: str) -> Dict:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    return response.json()['data']

def get_coding_standard_tools(organization: str, coding_standard_id: str) -> List[Dict]:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    return response.json()['data']

def get_tool_patterns(organization: str, coding_standard_id: str, tool_uuid: str) -> List[Dict]:
    patterns = []
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools/{tool_uuid}/patterns"
    
    while url:
        response = requests.get(url, headers=get_codacy_headers())
        response.raise_for_status()
        data = response.json()
        patterns.extend(data['data'])
        url = data.get('pagination', {}).get('next')
    
    return patterns

def save_coding_standard(standard: Dict, tools: List[Dict], filename: str):
    output = {
        "id": standard['id'],
        "name": standard['name'],
        "isDraft": standard['isDraft'],
        "isDefault": standard['isDefault'],
        "languages": standard['languages'],
        "meta": standard['meta'],
        "tools": [
            {
                "codingStandardId": tool['codingStandardId'],
                "uuid": tool['uuid'],
                "isEnabled": tool['isEnabled'],
                "patterns": [
                    pattern for pattern in tool['patterns']
                    if pattern.get('enabled', False)
                ]
            }
            for tool in tools
            if tool.get('isEnabled', False)
        ]
    }
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="Extract Codacy coding standards")
    parser.add_argument("--organization", help="Specify the Codacy organization", required=True)
    args = parser.parse_args()

    if not CODACY_API_TOKEN:
        raise ValueError("CODACY_API_TOKEN environment variable is not set")

    try:
        # 1. Get and list active coding standards
        coding_standards = get_coding_standards(args.organization)
        if not coding_standards:
            print(f'No active Coding Standards found for organization {args.organization}')
            return

        # 2. Select a coding standard
        selected_standard = select_coding_standard(coding_standards)
        print(f"\nSelected coding standard: {selected_standard['name']} (ID: {selected_standard['id']})")

        # 3. Get detailed information about the selected coding standard
        detailed_standard = get_coding_standard_details(args.organization, selected_standard['id'])

        # 4. Get tools for the selected coding standard
        tools = get_coding_standard_tools(args.organization, selected_standard['id'])
        
        # 5. For each tool, get its patterns
        for tool in tqdm(tools, desc="Fetching tool patterns"):
            if tool.get('isEnabled', False):
                patterns = get_tool_patterns(args.organization, selected_standard['id'], tool['uuid'])
                tool['patterns'] = patterns
            else:
                tool['patterns'] = []

        # 6. Save the coding standard with tools and patterns
        filename = f"{selected_standard['name'].replace(' ', '_').lower()}_standard.json"
        save_coding_standard(detailed_standard, tools, filename)
        print(f"\nCoding standard with tools and patterns has been saved to {filename}")

    except requests.RequestException as e:
        print(f"Error accessing Codacy API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()