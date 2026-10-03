def banco_disponivel(database_url, conectar, timeout=5):
    """True só se o Postgres responder dentro do prazo."""
    if not database_url:
        return False
    try:
        conectar(database_url, timeout)
        return True
    except Exception:
        return False
