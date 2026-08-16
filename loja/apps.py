from django.apps import AppConfig


class LojaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'loja'

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from .models import FraseTreinoAssistente
        from .assistant_intent import invalidate_model_cache

        def _clear_cache(**kwargs):
            invalidate_model_cache()

        post_save.connect(_clear_cache, sender=FraseTreinoAssistente)
        post_delete.connect(_clear_cache, sender=FraseTreinoAssistente)
