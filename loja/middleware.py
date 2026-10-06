from django.core.exceptions import RequestDataTooBig
from django.shortcuts import redirect


class LimiteUploadMiddleware:
    """Recusa um envio grande antes de derrubar o servidor gratuito."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except RequestDataTooBig:
            return redirect(f'{request.path}?erro=arquivo-grande')
