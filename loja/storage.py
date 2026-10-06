"""Mídia persistente: Supabase ou Cloudinary; disco local quando não há nuvem."""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)

LIMITE_ARQUIVO_NUVEM = 48 * 1024 * 1024


def usando_nuvem() -> bool:
    if getattr(settings, 'USAR_SUPABASE', False):
        return True
    return bool(getattr(settings, 'CLOUDINARY_URL', ''))


@deconstructible
class SafeFileSystemStorage(FileSystemStorage):
    """Não quebra o site se o arquivo já sumiu do disco (Render) ou o nome for uma URL."""

    def delete(self, name):
        if not name or str(name).startswith(('http://', 'https://')):
            return
        try:
            super().delete(name)
        except Exception:
            logger.warning('Não foi possível apagar arquivo local %s', name)


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
        try:
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
        except Exception:
            logger.warning('Falha ao remover mídia no Cloudinary: %s', name)

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


@deconstructible
class SupabaseStorage(Storage):
    """Envia capa, trailer e arquivo para o bucket público do Supabase."""

    def _credenciais(self):
        base = (getattr(settings, 'SUPABASE_URL', '') or '').rstrip('/')
        chave = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', '') or ''
        bucket = getattr(settings, 'SUPABASE_BUCKET', '') or 'midia'
        if not base or not chave:
            raise RuntimeError('Supabase não configurado.')
        return base, chave, bucket

    def _caminho(self, name: str) -> str:
        return str(name).replace('\\', '/').lstrip('/')

    def _save(self, name, content):
        tamanho = getattr(content, 'size', None)
        if tamanho and tamanho > LIMITE_ARQUIVO_NUVEM:
            raise RuntimeError('arquivo-grande')
        base, chave, bucket = self._credenciais()
        caminho = self._caminho(name)
        if hasattr(content, 'seek'):
            try:
                content.seek(0)
            except Exception:
                pass
        corpo = content.read()
        mime = mimetypes.guess_type(caminho)[0] or 'application/octet-stream'
        destino = f'{base}/storage/v1/object/{bucket}/{quote(caminho, safe="/")}'
        pedido = Request(destino, data=corpo, method='POST')
        pedido.add_header('Authorization', f'Bearer {chave}')
        pedido.add_header('apikey', chave)
        pedido.add_header('Content-Type', mime)
        pedido.add_header('x-upsert', 'true')
        try:
            with urlopen(pedido, timeout=120) as resposta:
                resposta.read()
        except HTTPError as erro:
            detalhe = erro.read().decode('utf-8', errors='replace')[:300]
            raise RuntimeError(f'Falha ao enviar para o Supabase ({erro.code}): {detalhe}') from erro
        return caminho

    def url(self, name):
        if not name:
            return ''
        if str(name).startswith(('http://', 'https://')):
            return str(name)
        base, _chave, bucket = self._credenciais()
        caminho = quote(self._caminho(name), safe='/')
        return f'{base}/storage/v1/object/public/{bucket}/{caminho}'

    def exists(self, name):
        return False

    def delete(self, name):
        if not name or str(name).startswith(('http://', 'https://')):
            return
        try:
            base, chave, bucket = self._credenciais()
            caminho = quote(self._caminho(name), safe='/')
            destino = f'{base}/storage/v1/object/{bucket}/{caminho}'
            pedido = Request(destino, method='DELETE')
            pedido.add_header('Authorization', f'Bearer {chave}')
            pedido.add_header('apikey', chave)
            with urlopen(pedido, timeout=30) as resposta:
                resposta.read()
        except Exception:
            logger.warning('Falha ao remover mídia no Supabase: %s', name)

    def size(self, name):
        return 0

    def get_available_name(self, name, max_length=None):
        if max_length and name and len(name) > max_length:
            return name[:max_length]
        return name


def media_storage():
    if getattr(settings, 'USAR_SUPABASE', False):
        return SupabaseStorage()
    if getattr(settings, 'CLOUDINARY_URL', ''):
        return CloudinaryAutoStorage()
    return SafeFileSystemStorage()
