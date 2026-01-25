import os
import fnmatch
import re
import textwrap
import time
import json
import argparse

################################################################################
### 1. SCRIPT LOGIC                                                          ###
# The core logic of the script resides here. It's designed to be generic     #
# and driven by the external configuration file.                             #
################################################################################

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="A tool to concatenate and process source code files into a single output file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-c", "--config",
        required=True,
        help="Path to the JSON configuration file."
    )
    parser.add_argument(
        "-o", "--output_dir",
        required=False,
        help="(Optional) Override the output directory. If not provided, a directory is generated based on the date and config."
    )
    parser.add_argument(
        "-s", "--silent",
        action="store_true",
        help="(Optional) Suppress non-error console output."
    )
    return parser.parse_args()


def load_config(config_path):
    """Loads and validates the JSON configuration file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # --- Validate required keys ---
    required_keys = [
        "project_items", "base_path_for_relpath", "processing_options",
        "excluded_dirs", "excluded_patterns", "allowed_extensions"
    ]
    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required key in config file: '{key}'")

    # --- Convert list to set for efficient lookup ---
    config["excluded_dirs"] = set(config["excluded_dirs"])

    # --- Process allowed_extensions: flatten if grouped by language ---
    extensions_config = config.get("allowed_extensions", {})
    # Check if the first value is a dictionary to determine if it's grouped
    if extensions_config and isinstance(next(iter(extensions_config.values()), None), dict):
        flattened_extensions = {}
        for lang_group in extensions_config.values():
            if isinstance(lang_group, dict):
                flattened_extensions.update(lang_group)
        config['allowed_extensions'] = flattened_extensions
    # If not grouped, it's already a flat dictionary, so no change needed.

    return config


def generate_output_components(config):
    """
    Generates the central components for the output filename and path
    based on the input parameters.
    Returns: (base_name, timestamp_str)
    """
    base_name = "export"
    project_items = config.get("project_items", [])
    if project_items:
        primary_project_item = project_items[0]
        base_path = config.get("base_path_for_relpath")

        if base_path and base_path in primary_project_item:
            relative_part = primary_project_item.replace(base_path, "")
        else:
            relative_part = os.path.basename(primary_project_item)

        if os.path.isfile(primary_project_item):
            relative_part, _ = os.path.splitext(relative_part)

        folder_structure = relative_part.replace("\\", "_").replace("/", "_").strip("_").lower()

        base_name_parts = [folder_structure]
        keywords = config.get("path_keywords", [])
        if keywords:
            sanitized_keywords = [re.sub(r'[\W_]+', '', k).lower() for k in keywords if k]
            if sanitized_keywords:
                keywords_str = "+".join(sanitized_keywords)
                base_name_parts.append(keywords_str)

        base_name = "_".join(part for part in base_name_parts if part)

    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    return base_name, timestamp_str


def process_file_content(content, filepath, config):
    """
    "Slims down" the file content based on the configurable options.
    """
    options = config.get("processing_options", {})
    # Untouched files
    if filepath.endswith((('.html', '.xml', '.csv'))):
        return content

    if options.get("remove_multiline_comments"):
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    if options.get("remove_singleline_comments"):
        content = re.sub(r'(?<!/)//.*', '', content)
    if options.get("summarize_xml_doc_comments"):
        def xml_comment_replacer(match):
            block = match.group(0)
            summary_match = re.search(r'<summary>\s*(.*?)\s*</summary>', block, re.DOTALL)
            if summary_match:
                summary_text = ' '.join(line.strip() for line in summary_match.group(1).split('\n'))
                indentation = re.match(r'^\s*', block).group(0) if re.match(r'^\s*', block) else ''
                return f"{indentation}/// {summary_text}\n"
            return ''
        content = re.sub(r'(^\s*///.*$\n?)+', xml_comment_replacer, content, flags=re.MULTILINE)
    if options.get("remove_debug_blocks"):
        content = re.sub(r'#if DEBUG.*?#endif', '', content, flags=re.DOTALL | re.MULTILINE)
    if options.get("remove_namespace_declarations"):
        def namespace_replacer(match): return textwrap.dedent(match.group(1))
        content = re.sub(r'^\s*\ufeff?\s*namespace\s+[\w\.]+\s*\{([\s\S]*)\}\s*$', namespace_replacer, content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\ufeff?\s*namespace .*?;\s*$\n?', '', content, flags=re.MULTILINE)
    if options.get("remove_using_statements"):
        content = re.sub(r'^\s*\ufeff?\s*using .*?;\s*$\n?', '', content, flags=re.MULTILINE)
    if options.get("remove_import_statements"):
        content = re.sub(r'^\s*import[\s\S]+?from[\s\S]+?[;]?\s*$', '', content, flags=re.MULTILINE)
    if options.get("collapse_multiple_empty_lines"):
        content = re.sub(r'\n\s*\n+', '\n\n', content)

    return content.strip()


def is_allowed_file(filepath, config):
    """
    Decides if a given file meets the processing criteria
    (extension, exclusions, keywords).
    """
    filename = os.path.basename(filepath)
    _, ext = os.path.splitext(filename)

    allowed_ext_map = config.get("allowed_extensions", {})
    # Check if the extension is explicitly enabled in the config map
    if not allowed_ext_map.get(ext.lower()):
        return False

    # Check if the filename is in the excluded patterns
    if any(fnmatch.fnmatch(filename, pattern) for pattern in config.get("excluded_patterns", [])):
        return False
    # If path keywords are specified, check if the path contains any of them
    path_keywords = config.get("path_keywords", [])
    if path_keywords and not any(keyword.lower() in filepath.lower() for keyword in path_keywords):
        return False
    return True


def collect_source_files(root_dir, config):
    """Recursively collects relevant files from a directory."""
    collected_files = []
    excluded_dirs = config.get("excluded_dirs", set())
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out excluded directories in-place
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in excluded_dirs]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if is_allowed_file(filepath, config):
                collected_files.append(filepath)
    return collected_files


def write_combined_file(files, output_path, config, is_silent=False):
    """Writes the content of the specified files into a single output file."""
    base_path = config.get("base_path_for_relpath")
    with open(output_path, "w", encoding="utf-8") as out:
        for filepath in files:
            try:
                rel_path = os.path.relpath(filepath, base_path)
            except ValueError:
                rel_path = filepath  # Fallback if relpath fails (e.g., different drives on Windows)
            out.write(f"\n\n--- FILE: {rel_path} ---\n")
            try:
                with open(filepath, "r", encoding="utf-8", errors='ignore') as f:
                    original_content = f.read()
                    processed_content = process_file_content(original_content, filepath, config)
                    out.write(processed_content)
            except Exception as e:
                error_message = f"[ERROR: Failed to read this file: {e}]\n"
                out.write(error_message)
                if not is_silent:
                    print(f"    - {error_message.strip()}")


################################################################################
### 2. MAIN EXECUTION BLOCK                                                  ###
################################################################################

def main():
    """The main entry point for the script."""
    args = parse_arguments()
    is_silent = args.silent

    try:
        config = load_config(args.config)
    except (FileNotFoundError, KeyError) as e:
        print(f"❌ Configuration Error: {e}")
        return

    # --- Generate output path and filename ---
    base_name, timestamp_str = generate_output_components(config)
    date_folder = timestamp_str.split('_')[0]
    
    if args.output_dir:
        output_directory = args.output_dir
    else:
        sub_folder = base_name
        output_directory = os.path.join(date_folder, sub_folder)

    final_filename = f"{base_name}_{timestamp_str}.txt"
    output_file_path = os.path.join(output_directory, final_filename)

    os.makedirs(output_directory, exist_ok=True)

    if not is_silent:
        print("🚀 Starting script with the following settings:")
        print(f"  - Output file: {output_file_path}")
        print(f"  - Items to process: {len(config.get('project_items', []))}")
        if config.get("path_keywords"):
            print(f"  - Active path keywords: {', '.join(config.get('path_keywords'))}")

    all_files = []
    for path_item in config.get("project_items", []):
        if os.path.isdir(path_item):
            if not is_silent:
                print(f"\n🔍 Traversing directory: {path_item}")
            source_files = collect_source_files(path_item, config)
            all_files.extend(source_files)
            if not is_silent:
                print(f"    -> {len(source_files)} relevant files added.")
        elif os.path.isfile(path_item):
            if not is_silent:
                print(f"\n➕ Analyzing single file: {path_item}")
            if is_allowed_file(path_item, config):
                all_files.append(path_item)
                if not is_silent:
                    print("    -> File added.")
            else:
                if not is_silent:
                    print("    -> File skipped (does not match filtering criteria).")
        else:
            if not is_silent:
                print(f"\n⚠️ Warning: Path does not exist or is invalid: {path_item}")

    unique_files = sorted(list(set(all_files)))

    if not unique_files:
        if not is_silent:
            print("\n❌ No files found matching the criteria.")
        return

    if not is_silent:
        print(f"\n✅ Total of {len(unique_files)} unique files collected.")
        print("✍️  Processing and writing to output file...")

    write_combined_file(unique_files, output_file_path, config, is_silent)

    if not is_silent:
        print(f"\n🎯 Done! Exported file available at: {output_file_path}")


if __name__ == "__main__":
    main()
