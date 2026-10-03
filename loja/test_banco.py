from django.test import SimpleTestCase

from config.database import banco_disponivel


class BancoDisponivelTests(SimpleTestCase):
    def test_sem_url_nao_tenta_conectar(self):
        def conectar(url, timeout):
            raise AssertionError('não devia conectar')

        self.assertFalse(banco_disponivel('', conectar))

    def test_banco_que_recusa_nao_trava_o_boot(self):
        def conectar(url, timeout):
            raise OSError('connection refused')

        self.assertFalse(banco_disponivel('postgres://loja/sumiu', conectar, timeout=5))

    def test_banco_que_responde_e_usado(self):
        chamado = {}

        def conectar(url, timeout):
            chamado['url'] = url
            chamado['timeout'] = timeout

        self.assertTrue(banco_disponivel('postgres://loja/ok', conectar, timeout=5))
        self.assertEqual(chamado['timeout'], 5)
