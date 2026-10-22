import os
import shutil
import zipfile


def unpack_upload(file, target_dir):
    ext = os.path.splitext(file.filename)[1].lower()

    if ext in (".html", ".htm"):
        file.save(os.path.join(target_dir, "index.html"))
        return "index.html"

    if ext == ".zip":
        zip_path = os.path.join(target_dir, "upload.zip")
        file.save(zip_path)
        _extract_zip(zip_path, target_dir)
        os.remove(zip_path)
        return _find_entry_html(target_dir)

    raise ValueError("Поддерживаются только файлы .html и .zip")


def _extract_zip(zip_path, target_dir):
    root = os.path.realpath(target_dir)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            path = os.path.realpath(os.path.join(root, member.filename))
            if not path.startswith(root + os.sep):
                raise ValueError(f"Недопустимый путь в архиве: {member.filename}")
            if member.is_dir():
                os.makedirs(path, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with archive.open(member) as src, open(path, "wb") as dst:
                shutil.copyfileobj(src, dst)


def _find_entry_html(root):
    candidates = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__MACOSX"]
        for name in filenames:
            if name.lower().endswith((".html", ".htm")):
                rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
                candidates.append(rel)

    if not candidates:
        raise ValueError("В архиве нет HTML-файла")

    candidates.sort(key=lambda p: (p.count("/"), not p.lower().endswith(("index.html", "index.htm")), p))
    return candidates[0]
