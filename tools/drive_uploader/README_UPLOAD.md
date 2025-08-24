# Uploader a Google Drive (carpeta destino de Auditoría)

Este script sube **todas** las salidas generadas a la carpeta de Drive:
**Folder ID:** `1g9gNN1XHrW9ei2ArtZ8v2vcv4dMZelRe`

## Opción A — Subida manual (recomendada si estás apurado/a)
1. Abrí la carpeta de Drive (link compartido).
2. Arrastrá y soltá los archivos de `/salidas/` o subí el ZIP `entregables_auditoria_expensas.zip`.

## Opción B — Subida automática con Python
> Requiere crear credenciales OAuth de Google (tipo *Desktop App*) y descargar `client_secrets.json`.

1. Creamos un **proyecto** en <https://console.cloud.google.com/apis/credentials>.
2. Hacé clic en **Create credentials → OAuth client ID → Desktop App**.
3. Descargá el archivo **`client_secrets.json`** y colocalo en **esta misma carpeta** (`tools/drive_uploader/`).
4. Instalar dependencias:
   ```bash
   pip install pydrive2
   ```
5. Ejecutar el uploader:
   ```bash
   python upload_to_drive.py --folder-id 1g9gNN1XHrW9ei2ArtZ8v2vcv4dMZelRe --src ../../salidas
   ```
6. En el primer uso se abrirá el flujo de autorización. Aceptá permisos. Se guardará `credentials.json` localmente.
7. Verificá en Drive que los archivos aparecen dentro de la carpeta destino, preservando subcarpetas.

**Scopes** solicitados (mínimos): `drive.file`, `drive.metadata.readonly`.
