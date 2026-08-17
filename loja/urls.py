from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('discos/', views.catalogo_discos, name='catalogo_discos'),
    path('livros/', views.catalogo_livros, name='catalogo_livros'),
    path('filmes/', views.catalogo_filmes, name='catalogo_filmes'),
    path('busca/', views.busca, name='busca'),
    path('item/<int:produto_id>/', views.produto_detalhe, name='produto_detalhe'),
    path('biblioteca/', views.biblioteca, name='biblioteca'),
    path('biblioteca/reproduzir/<int:item_id>/', views.reproduzir_conteudo, name='reproduzir_conteudo'),
    path('biblioteca/arquivo/<int:item_id>/', views.acessar_arquivo, name='acessar_arquivo'),
    path('carrinho/', views.carrinho, name='carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_carrinho'),
    path('pedidos/finalizar/', views.finalizar_pedido, name='finalizar_pedido'),
    path('pedidos/<int:pedido_id>/checkout/', views.checkout, name='checkout'),
    path('pedidos/<int:pedido_id>/processando/', views.processando_pedido, name='processando_pedido'),
    path('login/', views.LoginLojaView.as_view(), name='login'),
    path('login/esqueci-senha/', views.PasswordResetLojaView.as_view(), name='password_reset'),
    path('login/esqueci-senha/enviado/', views.PasswordResetDoneLojaView.as_view(), name='password_reset_done'),
    path('login/redefinir/<uidb64>/<token>/', views.PasswordResetConfirmLojaView.as_view(), name='password_reset_confirm'),
    path('logout/', views.LogoutLojaView.as_view(), name='logout'),
]
