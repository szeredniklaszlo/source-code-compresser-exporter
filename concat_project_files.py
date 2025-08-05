import os
import fnmatch

# Állítsd be a projekted gyökerét itt
PROJECT_DIR = "C:\\Users\\user\\Desktop\\Projects\\kep-sc"  # <-- Ezt módosítsd
OUTPUT_FILE = "kep_sc_snapshot.txt"

# Kizárt könyvtárak
EXCLUDED_DIRS = {
    "node_modules", "dist", "coverage", "target", "build", ".git", ".idea", ".vscode", ".gradle", ".mvn", "__pycache__",
    "bin", "obj", ".vs"  # .NET specifikus kizárások
}

# Kizárt fájlnevek vagy minták
EXCLUDED_PATTERNS = [
    "package-lock.json", "*.spec.ts", "*.class", "*.iml", "*.log", "*.jar", "*.war",
    "*.user", "*.suo"  # Visual Studio felhasználói beállítások
]

# Csak ezekkel a kiterjesztésekkel engedélyezünk fájlokat
ALLOWED_EXTENSIONS = {
    # Webfejlesztési fájlok
    ".ts", ".tsx", ".js", ".html", ".scss", ".css",

    # Adatok
    #".json",

    # Java specifikus (meghagyva az eredetiből)
    ".java", ".xml", ".properties",

    # Konfiguráció és dokumentáció
    ".yml", ".yaml", ".md", ".txt", ".env", ".sh",

    # .NET és C# specifikus kiterjesztések
    ".cs", ".csproj", ".sln", ".cshtml", ".razor", ".config"
}

def is_excluded_file(filename):
    return any(fnmatch.fnmatch(filename, pattern) for pattern in EXCLUDED_PATTERNS)

def is_text_file(filename):
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)

def collect_source_files(root_dir):
    collected_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for filename in filenames:
            if is_excluded_file(filename):
                continue
            filepath = os.path.join(dirpath, filename)
            if is_text_file(filename):
                collected_files.append(filepath)
    return collected_files

def write_combined_file(files, output_path):
    with open(output_path, "w", encoding="utf-8") as out:
        for filepath in files:
            rel_path = os.path.relpath(filepath, PROJECT_DIR)
            out.write(f"\n\n{'=' * 100}\n")
            out.write(f"📄 FILE: {rel_path}\n")
            out.write(f"{'=' * 100}\n\n")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    out.write(f.read())
            except Exception as e:
                out.write(f"[HIBA: Nem sikerült beolvasni ezt a fájlt: {e}]\n")

def main():
    print(f"🔍 Projekt bejárása: {PROJECT_DIR}")
    source_files = collect_source_files(PROJECT_DIR)
    print(f"✅ {len(source_files)} forrásfájl összegyűjtve. Írás ide: {OUTPUT_FILE}")
    write_combined_file(source_files, OUTPUT_FILE)
    print("🎯 Kész! Most már feltöltheted az LLM-nek vagy chunkokra vághatod!")

if __name__ == "__main__":
    main()
