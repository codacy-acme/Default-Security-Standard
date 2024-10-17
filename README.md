# Codacy Standard Manager

This script provides a comprehensive solution for managing coding standards in Codacy. It allows you to create, configure, and promote coding standards programmatically using the Codacy API.

## Features

- Create new coding standards
- List and configure tools for coding standards
- Enable/disable specific patterns for each tool
- Promote coding standards to active status
- Load configuration from JSON files
- Save results to JSON files

## Prerequisites

- Python 3.6+
- `requests` library
- `tqdm` library
- Codacy API token

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/codacy-standard-manager.git
   cd codacy-standard-manager
   ```

2. Install the required dependencies:
   ```
   pip install requests tqdm
   ```

3. Set up your Codacy API token as an environment variable:
   ```
   export CODACY_API_TOKEN=your_api_token_here
   ```

## Usage

Run the script with the following command:

```
python codacy_standard_manager.py --organization <org_name> --name <standard_name> --config <config_file_path>
```

Arguments:
- `--organization`: Your Codacy organization name
- `--name`: Name for the new coding standard
- `--config`: Path to the JSON configuration file

## Configuration File

The configuration file should be in JSON format and contain the following structure:

```json
{
  "languages": ["python", "javascript"],
  "tools": [
    {
      "uuid": "tool-uuid",
      "isEnabled": true,
      "patterns": [
        {
          "patternDefinition": {
            "id": "pattern-id"
          },
          "enabled": true,
          "parameters": {}
        }
      ]
    }
  ]
}
```

## Trivy and Semgrep Recommended Rules

The recommended rules for Trivy and Semgrep are located in the repository under:

```
standards_extractor/trivy-semgrep-recommended_standard.json
```

You can use this file as a starting point for your configuration or incorporate these rules into your custom configuration.

## Output

The script will create a JSON file with the results of the coding standard creation and configuration. The file will be named based on the provided standard name (e.g., `my_new_standard_result.json`).

## Error Handling

The script includes error handling for API requests and will print detailed error messages if any issues occur during execution.

