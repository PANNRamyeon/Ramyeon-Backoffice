"""
URL configuration for posbackend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from app.kpi_views.customer_product_views import (
    CustomerProductListView,
    CustomerProductDetailView,
    CustomerProductSearchView,
    CustomerProductByCategoryView,
    CustomerFeaturedProductsView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('app.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    # Customer product catalogue (public)
    path('api/v1/customer/products/', CustomerProductListView.as_view(), name='customer-products'),
    path('api/v1/customer/products/search/', CustomerProductSearchView.as_view(), name='customer-products-search'),
    path('api/v1/customer/products/featured/', CustomerFeaturedProductsView.as_view(), name='customer-products-featured'),
    path('api/v1/customer/products/category/<str:category_id>/', CustomerProductByCategoryView.as_view(), name='customer-products-by-category'),
    path('api/v1/customer/products/<str:product_id>/', CustomerProductDetailView.as_view(), name='customer-product-detail'),
    path('', lambda request: HttpResponse("POS System API is running!")),
]
