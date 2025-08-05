import os
import fnmatch
import re
import textwrap
import time

# Állítsd be a projekted gyökerét itt
PROJECT_DIR = "S:\\Programozas\\Egyeb\\Munkahely\\kep-sc\\Source\\ClientApp"  # <-- Ezt módosítsd

prefix_to_remove = "S:\\Programozas\\Egyeb\\Munkahely\\"  # <-- Ezt is módosítsd
remaining_path = PROJECT_DIR.replace(prefix_to_remove, "")

# Ha üresen hagyod ([] vagy None), a szűrés nem aktív, és a szkript a régi módon működik.
PATH_KEYWORDS = ["error", "exception"]  # <-- MÓDOSÍTSD EZT A LISTÁT A SZŰRÉSHEZ

folder_structure = remaining_path.replace("\\", "_").lower()

# A kimeneti fájl nevének összeállítása, figyelembe véve a kulcsszavakat is.
filename_parts = [folder_structure]
if PATH_KEYWORDS:
    # A kulcsszavakat kisbetűssé alakítjuk és '+' jellel fűzzük össze a jobb olvashatóság érdekében.
    # A biztonság kedvéért eltávolítunk minden nem alfanumerikus karaktert.
    sanitized_keywords = [re.sub(r'[\W_]+', '', k).lower() for k in PATH_KEYWORDS if k]
    if sanitized_keywords:
        keywords_str = "+".join(sanitized_keywords)
        filename_parts.append(keywords_str)

filename_parts.append(time.strftime("%Y%m%d_%H%M%S"))

OUTPUT_FILE = "_".join(filename_parts) + ".txt"

# Kizárt könyvtárak
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


def process_file_content(content):
    """
    Ez a függvény végzi a forráskód "karcsúsítását" az LLM számára.
    A feldolgozás sorrendje fontos.
    """

    # 1. Többsoros /* ... */ kommentek törlése
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    # 2. Egysoros // kommentek törlése, de a /// XML kommenteket kihagyjuk.
    content = re.sub(r'(?<!/)//.*', '', content)

    # 3. XML doc kommentek feldolgozása
    def xml_comment_replacer(match):
        block = match.group(0)
        summary_match = re.search(r'<summary>\s*(.*?)\s*</summary>', block, re.DOTALL)
        if summary_match:
            summary_text = ' '.join(line.strip() for line in summary_match.group(1).split('\n'))
            indentation = re.match(r'^\s*', block).group(0) if re.match(r'^\s*', block) else ''
            return f"{indentation}/// {summary_text}\n"
        else:
            return ''

    content = re.sub(r'(^\s*///.*$\n?)+', xml_comment_replacer, content, flags=re.MULTILINE)

    # 4. #if DEBUG ... #endif blokkok törlése
    content = re.sub(r'#if DEBUG.*?#endif', '', content, flags=re.DOTALL | re.MULTILINE)

    # 5. Namespace deklarációk eltávolítása (C#)
    # Kezeli az opcionális BOM (\ufeff) karaktert is a sor elején.
    # Először a blokk-hatókörű (namespace { ... }) névtereket kezeljük
    def namespace_replacer(match):
        # A regex a névtéren belüli teljes tartalmat capture-öli az 1. csoportba.
        inner_content = match.group(1)
        # A textwrap.dedent eltávolítja a közös behúzást a blokk minden sorából.
        return textwrap.dedent(inner_content)

    # Ez a regex megkeresi a 'namespace ... {' ... '}' blokkot.
    # [\s\S]*? : Bármilyen karakter (beleértve a sortöréseket is), nem mohó módon.
    # A re.DOTALL miatt a '.' is illeszkedik a sortörésekre.
    content = re.sub(r'^\s*\ufeff?\s*namespace\s+[\w\.]+\s*\{([\s\S]*)\}\s*$', namespace_replacer, content,
                     flags=re.MULTILINE)

    content = re.sub(r'^\s*\ufeff?\s*namespace .*;\s*$\n?', '', content, flags=re.MULTILINE)

    # 6. `using` direktívák törlése (C#)
    # A biztonság kedvéért itt is kezeljük az opcionális BOM-ot, hátha using van a fájl elején.
    content = re.sub(r'^\s*\ufeff?\s*using .*;\s*$\n?', '', content, flags=re.MULTILINE)

    # 7. `import` direktívák törlése (TypeScript/JavaScript)
    content = re.sub(r'^\s*import[\s\S]+?from[\s\S]+?[;]?\s*$', '', content, flags=re.MULTILINE)

    # 8. Több egymást követő üres sor cseréje egyetlen üres sorra
    content = re.sub(r'\n\s*\n+', '\n\n', content)

    return content.strip()


def is_excluded_file(filename):
    return any(fnmatch.fnmatch(filename, pattern) for pattern in EXCLUDED_PATTERNS)


def is_text_file(filename):
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def collect_source_files(root_dir):
    """
    Kibővítve a PATH_KEYWORDS változó szerinti szűréssel.
    """
    collected_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Könyvtárak kizárása a bejárásból a gyorsaság érdekében
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in EXCLUDED_DIRS]

        for filename in filenames:
            # Fájlnév és minta alapján történő kizárás
            if is_excluded_file(filename):
                continue

            filepath = os.path.join(dirpath, filename)

            # --- ÚJ SZŰRÉSI LOGIKA ---
            # Ha a PATH_KEYWORDS lista definiálva van és nem üres, akkor ellenőrizzük a path-t.
            if PATH_KEYWORDS:
                # Kis- és nagybetű érzéketlen ellenőrzés, hogy a path tartalmazza-e bármelyik kulcsszót.
                if not any(keyword.lower() in filepath.lower() for keyword in PATH_KEYWORDS):
                    continue  # Ha egyik kulcsszó sem található meg a path-ban, kihagyjuk a fájlt.

            # Kiterjesztés ellenőrzése
            if is_text_file(filename):
                collected_files.append(filepath)

    return collected_files


def write_combined_file(files, output_path):
    with open(output_path, "w", encoding="utf-8") as out:
        for filepath in files:
            rel_path = os.path.relpath(filepath, PROJECT_DIR)
            out.write(f"\n\n--- FILE: {rel_path} ---\n\n")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    original_content = f.read()
                    processed_content = process_file_content(original_content)
                    out.write(processed_content)
            except Exception as e:
                out.write(f"[HIBA: Nem sikerült beolvasni ezt a fájlt: {e}]\n")


def main():
    print(f"🔍 Projekt bejárása: {PROJECT_DIR}")
    if PATH_KEYWORDS:
        print(f"⚡ Aktív útvonal szűrő! Kulcsszavak: {', '.join(PATH_KEYWORDS)}")

    source_files = collect_source_files(PROJECT_DIR)

    if not source_files:
        print("❌ Nem található a szűrési feltételeknek megfelelő fájl.")
        return

    print(f"✅ {len(source_files)} forrásfájl összegyűjtve. Feldolgozás és írás ide: {OUTPUT_FILE}")
    write_combined_file(source_files, OUTPUT_FILE)
    print("🎯 Kész! A tovább karcsúsított fájl most már feltölthető az LLM-nek!")


if __name__ == "__main__":
    main()