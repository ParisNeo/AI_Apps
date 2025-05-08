import os
import json # Ensure json is imported
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re
import logging

# Configure logging (DEBUG level for detailed output, INFO for production)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# To see detailed path checks, change to:
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Configuration ---
SCAN_DIR = "."  # Scan the current directory (project root) for app subfolders
OUTPUT_HTML_FILE = "index.html" # Output file at the project root
TEMPLATE_FILE = "index_template.html" # Template file at the project root

DEFAULT_APP_COLOR = "#3B82F6"
DEFAULT_APP_DESC = "A cool web application."
DEFAULT_IS_DOWNLOAD = False

# List of folders/files to ignore at the root level when searching for apps
IGNORE_LIST = [
    ".git",
    ".github",
    ".vscode",
    "venv",
    "__pycache__",
    "node_modules",
    os.path.basename(__file__),  # The script file itself
    TEMPLATE_FILE,               # The template file
    OUTPUT_HTML_FILE,            # The output file (to avoid re-parsing if it exists)
    "README.md",
    "LICENSE",
    ".gitignore",
    # Add any other specific root files/folders that aren't apps
    # e.g., "docs", "assets" if they are at the root and not apps
]

def format_app_name(folder_name):
    """Converts folder_name to a more readable App Name."""
    name = re.sub(r'[_-]', ' ', folder_name) # Replace _ or - with space
    name = name.title() # Capitalize each word
    return name

def discover_apps(scan_directory):
    """Discovers apps in the given directory, ignoring specified items."""
    discovered_apps = []
    if not os.path.isdir(scan_directory):
        logging.error(f"Scan directory '{scan_directory}' not found.")
        return []

    for item_name in os.listdir(scan_directory):
        # Skip items in the IGNORE_LIST or hidden files/folders
        if item_name in IGNORE_LIST or item_name.startswith('.'):
            logging.debug(f"Ignoring '{item_name}' as per IGNORE_LIST or it's hidden.")
            continue

        item_path = os.path.join(scan_directory, item_name)

        if os.path.isdir(item_path):
            app_folder_name = item_name # This is the potential app's folder name
            index_html_path = os.path.join(item_path, "index.html")
            icon_png_path = os.path.join(item_path, "icon.png")
            manifest_path = os.path.join(item_path, "manifest.json")

            logging.debug(f"Checking app folder: {item_path}")
            logging.debug(f"  Expected index.html: {index_html_path} (Exists: {os.path.exists(index_html_path)})")
            logging.debug(f"  Expected icon.png: {icon_png_path} (Exists: {os.path.exists(icon_png_path)})")

            if os.path.exists(index_html_path) and os.path.exists(icon_png_path):
                app_data = {
                    "name": format_app_name(app_folder_name),
                    # Paths are now relative to the root, e.g., "Audio_mixing_app/index.html"
                    "path": os.path.join(app_folder_name, "index.html").replace("\\", "/"),
                    "icon": os.path.join(app_folder_name, "icon.png").replace("\\", "/"),
                    "desc": DEFAULT_APP_DESC,
                    "color": DEFAULT_APP_COLOR,
                    "isDownload": DEFAULT_IS_DOWNLOAD,
                    "folder_name": app_folder_name
                }

                # Try to load metadata from manifest.json
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f: # Added encoding
                            manifest = json.load(f)
                        app_data["name"] = manifest.get("name", app_data["name"])
                        app_data["desc"] = manifest.get("description", app_data["desc"])
                        app_data["color"] = manifest.get("color", app_data["color"])
                        app_data["isDownload"] = manifest.get("isDownload", app_data["isDownload"])
                        logging.info(f"Loaded manifest for {app_folder_name}")
                    except json.JSONDecodeError:
                        logging.warning(f"Could not parse manifest.json for {app_folder_name}. Using defaults.")
                    except Exception as e:
                        logging.warning(f"Error reading manifest for {app_folder_name}: {e}")
                else:
                    logging.info(f"No manifest.json for {app_folder_name}. Using defaults.")

                discovered_apps.append(app_data)
                logging.info(f"Discovered app: {app_data['name']} in folder '{app_folder_name}'")
            else:
                logging.warning(f"Skipping directory '{app_folder_name}': missing index.html or icon.png based on checks above.")
        else:
            logging.debug(f"Skipping '{item_name}': it's not a directory.")

    discovered_apps.sort(key=lambda x: x['name'])
    return discovered_apps

def generate_html(apps_data, template_filename, output_filepath):
    """Generates the HTML file from a template and app data."""
    template_dir = os.path.dirname(template_filename) or "."
    actual_template_name = os.path.basename(template_filename)

    if not os.path.exists(template_filename):
        logging.error(f"Template file '{template_filename}' not found in '{template_dir}'.")
        return

    env = Environment(
        loader=FileSystemLoader(searchpath=template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    try:
        template = env.get_template(actual_template_name)
    except Exception as e:
        logging.error(f"Error loading template '{actual_template_name}': {e}")
        return


    js_apps_list = []
    for app in apps_data:
        js_app = app.copy()
        js_app['isDownload_js'] = str(js_app['isDownload']).lower()
        # Properly escape description for JavaScript string literal using json.dumps
        js_app['desc_js'] = json.dumps(app['desc'])
        js_apps_list.append(js_app)


    html_content = template.render(apps=js_apps_list)

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logging.info(f"Successfully generated '{output_filepath}'")
    except IOError as e:
        logging.error(f"Could not write to output file '{output_filepath}': {e}")

if __name__ == "__main__":
    logging.info("Starting index.html builder...")
    # Ensure paths are correct if script is not run from project root (though it should be)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scan_path = os.path.join(script_dir, SCAN_DIR) # SCAN_DIR is ".", so effectively script_dir
    template_path = os.path.join(script_dir, TEMPLATE_FILE)
    output_path = os.path.join(script_dir, OUTPUT_HTML_FILE)

    apps_data = discover_apps(scan_path)
    if apps_data:
        generate_html(apps_data, template_path, output_path)
    else:
        logging.warning("No apps found or scan directory missing. HTML not generated.")
    logging.info("Builder finished.")