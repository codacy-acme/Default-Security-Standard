import requests
import json
import os
import argparse
import time
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
        except requests.exceptions.HTTPError as e:
            print(f"Error updating tool: {e}")

    try:
        print("Promoting coding standard to active")
        promote_coding_standard(organization, coding_standard_id)
    except requests.exceptions.HTTPError as e:
        print(f"Error promoting coding standard: {e}")
    
    return standard

def list_organization_repositories(organization: str, cursor: str = None) -> Dict:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/repositories"
    params = {"limit": 100}
    if cursor:
        params["cursor"] = cursor
    
    response = requests.get(url, headers=get_codacy_headers(), params=params)
    response.raise_for_status()
    return response.json()

def apply_coding_standard_to_repositories(organization: str, coding_standard_id: str, repositories: List[str], max_retries: int = 3) -> Dict:
    url = f"{CODACY_API_BASE_URL}/organizations/{PROVIDER}/{organization}/coding-standards/{coding_standard_id}/repositories"
    data = {
        "link": repositories,
        "unlink": []  # Include an empty unlink list
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.patch(url, headers=get_codacy_headers(), json=data)
            response.raise_for_status()
            return {"success": True, "response": response.json()}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                # Capture the response content for 400 errors
                error_content = e.response.text
                return {"success": False, "error": str(e), "status_code": e.response.status_code, "error_content": error_content}
            if attempt == max_retries - 1:
                return {"success": False, "error": str(e), "status_code": e.response.status_code}
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return {"success": False, "error": "Max retries reached"}

def apply_coding_standard_to_all_repositories(organization: str, coding_standard_id: str, batch_size: int = 75):
    all_repositories = []
    cursor = None
    
    while True:
        repo_data = list_organization_repositories(organization, cursor)
        repositories = repo_data.get('data', [])
        all_repositories.extend([repo['name'] for repo in repositories])
        
        pagination_info = repo_data.get('pagination')
        if not pagination_info or not pagination_info.get('cursor'):
            break
        cursor = pagination_info['cursor']
    
    total_repos = len(all_repositories)
    print(f"Applying coding standard to {total_repos} repositories in batches of {batch_size}")
    
    results = {"successful": [], "failed": []}
    for i in tqdm(range(0, total_repos, batch_size), desc="Processing batches"):
        batch = all_repositories[i:i+batch_size]
        result = apply_coding_standard_to_repositories(organization, coding_standard_id, batch)
        if result["success"]:
            results["successful"].extend(batch)
        else:
            error_msg = f"Error applying to batch {i//batch_size + 1}: {result['error']}"
            if 'error_content' in result:
                error_msg += f"\nError content: {result['error_content']}"
            print(error_msg)
            results["failed"].extend([{
                "repo": repo,
                "error": result['error'],
                "status_code": result.get('status_code'),
                "error_content": result.get('error_content')
            } for repo in batch])
        time.sleep(1)  # Add a delay between batches to avoid rate limiting
    
    print(f"Finished applying coding standard to all repositories")
    print(f"Successful: {len(results['successful'])}, Failed: {len(results['failed'])}")
    return results

def main():
    parser = argparse.ArgumentParser(description="Comprehensive Coding Standard Management Script")
    parser.add_argument("--organization", required=True, help="Codacy organization name")
    parser.add_argument("--name", required=True, help="Name for the new coding standard")
    parser.add_argument("--config", required=True, help="Path to JSON configuration file")
    parser.add_argument("--batch-size", type=int, default=75, help="Number of repositories to process in each batch")
    
    args = parser.parse_args()

    if not CODACY_API_TOKEN:
        raise ValueError("CODACY_API_TOKEN environment variable is not set")

    try:
        result = process_coding_standard(args.organization, args.name, args.config)
        coding_standard_id = result['data']['id']
        
        apply_results = apply_coding_standard_to_all_repositories(args.organization, coding_standard_id, args.batch_size)
        
        output_filename = f"{args.name.replace(' ', '_').lower()}_result.json"
        save_json_file({"standard_creation": result, "apply_to_repositories": apply_results}, output_filename)
        print(f"Final result saved to {output_filename}")
        print("Coding standard creation, update, promotion, and application to repositories completed.")
        print(f"Successfully applied to {len(apply_results['successful'])} repositories.")
        print(f"Failed to apply to {len(apply_results['failed'])} repositories.")
        
        if apply_results['failed']:
            print("\nFailed repositories:")
            for failed_repo in apply_results['failed']:
                print(f"  - {failed_repo['repo']}: Error {failed_repo.get('status_code', 'N/A')} - {failed_repo['error']}")
                if 'error_content' in failed_repo:
                    print(f"    Error content: {failed_repo['error_content']}")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()