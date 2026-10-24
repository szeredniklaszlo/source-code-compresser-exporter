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
    #r"S:\Programozas\Egyeb\MVP\rentio-core",
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
    "remove_multiline_comments": False,  # Eltávolítja a /* ... */ kommenteket
    "remove_singleline_comments": False,  # Eltávolítja a // kommenteket (a /// XML doksit nem)
    "summarize_xml_doc_comments": False,  # A /// kommenteket egy soros összefoglalóvá alakítja
    "remove_debug_blocks": False,  # Eltávolítja a #if DEBUG ... #endif blokkokat (C#)
    "remove_namespace_declarations": False,  # Eltávolítja a 'namespace ...' sorokat/blokkokat (C#)
    "remove_using_statements": False,  # Eltávolítja a 'using ...;' sorokat (C#)
    "remove_import_statements": False,  # Eltávolítja az 'import ...' sorokat (JS/TS)
    "collapse_multiple_empty_lines": False,  # Több üres sort egyre cserél
}

# --- Szűrési Szabályok ---
# Könyvtárak, amiket TELJESEN figyelmen kívül hagyunk (generált, cache, külső cuccok)
EXCLUDED_DIRS = {
    # Generált build és függőség mappák
    ".next",
    "node_modules",
    "target",
    "dist",
    "build",
    "out",
    "coverage",
    ".mvn",

    # Verziókezelő és fejlesztői környezet
    ".git",
    ".idea",
    ".vscode",
    ".local",
    "__pycache__",
    "bin",
    "obj",
    #".vs", ".nuke",  # .NET specifikus kizárások

    # Nem fejlesztett kódok / mockuppok / logok
    "tmp",            # Stitch design/mockup mentések és képek
    "logs",           # Backend és teszt futási logok
    "public",         # Next.js gyári sablon SVG ikonok
    "ui-blueprint",   # Mockup PNG-k és html fájlok a docs alatt

    # Ignored real code
    # "Test", "Tests", "UnitTest", "UnitTests", "E2ETests",
    # "Common.Logic", "Common.Logic.UnitTests", "Common.Pdf", "Common.UnitTest",
    # "ClientApp", "helm", "Docker", "Appsetting.Development",

    ".agents",
    ".infrastructure",

    # ÚJ: Üres AI mappa, komplett tesztmappák és a felesleges Supabase function mappa
    ".ai",
    "test",       # Ezzel kiesik a backend src/test (nem kell egyesével kizárni a tesztkonfigokat)
    "tests",      # Ezzel kiesik a frontend e2e tesztmappája is
    #"supabase",   # Ha nem kellenek a Deno edge funkciók
}

# Kizárt egyedi fájlok és minták (amiket nem te írtál, vagy csak szemét)
EXCLUDED_PATTERNS = [
    # Generált csomagkezelő és build cache fájlok
    "package-lock.json",
    "next-env.d.ts",
    "*.tsbuildinfo",
    "mvnw",
    "mvnw.cmd",
    "fajlfa.txt",
    "admin_reports_c24.html",

    # Fordítási termékek és logok
    "*.class",
    "*.jar",
    "*.war",
    "*.log",
    "*.iml",
    "*.pyc",

    # Konfigurációs meta fájlok (általában nem releváns a forráskódhoz)
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    ".nextignore",

    # Ha a tesztfájlokat IS ki akarod hagyni, vedd ki a kettőskeresztet:
    "*.test.ts", "*.test.tsx", "*.test.js", "*.spec.ts", "*Test.java", "*IT.java",

    # Ignored real code
    # "*.user", "*.suo", "*.md",
    # "*.Test.csproj", "*.UnitTest.csproj", "*.Tests.csproj", "*.csproj", "*.sln", "*.spec.ts",
    # "*.json", "*.yaml", "*.yml", ".env", ".gitignore", ".gitattributes",
    # "*.cmd", "*.sh", "*.bat", "*.ps1", "*.sql",
    # "I*.cs",

    # ÚJ: Lokális próbaszkriptek és indítók kizárása
    "test_api.js",
    "test_db.js",
    "scan.ps1",
    "find_docs.ps1",
    "dev.ps1",
    "release.ps1",

    # ÚJ: Felesleges Next.js starter CSS és logback XML-ek
    "page.module.css",
    "logback*.xml",

    # ÚJ: Tesztkeretrendszer-konfigurációk
    "*playwright*.config.ts",
    "*vitest*.config.ts",
    "vitest.setup.ts",

    # ÚJ: Felesleges típus-dömping, seed adatok és grafikai koordináták kizárása
    "db.ts",                    # A Supabase 1100 soros PostGIS típusleírója
    "*Seeder.java",             # A 250 soros dummy adatgeneráló (Ikea fotel stb.)
    "legal-content.ts",         # A statikus ÁSZF és Adatvédelem szövege
    "HomeAmbientBackground.tsx",# 150 sornyi SVG görbe-koordináta
    "Logo.tsx",                 # SVG logó koordináták
    "FloatingGlassShards.tsx",  # Lebegő háttér-dekoráció
]

# Csak a valódi forráskódokat és releváns konfigurációkat engedélyezzük
# Csak ezekkel a kiterjesztésekkel engedélyezünk fájlokat
ALLOWED_EXTENSIONS = {
    # Java backend
    ".java", ".xml",
    ".properties",

    # Adatbázis migrációk (Flyway - kulcsfontosságú saját kód!)
    #".sql",

    # Frontend (Next.js / TypeScript / React / Tooling)
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    #".mjs",
    ".css",
    ".scss",
    ".html",

    # C# & PowerShell (ha a saját .infrastructure vagy .agents szkriptek kellenek)
    # .NET és C# specifikus kiterjesztések
    ".cs", ".csproj", ".sln", ".cshtml", ".razor", ".config",
    ".ps1",

    # Konfiguráció és dokumentáció
    ".json",
    #".yml",
    #".yaml",
    "Dockerfile",
    ".xml",
    # TODO: remove if not needed:
    ".md", ".txt", ".env", ".sh",
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
    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
            return True
    return False


def is_allowed_file(filepath):
    """
    Eldönti, hogy egy adott fájl megfelel-e a feldolgozási feltételeknek
    (kiterjesztés, kizárások, kulcsszavak).
    """
    filename = os.path.basename(filepath)
    # Ellenőrizzük, hogy a fájl kiterjesztése szerepel-e az engedélyezettek között.
    _, ext = os.path.splitext(filename)

    # Speciális eset: Dockerfile-nak nincs külön kiterjesztése
    if filename.lower() == "dockerfile":
        ext = "Dockerfile"

    if not ext or ext.lower() not in [e.lower() for e in ALLOWED_EXTENSIONS]:
        return False

    if is_excluded_file(filename):
        return False

    if PATH_KEYWORDS and not any(keyword.lower() in filepath.lower() for keyword in PATH_KEYWORDS):
        return False

    return True


def collect_source_files(root_dir):
    """Rekurzívan összegyűjti a releváns fájlokat egy könyvtárból."""
    collected_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Csak a tiltólistás könyvtárakat vágjuk le a bejárásból,
        # így a hasznos ponttal kezdődő mappák (.infrastructure, .agents) megmaradnak!
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]

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
    print(f"  Feldolgozandó elemek: {len(PROJECT_ITEMS)} db")
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
                print("    -> Fájl kihagyva.")
        # Ha az elem se nem fájl, se nem könyvtár (vagy nem létezik).
        else:
            print(f"\n⚠️ Az útvonal nem létezik: {path_item}")

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
