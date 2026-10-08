"""Pix copia e cola e QR Code no padrão BR Code do Banco Central, com a chave da própria loja."""

import base64
import io
import re
import unicodedata
from decimal import Decimal


def _campo(identificador: str, valor: str) -> str:
    return f'{identificador}{len(valor):02d}{valor}'


def _crc16(payload: str) -> str:
    crc = 0xFFFF
    for byte in payload.encode('utf-8'):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f'{crc:04X}'


def _sem_acento(texto: str, limite: int) -> str:
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'[^A-Za-z0-9 .&\-]', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()[:limite]


def normalizar_chave(tipo: str, chave: str) -> str:
    chave = (chave or '').strip()
    if tipo in ('cpf', 'cnpj'):
        return re.sub(r'\D', '', chave)
    if tipo == 'telefone':
        digitos = re.sub(r'\D', '', chave)
        if not digitos.startswith('55') or len(digitos) <= 11:
            digitos = '55' + digitos
        return '+' + digitos
    return chave.lower()


def txid_do_pedido(pedido_id) -> str:
    return f'VP{pedido_id}'[:25]


def montar_copia_e_cola(chave: str, nome: str, cidade: str, valor=None, txid: str = '***') -> str:
    conta = _campo('00', 'br.gov.bcb.pix') + _campo('01', chave)
    payload = (
        _campo('00', '01')
        + _campo('26', conta)
        + _campo('52', '0000')
        + _campo('53', '986')
    )
    if valor is not None:
        payload += _campo('54', f'{Decimal(valor).quantize(Decimal("0.01"))}')
    payload += (
        _campo('58', 'BR')
        + _campo('59', _sem_acento(nome, 25))
        + _campo('60', _sem_acento(cidade, 15))
        + _campo('62', _campo('05', txid or '***'))
        + '6304'
    )
    return payload + _crc16(payload)


def qr_code_base64(texto: str) -> str:
    import qrcode

    imagem = qrcode.make(texto, box_size=8, border=2)
    buffer = io.BytesIO()
    imagem.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def pix_da_loja(config, valor, txid: str) -> dict:
    codigo = montar_copia_e_cola(
        normalizar_chave(config.tipo_chave, config.chave),
        config.nome_recebedor,
        config.cidade,
        valor,
        txid,
    )
    return {'qr_code': codigo, 'qr_code_base64': qr_code_base64(codigo), 'ticket_url': ''}
