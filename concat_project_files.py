import os
import fnmatch
import re
import textwrap
import time

################################################################################
### 1. KONFIGURÁCIÓS SZEKCIÓ                                                 ###
# Minden, amit módosítanod kell, ezen a területen található.                #
################################################################################

# --- Alapbeállítások ---
# Add meg azokat a gyökérkönyvtárakat, amiket a szkriptnek be kell járnia.
PROJECT_DIRS = [
    "S:\\Programozas\\Egyeb\\Munkahely\\kep-sc\\Source\\JavaServer",
    "S:\\Programozas\\Egyeb\\Munkahely\\kep-sc\\Source\\JavaServer\\reporting\\target\\site\\jacoco",
]

# Viszonyítási alap a relatív útvonalakhoz és a kimeneti fájlnévhez.
# Általában a projektjeidet tartalmazó közös szülőmappa.
BASE_PATH_FOR_RELPATH = "S:\\Programozas\\Egyeb\\Munkahely\\"

# Szűrési kulcsszavak az útvonalakra. Csak azok a fájlok kerülnek be,
# amelyek teljes útvonala tartalmazza valamelyik kulcsszót.
# Hagyd üresen ([]) a szűrés kikapcsolásához.
PATH_KEYWORDS = []  # pl. ["service", "controller"]

# --- Feldolgozási Opciók ---
# Itt szabályozhatod, hogy a szkript melyik "karcsúsító" lépést hajtsa végre.
# Állítsd 'False'-ra, ha egy lépést ki akarsz hagyni.
# A .html, .xml, .csv fájlokat a szkript automatikusan érintetlenül hagyja.
PROCESSING_OPTIONS = {
    "remove_multiline_comments": True,  # Eltávolítja a /* ... */ kommenteket
    "remove_singleline_comments": True,  # Eltávolítja a // kommenteket (a /// XML doksit nem)
    "summarize_xml_doc_comments": True,  # A /// kommenteket egy soros összefoglalóvá alakítja
    "remove_debug_blocks": True,  # Eltávolítja a #if DEBUG ... #endif blokkokat (C#)
    "remove_namespace_declarations": True,  # Eltávolítja a 'namespace ...' sorokat/blokkokat (C#)
    "remove_using_statements": True,  # Eltávolítja a 'using ...;' sorokat (C#)
    "remove_import_statements": True,  # Eltávolítja az 'import ...' sorokat (JS/TS)
    "collapse_multiple_empty_lines": True,  # Több üres sort egyre cserél
}

# --- Szűrési Szabályok ---
# Könyvtárak, amiket a bejárás során teljesen figyelmen kívül hagyunk.
EXCLUDED_DIRS = {
    # Generated
    "node_modules", "dist", "coverage", "target", "build", ".git", ".idea", ".vscode", ".gradle", ".mvn", "__pycache__",
    "bin", "obj", ".vs", ".nuke",  # .NET specifikus kizárások

    # Ignored real code
    # "Test", "Tests", "UnitTest", "UnitTests", "E2ETests",
    # "Common.Logic", "Common.Logic.UnitTests", "Common.Pdf", "Common.UnitTest",
    # "ClientApp", "helm", "Docker", "Appsetting.Development",
}

# Kizárt fájlnevek vagy minták
EXCLUDED_PATTERNS = [
    # Generated
    "package-lock.json", "*.class", "*.iml", "*.log", "*.jar", "*.war",

    # Ignored real code
    # "*.user", "*.suo", "*.md",
    # "*.Test.csproj", "*.UnitTest.csproj", "*.Tests.csproj", "*.csproj", "*.sln", "*.spec.ts",
    # "*.json", "*.yaml", "*.yml", ".env", ".gitignore", ".gitattributes",
    # "*.cmd", "*.sh", "*.bat", "*.ps1", "*.sql",
    # "I*.cs",
]

# Csak ezekkel a kiterjesztésekkel engedélyezünk fájlokat
ALLOWED_EXTENSIONS = {
    # Webfejlesztési fájlok
    ".ts", ".tsx", ".js", ".html",
    # ".scss", ".css",

    # Java specifikus (meghagyva az eredetiből)
    ".java", ".xml", ".properties",

    # .NET és C# specifikus kiterjesztések
    ".cs", ".csproj", ".sln", ".cshtml", ".razor", ".config",

    # Konfiguráció és dokumentáció
    ".yml", ".yaml", ".md", ".txt", ".env", ".sh",

    # Adatok
    ".json",
}


################################################################################
### 2. SZKRIPT LOGIKA                                                        ###
# Innentől kezdve általában nem szükséges módosítani.                       #
################################################################################

