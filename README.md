# Code Compressor

Code Compressor is a Python script that concatenates and processes source code files from your project into a single output file. It's designed to simplify code sharing, facilitate analysis by Large Language Models (LLMs), and create project snapshots by reducing file content based on configurable options.

## Features

- Consolidate multiple source files into one.
- Filter files by extension, directory, patterns, and keywords.
- "Slim down" file content by removing comments, declarations, and empty lines.
- Customizable configuration via a JSON file.

## Setup and Usage

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd CodeCompresser
    ```

2.  **Create Your Configuration File:**
    Copy `config.template.json` to `my_config.json` in the project root:
    ```bash
    cp config.template.json my_config.json
    ```
    Then, open `my_config.json` and adjust the settings to your project's needs. Key configuration options include:
    *   `project_items`: List of directories or files to include.
    *   `base_path_for_relpath`: Base path for generating relative file paths in the output.
    *   `allowed_extensions`: Define which file types to include, now conveniently grouped by language.
    *   `processing_options`: Control what gets removed from file content (e.g., comments, `using` statements).
    *   `excluded_dirs`, `excluded_patterns`: Specify directories and file patterns to ignore.

3.  **Run the Script:**
    Execute the script using Python, pointing to your configuration file:
    ```bash
    python project_concat.py -c my_config.json
    ```

    **Command-Line Options:**
    *   `-c <path_to_config>` or `--config <path_to_config>`: (Required) Specify the path to your JSON configuration file (e.g., `my_config.json`).
    *   `-o <output_directory>` or `--output_dir <output_directory>`: (Optional) Override the default output directory. If not provided, a directory is generated based on the date and config.
    *   `-s` or `--silent`: (Optional) Suppress non-error console output during execution.

## Example Output

The script will create a directory (e.g., `20260125/my_project_export`) and an output file (e.g., `my_project_export_20260125_103000.txt`) containing all processed code.
