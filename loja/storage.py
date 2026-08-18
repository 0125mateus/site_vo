"""Mídia persistente: Cloudinary em produção, disco local em desenvolvimento."""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


def usando_nuvem() -> bool:
    return bool(getattr(settings, 'CLOUDINARY_URL', ''))


@deconstructible
class CloudinaryAutoStorage(Storage):
    """Envia capa, trailer e arquivos com resource_type=auto (imagem, vídeo ou raw)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._configured = False

    def _config(self):
        if self._configured:
            return
        import cloudinary

        url = getattr(settings, 'CLOUDINARY_URL', '')
        if not url:
            raise RuntimeError('CLOUDINARY_URL não configurada.')
        cloudinary.config(cloudinary_url=url, secure=True)
        self._configured = True

    def _save(self, name, content):
        self._config()
        import cloudinary.uploader

        if hasattr(content, 'seek'):
            try:
                content.seek(0)
            except Exception:
                pass

        public_id = str(Path(name).with_suffix('')).replace('\\', '/').lstrip('/')
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            resource_type='auto',
            overwrite=True,
            unique_filename=False,
            use_filename=True,
            invalidate=True,
        )
        return result.get('secure_url') or result.get('url') or public_id

    def url(self, name):
        if not name:
            return ''
        if str(name).startswith(('http://', 'https://')):
            return str(name)
        self._config()
        import cloudinary.utils

        return cloudinary.utils.cloudinary_url(name, secure=True)[0]

    def exists(self, name):
        return False

    def delete(self, name):
        if not name:
            return
        self._config()
        import cloudinary.uploader

        public_id = self._public_id_from_name(name)
        for resource_type in ('image', 'video', 'raw'):
            try:
                cloudinary.uploader.destroy(
                    public_id,
                    resource_type=resource_type,
                    invalidate=True,
                )
            except Exception:
                logger.debug('Cloudinary destroy %s/%s ignorado', resource_type, public_id)

    def _public_id_from_name(self, name: str) -> str:
        if str(name).startswith(('http://', 'https://')):
            path = urlparse(str(name)).path
            parts = path.split('/upload/')
            if len(parts) == 2:
                rest = parts[1]
                if rest.startswith('v') and '/' in rest:
                    rest = rest.split('/', 1)[1]
                return str(Path(rest).with_suffix(''))
        return str(Path(name).with_suffix('')).replace('\\', '/')

    def size(self, name):
        return 0

    def get_available_name(self, name, max_length=None):
        if max_length and name and len(name) > max_length:
            return name[:max_length]
        return name


def media_storage():
    if usando_nuvem():
        return CloudinaryAutoStorage()
    return FileSystemStorage()
