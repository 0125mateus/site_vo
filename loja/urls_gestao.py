from django.urls import path

from . import views_gestao

urlpatterns = [
    path('', views_gestao.dashboard, name='gestao_dashboard'),
    path('entrar/', views_gestao.GestaoLoginView.as_view(), name='gestao_entrar'),
    path('sair/', views_gestao.GestaoLogoutView.as_view(), name='gestao_sair'),
    path('discos/', views_gestao.discos_lista, name='gestao_discos_lista'),
    path('discos/novo/', views_gestao.disco_criar, name='gestao_disco_criar'),
    path('discos/<int:pk>/editar/', views_gestao.disco_editar, name='gestao_disco_editar'),
    path('discos/<int:pk>/excluir/', views_gestao.disco_excluir, name='gestao_disco_excluir'),
    path('livros/', views_gestao.livros_lista, name='gestao_livros_lista'),
    path('livros/novo/', views_gestao.livro_criar, name='gestao_livro_criar'),
    path('livros/<int:pk>/editar/', views_gestao.livro_editar, name='gestao_livro_editar'),
    path('livros/<int:pk>/excluir/', views_gestao.livro_excluir, name='gestao_livro_excluir'),
    path('midias/', views_gestao.midias_lista, name='gestao_midias_lista'),
    path('midias/novo/', views_gestao.midia_criar, name='gestao_midia_criar'),
    path('midias/<int:pk>/editar/', views_gestao.midia_editar, name='gestao_midia_editar'),
    path('midias/<int:pk>/excluir/', views_gestao.midia_excluir, name='gestao_midia_excluir'),
    path('assistente/', views_gestao.assistente_frases, name='gestao_assistente_frases'),
    path('assistente/frases/<int:pk>/excluir/', views_gestao.assistente_frase_excluir, name='gestao_assistente_frase_excluir'),
    path('pedidos/', views_gestao.pedidos_lista, name='gestao_pedidos_lista'),
    path('pedidos/<int:pk>/', views_gestao.pedido_detalhe, name='gestao_pedido_detalhe'),
    path('clube/', views_gestao.planos_clube_lista, name='gestao_planos_clube_lista'),
    path('clube/novo/', views_gestao.plano_clube_criar, name='gestao_plano_clube_criar'),
    path('clube/<int:pk>/editar/', views_gestao.plano_clube_editar, name='gestao_plano_clube_editar'),
    path('importar/', views_gestao.importar_catalogo, name='gestao_importar_catalogo'),
    path('api/gerar-descricao/', views_gestao.gerar_descricao_ia, name='gestao_gerar_descricao_ia'),
]
