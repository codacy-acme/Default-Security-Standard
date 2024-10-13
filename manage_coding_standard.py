import requests
import json
import os
import argparse
from typing import Dict, List
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

def create_coding_standard(organization: str, name: str, languages: List[str]) -> Dict:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards"
    data = {
        "name": name,
        "languages": languages
    }
    print(f"Creating coding standard with payload: {json.dumps(data, indent=2)}")
    response = requests.post(url, headers=get_codacy_headers(), json=data)
    response.raise_for_status()
    return response.json()

def list_coding_standard_tools(organization: str, coding_standard_id: str) -> List[Dict]:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    return response.json()['data']

def list_tool_patterns(organization: str, coding_standard_id: str, tool_uuid: str) -> List[Dict]:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools/{tool_uuid}/patterns"
    response = requests.get(url, headers=get_codacy_headers())
    response.raise_for_status()
    return response.json()['data']

def update_coding_standard_tool(organization: str, coding_standard_id: str, tool_uuid: str, enabled: bool, patterns: List[Dict] = None) -> Dict:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/tools/{tool_uuid}"
    data = {
        "enabled": enabled,
        "patterns": patterns or []
    }
    print(f"Updating tool with payload: {json.dumps(data, indent=2)}")
    response = requests.patch(url, headers=get_codacy_headers(), json=data)
    print(f"Raw response: {response.text}")
    response.raise_for_status()
    return response.json() if response.text else {}

def promote_coding_standard(organization: str, coding_standard_id: str) -> Dict:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/promote"
    print("Promoting coding standard")
    response = requests.post(url, headers=get_codacy_headers())
    response.raise_for_status()
    return response.json()

def load_config(config_file: str) -> Dict:
    with open(config_file, 'r') as file:
        return json.load(file)

def save_json_file(data: Dict, filename: str):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def process_coding_standard(organization: str, name: str, config_file: str) -> Dict:
    config = load_config(config_file)
    
    languages = config.get('languages', [])
    
    print(f"Creating coding standard: {name}")
    standard = create_coding_standard(organization, name, languages)
    coding_standard_id = standard['data']['id']
    print(f"Coding standard created with ID: {coding_standard_id}")
    
    # List all tools
    tools = list_coding_standard_tools(organization, coding_standard_id)
    
    # Disable all tools and their patterns
    for tool in tqdm(tools, desc="Disabling all tools and patterns"):
        patterns = list_tool_patterns(organization, coding_standard_id, tool['uuid'])
        print(f"Patterns for tool {tool['uuid']}:")
        print(json.dumps(patterns[:2], indent=2))  # Print first two patterns for inspection
        
        disabled_patterns = [
            {
                "id": pattern['patternDefinition']['id'],
                "enabled": False
            } for pattern in patterns if 'patternDefinition' in pattern and 'id' in pattern['patternDefinition']
        ]
        
        update_coding_standard_tool(organization, coding_standard_id, tool['uuid'], False, disabled_patterns)
    
    # Enable and configure specified tools and patterns
    for tool in tqdm(config.get('tools', []), desc="Enabling specified tools and patterns"):
        tool_uuid = tool['uuid']
        
        try:
            print(f"Updating tool: {tool_uuid}")
            patterns = [
                {
                    "id": pattern['patternDefinition']['id'],
                    "enabled": pattern['enabled'],
                    "parameters": pattern['parameters']
                } for pattern in tool['patterns'] if pattern['enabled']
            ]
            update_coding_standard_tool(organization, coding_standard_id, tool_uuid, tool['isEnabled'], patterns)
        except requests.RequestException as e:
            print(f"Error updating tool: {e}")

    try:
        print("Promoting coding standard to active")
        promote_coding_standard(organization, coding_standard_id)
    except requests.RequestException as e:
        print(f"Error promoting coding standard: {e}")
    
    return standard

def main():
    parser = argparse.ArgumentParser(description="Comprehensive Coding Standard Management Script")
    parser.add_argument("--organization", required=True, help="Codacy organization name")
    parser.add_argument("--name", required=True, help="Name for the new coding standard")
    parser.add_argument("--config", required=True, help="Path to JSON configuration file")
    
    args = parser.parse_args()

    if not CODACY_API_TOKEN:
        raise ValueError("CODACY_API_TOKEN environment variable is not set")

    try:
        result = process_coding_standard(args.organization, args.name, args.config)
        
        output_filename = f"{args.name.replace(' ', '_').lower()}_result.json"
        save_json_file(result, output_filename)
        print(f"Final result saved to {output_filename}")
        print("Coding standard creation, update, and promotion completed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()