"""Build the Blender extension zip: python tools/build_zip.py  ->  dist/scaffvisor-<version>.zip"""
import os, re, zipfile
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ver = re.search(r'^version = "([^"]+)"', open(os.path.join(root, "blender_manifest.toml")).read(), re.M).group(1)
skip = {"docs", "tests", "tools", "dist", ".git", "__pycache__", ".github"}
out = os.path.join(root, "dist"); os.makedirs(out, exist_ok=True)
path = os.path.join(out, "scaffvisor-%s.zip" % ver)
with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in skip]
        for f in files:
            if f.endswith((".pyc", ".md")) and f != "README.md" or f == ".gitignore":
                continue
            full = os.path.join(d, f)
            z.write(full, os.path.relpath(full, root))
print(path)