def generate_output_filename(project_dirs, base_path, keywords):
    """
    Generál egy egyedi és informatív fájlnevet a bemeneti paraméterek alapján.
    """
    if not project_dirs:
        return f"export_{time.strftime('%Y%m%d_%H%M%S')}.txt"

    primary_project_dir = project_dirs[0]

    if base_path and base_path in primary_project_dir:
        relative_part = primary_project_dir.replace(base_path, "")
    else:
        relative_part = os.path.basename(primary_project_dir)

    folder_structure = relative_part.replace("\\", "_").replace("/", "_").lower()

    filename_parts = [folder_structure]
    if keywords:
        sanitized_keywords = [re.sub(r'[\W_]+', '', k).lower() for k in keywords if k]
        if sanitized_keywords:
            keywords_str = "+".join(sanitized_keywords)
            filename_parts.append(keywords_str)

    filename_parts.append(time.strftime("%Y%m%d_%H%M%S"))
    return "_".join(part for part in filename_parts if part) + ".txt"


# A kimeneti fájlnév meghatározása a konfiguráció alapján
OUTPUT_FILE = generate_output_filename(PROJECT_DIRS, BASE_PATH_FOR_RELPATH, PATH_KEYWORDS)


def process_file_content(content, options, filepath):
    """
    A fájl tartalmát "karcsúsítja" a konfigurálható opciók alapján.
    """
    if filepath.endswith(('.html', '.xml', '.csv')):
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

        content = re.sub(r'^\s*\ufeff?\s*namespace\s+[\w\.]+\s*\{([\s\S]*)\}\s*$', namespace_replacer, content,
                         flags=re.MULTILINE)
        content = re.sub(r'^\s*\ufeff?\s*namespace .*;\s*$\n?', '', content, flags=re.MULTILINE)
    if options.get("remove_using_statements"):
        content = re.sub(r'^\s*\ufeff?\s*using .*;\s*$\n?', '', content, flags=re.MULTILINE)
    if options.get("remove_import_statements"):
        content = re.sub(r'^\s*import[\s\S]+?from[\s\S]+?[;]?\s*$', '', content, flags=re.MULTILINE)
    if options.get("collapse_multiple_empty_lines"):
        content = re.sub(r'\n\s*\n+', '\n\n', content)

    return content.strip()


def is_excluded_file(filename):
    return any(fnmatch.fnmatch(filename, pattern) for pattern in EXCLUDED_PATTERNS)


def is_allowed_file(filepath):
    filename = os.path.basename(filepath)
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False
    if is_excluded_file(filename):
        return False
    if PATH_KEYWORDS and not any(keyword.lower() in filepath.lower() for keyword in PATH_KEYWORDS):
        return False
    return True


def collect_source_files(root_dir):
    collected_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in EXCLUDED_DIRS]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if is_allowed_file(filepath):
                collected_files.append(filepath)
    return collected_files


def write_combined_file(files, output_path, base_path):
    with open(output_path, "w", encoding="utf-8") as out:
        for filepath in files:
            try:
                rel_path = os.path.relpath(filepath, base_path)
            except ValueError:
                rel_path = filepath
            out.write(f"\n\n--- FILE: {rel_path} ---\n\n")
            try:
                with open(filepath, "r", encoding="utf-8", errors='ignore') as f:
                    original_content = f.read()
                    processed_content = process_file_content(original_content, PROCESSING_OPTIONS, filepath)
                    out.write(processed_content)
            except Exception as e:
                out.write(f"[HIBA: Nem sikerült beolvasni ezt a fájlt: {e}]\n")


def main():
    all_files = []
    print("🚀 Szkript indítása a következő beállításokkal:")
    print(f"  Kimeneti fájl: {OUTPUT_FILE}")
    print(f"  Bejárandó könyvtárak: {len(PROJECT_DIRS)} db")
    if PATH_KEYWORDS:
        print(f"  Aktív útvonal szűrő! Kulcsszavak: {', '.join(PATH_KEYWORDS)}")

    for project_dir in PROJECT_DIRS:
        print(f"\n🔍 Könyvtár bejárása: {project_dir}")
        source_files = collect_source_files(project_dir)
        all_files.extend(source_files)
        print(f"    -> {len(source_files)} releváns fájl hozzáadva.")

    unique_files = sorted(list(set(all_files)))

    if not unique_files:
        print("\n❌ Nem található a szűrési feltételeknek megfelelő fájl.")
        return

    print(f"\n✅ Összesen {len(unique_files)} egyedi fájl összegyűjtve.")
    print("✍️  Feldolgozás és írás...")
    write_combined_file(unique_files, OUTPUT_FILE, BASE_PATH_FOR_RELPATH)
    print("🎯 Kész! A testreszabott export fájl feltölthető az LLM-nek!")


if __name__ == "__main__":
    main()