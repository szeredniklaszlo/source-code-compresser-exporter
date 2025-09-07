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
# Add meg azokat a gyökérkönyvtárakat VAGY konkrét fájlokat,
# amiket a szkriptnek fel kell dolgoznia.
PROJECT_ITEMS = [
    r"S:\Programozas\Egyeb\Munkahely\kep-sc\Source\JavaServer\reporting\src",
    #r"S:\Programozas\Egyeb\Munkahely\kep-sc\Source\Server\Modules\Monitoring\DB\Migrations\V1.250903.1100__add_reporting_tables_and_enums.sql",
    # Példa egy másik egyedi fájlra:
    # r"C:\projektem\konfiguracio\app.config"
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
    ".ts", ".tsx", ".js", ".html", ".sql",
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

def generate_output_components(project_items, base_path, keywords):
    """
    Legenerálja a kimeneti fájlnév és útvonal központi elemeit a bemeneti
    paraméterek alapján.
    Visszatérési érték: (alap_név, időbélyeg_str)
    """
    base_name = "export"
    if project_items:
        primary_project_item = project_items[0]

        if base_path and base_path in primary_project_item:
            relative_part = primary_project_item.replace(base_path, "")
        else:
            relative_part = os.path.basename(primary_project_item)

        if os.path.isfile(primary_project_item):
            relative_part, _ = os.path.splitext(relative_part)

        folder_structure = relative_part.replace("\\", "_").replace("/", "_").lower()

        base_name_parts = [folder_structure]
        if keywords:
            sanitized_keywords = [re.sub(r'[\W_]+', '', k).lower() for k in keywords if k]
            if sanitized_keywords:
                keywords_str = "+".join(sanitized_keywords)
                base_name_parts.append(keywords_str)

        base_name = "_".join(part for part in base_name_parts if part)

    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    return base_name, timestamp_str


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
    """Ellenőrzi, hogy egy fájlnév szerepel-e a kizárási listán."""
    return any(fnmatch.fnmatch(filename, pattern) for pattern in EXCLUDED_PATTERNS)


def is_allowed_file(filepath):
    """
    Eldönti, hogy egy adott fájl megfelel-e a feldolgozási feltételeknek
    (kiterjesztés, kizárások, kulcsszavak).
    """
    filename = os.path.basename(filepath)
    # Ellenőrizzük, hogy a fájl kiterjesztése szerepel-e az engedélyezettek között.
    _, ext = os.path.splitext(filename)
    if not ext or ext.lower() not in ALLOWED_EXTENSIONS:
        return False
    # Ellenőrizzük, hogy a fájlnév nincs-e a kizárt minták között.
    if is_excluded_file(filename):
        return False
    # Ha vannak útvonal kulcsszavak, ellenőrizzük, hogy az útvonal tartalmazza-e valamelyiket.
    if PATH_KEYWORDS and not any(keyword.lower() in filepath.lower() for keyword in PATH_KEYWORDS):
        return False
    return True


def collect_source_files(root_dir):
    """Rekurzívan összegyűjti a releváns fájlokat egy könyvtárból."""
    collected_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in EXCLUDED_DIRS]
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if is_allowed_file(filepath):
                collected_files.append(filepath)
    return collected_files


def write_combined_file(files, output_path, base_path):
    """A megadott fájlok tartalmát egyetlen kimeneti fájlba írja."""
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
    """A szkript fő belépési pontja."""
    # --- Fájlnév és kimeneti útvonal generálása ---
    base_name, timestamp_str = generate_output_components(PROJECT_ITEMS, BASE_PATH_FOR_RELPATH, PATH_KEYWORDS)

    # Dátum mappa (YYYYMMDD) és al-mappa nevének meghatározása
    date_folder = timestamp_str.split('_')[0]
    sub_folder = base_name

    # Teljes kimeneti útvonal és fájlnév összeállítása
    output_directory = os.path.join(date_folder, sub_folder)
    final_filename = f"{base_name}_{timestamp_str}.txt"
    output_file_path = os.path.join(output_directory, final_filename)

    # A szükséges mappastruktúra létrehozása (ha még nem létezik)
    os.makedirs(output_directory, exist_ok=True)


    all_files = []
    print("🚀 Szkript indítása a következő beállításokkal:")
    print(f"  Kimeneti fájl: {output_file_path}")
    print(f"  Feldolgozandó elemek (fájlok/könyvtárak): {len(PROJECT_ITEMS)} db")
    if PATH_KEYWORDS:
        print(f"  Aktív útvonal szűrő! Kulcsszavak: {', '.join(PATH_KEYWORDS)}")

    # Végigmegyünk a feldolgozandó elemeken.
    for path_item in PROJECT_ITEMS:
        # Ha az elem egy létező könyvtár...
        if os.path.isdir(path_item):
            print(f"\n🔍 Könyvtár bejárása: {path_item}")
            source_files = collect_source_files(path_item)
            all_files.extend(source_files)
            print(f"    -> {len(source_files)} releváns fájl hozzáadva.")
        # Ha az elem egy létező fájl...
        elif os.path.isfile(path_item):
            print(f"\n➕ Egyedi fájl vizsgálata: {path_item}")
            if is_allowed_file(path_item):
                all_files.append(path_item)
                print("    -> Fájl hozzáadva.")
            else:
                print("    -> Fájl kihagyva (nem felelt meg a szűrési feltételeknek).")
        # Ha az elem se nem fájl, se nem könyvtár (vagy nem létezik).
        else:
            print(f"\n⚠️ Figyelmeztetés: Az útvonal nem létezik vagy nem érvényes: {path_item}")

    # Kiszűrjük az esetleges duplikátumokat és sorba rendezzük a fájlokat.
    unique_files = sorted(list(set(all_files)))

    if not unique_files:
        print("\n❌ Nem található a szűrési feltételeknek megfelelő fájl.")
        return

    print(f"\n✅ Összesen {len(unique_files)} egyedi fájl összegyűjtve.")
    print("✍️  Feldolgozás és írás a kimeneti fájlba...")
    write_combined_file(unique_files, output_file_path, BASE_PATH_FOR_RELPATH)
    print(f"🎯 Kész! Az exportált fájl elérhető itt: {output_file_path}")


if __name__ == "__main__":
    main()