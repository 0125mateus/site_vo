import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .assistant_service import chat, get_greeting, get_suggestions


def _audience_from_request(request):
    audience = request.GET.get('audience') or 'cliente'
    if request.method == 'POST':
        try:
            payload = json.loads(request.body.decode('utf-8'))
            audience = payload.get('audience', audience)
        except json.JSONDecodeError:
            pass
    return 'gestor' if audience == 'gestor' else 'cliente'


@require_GET
def assistant_init(request):
    audience = _audience_from_request(request)
    if audience == 'gestor' and not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'error': 'Acesso restrito a gestores.'}, status=403)

    return JsonResponse({
        'greeting': get_greeting(audience),
        'suggestions': get_suggestions(audience),
        'ai_enabled': bool(settings.OPENAI_API_KEY),
        'audience': audience,
    })


@require_POST
def assistant_chat_view(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    audience = payload.get('audience', 'cliente')
    if audience == 'gestor' and not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'error': 'Acesso restrito a gestores.'}, status=403)

    message = payload.get('message', '')
    history = payload.get('history', [])
    if not isinstance(history, list):
        history = []

    result = chat(message, history, audience=audience)
    if result.get('error') and not result.get('reply'):
        return JsonResponse(result, status=400)
    return JsonResponse(result)
