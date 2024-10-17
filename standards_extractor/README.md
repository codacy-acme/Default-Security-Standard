# Codacy Coding Standard Extractor

This Python script allows you to extract and save coding standards from Codacy, including associated tools and their enabled patterns. It provides a convenient way to backup or review your Codacy coding standards outside of the Codacy platform.

## Features

- List and select active coding standards from a specified Codacy organization
- Extract detailed information about a selected coding standard
- Fetch all tools associated with the coding standard
- Retrieve enabled patterns for each tool
- Save the extracted data in a structured JSON format

## Prerequisites

- Python 3.6+
- Codacy API token
- Codacy organization name

## Installation

1. Clone this repository or download the script.

2. Install the required Python packages:

   ```
   pip install requests tqdm
   ```

3. Set up your Codacy API token as an environment variable:

   ```
   export CODACY_API_TOKEN=your_codacy_api_token_here
   ```

   Replace `your_codacy_api_token_here` with your actual Codacy API token.

## Usage

Run the script from the command line, providing your Codacy organization name as an argument:

```
python codacy_standard_extractor.py --organization your_organization_name
```

Replace `your_organization_name` with the name of your Codacy organization.

The script will:

1. Fetch and display a list of active coding standards for your organization.
2. Prompt you to select a coding standard to extract.
3. Retrieve detailed information about the selected standard, including its tools and patterns.
4. Save the extracted data to a JSON file named after the coding standard (e.g., `your_standard_name_standard.json`).

## Output

The script generates a JSON file containing the following information:

- Coding standard ID, name, and metadata
- List of associated tools (enabled only)
- Enabled patterns for each tool

## Customization

- If you're using a version control system other than GitHub, update the `PROVIDER` variable in the script.
- Modify the `CODACY_API_BASE_URL` if you're using a self-hosted Codacy instance.

## Troubleshooting

- Ensure your Codacy API token has the necessary permissions to access coding standards.
- Check that your organization name is correct and matches the one in Codacy.
- If you encounter API rate limits, you may need to add delays between requests.

