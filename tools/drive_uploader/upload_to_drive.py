#!/usr/bin/env python3
import argparse, os, sys, mimetypes
from pathlib import Path
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Path constants
CREDENTIALS_PATH = "credentials.json"

def ensure_auth():
    gauth = GoogleAuth()
    # Try to load saved client credentials
    gauth.LoadCredentialsFile(CREDENTIALS_PATH)
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    gauth.SaveCredentialsFile(CREDENTIALS_PATH)
    return GoogleDrive(gauth)

def get_or_create_folder(drive, name, parent_id):
    # Try to find existing folder
    q = f"mimeType = 'application/vnd.google-apps.folder' and trashed = false and name = '{name}' and '{parent_id}' in parents"
    matches = drive.ListFile({'q': q}).GetList()
    if matches:
        return matches[0]['id']
    # Create
    folder = drive.CreateFile({
        'title': name,
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [{'id': parent_id}]
    })
    folder.Upload()
    return folder['id']

def upload_file(drive, local_path, parent_id):
    fname = os.path.basename(local_path)
    mimetype, _ = mimetypes.guess_type(local_path)
    gfile = drive.CreateFile({'title': fname, 'parents': [{'id': parent_id}]})
    gfile.SetContentFile(local_path)
    gfile.Upload()
    print("Subido:", local_path, "→", f"https://drive.google.com/file/d/{gfile['id']}/view")

def mirror_directory(drive, src_dir, dst_folder_id):
    src_dir = Path(src_dir)
    # Map local subfolders to Drive folder IDs
    folder_map = {src_dir: dst_folder_id}
    for root, dirs, files in os.walk(src_dir):
        root_p = Path(root)
        parent_id = folder_map[root_p]
        # Ensure subfolders exist
        for d in dirs:
            sub = root_p / d
            sub_id = get_or_create_folder(drive, d, parent_id)
            folder_map[sub] = sub_id
        # Upload files
        for f in files:
            local = root_p / f
            upload_file(drive, str(local), parent_id)

def main():
    ap = argparse.ArgumentParser(description="Subir contenido de una carpeta a Google Drive (espejo de estructura).")
    ap.add_argument("--src", required=True, help="Ruta local de la carpeta a subir (ej: ../../salidas)")
    ap.add_argument("--folder-id", required=True, help="Folder ID de Google Drive destino")
    args = ap.parse_args()

    drive = ensure_auth()
    # Validar que folder-id exista
    try:
        dst = drive.CreateFile({'id': args.folder_id})
        dst.FetchMetadata()
    except Exception as e:
        print("ERROR: Folder ID inválida o no accesible:", e, file=sys.stderr)
        sys.exit(1)

    mirror_directory(drive, args.src, args.folder_id)
    print("¡Carga completa!")

if __name__ == "__main__":
    main()
