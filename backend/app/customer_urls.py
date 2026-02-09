from django.urls import path

from app.kpi_views.customer_product_views import (
    CustomerProductListView,
    CustomerProductDetailView,
    CustomerProductSearchView,
    CustomerProductByCategoryView,
    CustomerFeaturedProductsView,
)

urlpatterns = [
    path('products/', CustomerProductListView.as_view(), name='customer-products'),
    path('products/search/', CustomerProductSearchView.as_view(), name='customer-products-search'),
    path('products/featured/', CustomerFeaturedProductsView.as_view(), name='customer-products-featured'),
    path('products/category/<str:category_id>/', CustomerProductByCategoryView.as_view(), name='customer-products-by-category'),
    path('products/<str:product_id>/', CustomerProductDetailView.as_view(), name='customer-product-detail'),
]


