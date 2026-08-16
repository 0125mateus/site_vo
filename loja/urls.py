from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('carrinho/', views.carrinho, name='carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', views.adicionar_ao_carrinho, name='adicionar_carrinho'),
    path('pedidos/finalizar/', views.finalizar_pedido, name='finalizar_pedido'),
    path('pedidos/<int:pedido_id>/checkout/', views.checkout, name='checkout'),
    path('pedidos/<int:pedido_id>/processando/', views.processando_pedido, name='processando_pedido'),
    path('login/', views.LoginLojaView.as_view(), name='login'),
    path('logout/', views.LogoutLojaView.as_view(), name='logout'),
]
