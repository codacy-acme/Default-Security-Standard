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
        "Accept": "application/json",
        "Content-Type": "application/json"
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
            selection = int(input("\nEnter the number of the coding standard you want to manage: "))
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

def update_coding_standard_tool(organization: str, coding_standard_id: str, tool_uuid: str, enabled: bool, patterns: List[Dict]) -> Dict:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools/{tool_uuid}"
    data = {
        "enabled": enabled,
        "patterns": patterns
    }
    response = requests.patch(url, headers=get_codacy_headers(), json=data)
    response.raise_for_status()
    return response.json()

def compare_and_update_standard(organization: str, current_standard: Dict, original_config: Dict) -> Dict:
    deviations = []
    coding_standard_id = current_standard['id']

    # Compare tools and patterns
    for original_tool in original_config['tools']:
        current_tool = next((tool for tool in current_standard['tools'] if tool['uuid'] == original_tool['uuid']), None)
        
        if not current_tool:
            deviations.append(f"Tool {original_tool['uuid']} is missing")
            continue

        if current_tool['isEnabled'] != original_tool['isEnabled']:
            deviations.append(f"Tool {original_tool['uuid']} enabled status mismatch")

        # Compare patterns
        original_patterns = {p['id']: p for p in original_tool['patterns']}
        current_patterns = {p['id']: p for p in current_tool['patterns']}

        for pattern_id, original_pattern in original_patterns.items():
            if pattern_id not in current_patterns:
                deviations.append(f"Pattern {pattern_id} is missing in tool {original_tool['uuid']}")
            elif current_patterns[pattern_id]['enabled'] != original_pattern['enabled']:
                deviations.append(f"Pattern {pattern_id} in tool {original_tool['uuid']} has different enabled status")

        # Update tool if there are deviations
        if deviations:
            print(f"Updating tool {original_tool['uuid']}...")
            update_coding_standard_tool(
                organization,
                coding_standard_id,
                original_tool['uuid'],
                original_tool['isEnabled'],
                original_tool['patterns']
            )

    return deviations

def load_original_config(filename: str) -> Dict:
    with open(filename, 'r') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="Manage Codacy coding standards")
    parser.add_argument("--organization", help="Specify the Codacy organization", required=True)
    parser.add_argument("--config", help="Path to the original configuration file", required=True)
    args = parser.parse_args()

    if not CODACY_API_TOKEN:
        raise ValueError("CODACY_API_TOKEN environment variable is not set")

    try:
        # Load the original configuration
        original_config = load_original_config(args.config)

        # Get and list active coding standards
        coding_standards = get_coding_standards(args.organization)
        if not coding_standards:
            print(f'No active Coding Standards found for organization {args.organization}')
            return

        # Select a coding standard
        selected_standard = select_coding_standard(coding_standards)
        print(f"\nSelected coding standard: {selected_standard['name']} (ID: {selected_standard['id']})")

        # Get detailed information about the selected coding standard
        detailed_standard = get_coding_standard_details(args.organization, selected_standard['id'])

        # Get tools for the selected coding standard
        tools = get_coding_standard_tools(args.organization, selected_standard['id'])
        
        # For each tool, get its patterns
        for tool in tqdm(tools, desc="Fetching tool patterns"):
            patterns = get_tool_patterns(args.organization, selected_standard['id'], tool['uuid'])
            tool['patterns'] = patterns

        # Add tools to the detailed standard
        detailed_standard['tools'] = tools

        # Compare and update the standard
        deviations = compare_and_update_standard(args.organization, detailed_standard, original_config)

        if deviations:
            print("\nDeviations found and corrected:")
            for deviation in deviations:
                print(f"- {deviation}")
        else:
            print("\nNo deviations found. The coding standard matches the original configuration.")

    except requests.RequestException as e:
        print(f"Error accessing Codacy API: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()