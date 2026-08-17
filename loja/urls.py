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
    path('login/esqueci-senha/', views.PasswordResetLojaView.as_view(), name='password_reset'),
    path('login/esqueci-senha/enviado/', views.PasswordResetDoneLojaView.as_view(), name='password_reset_done'),
    path('login/redefinir/<uidb64>/<token>/', views.PasswordResetConfirmLojaView.as_view(), name='password_reset_confirm'),
    path('logout/', views.LogoutLojaView.as_view(), name='logout'),
]
