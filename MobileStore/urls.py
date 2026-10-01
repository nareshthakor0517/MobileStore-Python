from django.contrib import admin
from django.urls import path
from store.views import *

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home & Product
    path('index/', index, name='index'),
    path('product_detail/<int:id>/', product_detail, name='product_detail'),
   
    # Search
    path('search/', search_results, name='search_results'),

    # All Product
    path('all_products/', all_products, name='all_products'),

    # Buy Now
    path('buynow/<int:product_id>/', buy_now, name='buy_now'),


    # Medlware Step-1
    path("begin-checkout/", begin_checkout, name="begin_checkout"),

    # Cart
    path('cart/', cart_view, name='cart_view'),
    path('cart/update/<int:id>/', update_cart, name='update_cart'),
    path('add-to-cart/<int:id>/', add_to_cart, name='add_to_cart'),
    path('remove/<int:id>/', remove_from_cart, name='remove_from_cart'), 
    path('increase/<int:id>/', increase_quantity, name='increase_quantity'),
    path('decrease/<int:id>/', decrease_quantity, name='decrease_quantity'),

    # Checkout/placeorder
    path('placeOrder/', placeOrder, name='placeOrder'),
    path('save-and-deliver/', save_and_deliver, name='save_and_deliver'),
    path("setAddress/", setAddress, name="setAddress"),

    # OrderSummary
    path('orderSummary/', orderSummary, name='orderSummary'),
    path('orderSummary/update_summary/<int:id>/', update_summary, name='update_summary'),
    path('increase-summary/<int:id>/', increase_qty, name='increase_qty'),
    path('decrease-summary/<int:id>/', decrease_qty, name='decrease_qty'),
    path('remove-summary/<int:id>/', remove_summary, name='remove_summary'), 
    path('save_gst/', save_gst, name='save_gst'),

    # Payment
    path('payment/', payment, name='payment'),
    path('destroy_gst_session/', destroy_gst_session, name='destroy_gst_session'),
    path('debug-session/', debug_session, name='debug_session'),

    # COD
    path("cod_order/", cod_order, name="cod_order"),
    path("order_success/", order_success, name="order_success"),

    # Order
    path("my_orders/", my_orders, name="my_orders"),
    path("invoice/<int:order_id>/", invoice, name="invoice"),

    # Review
    path('submit_review/', submit_review, name='submit_review'),

    # TrackOrder
    path('track/<str:order_id>/', track_order, name='track_order'),
    path('api/track_status/<int:order_id>/', track_status_api, name='track_status_api'),

    # User
    path('profile_user/', profile_user, name='profile_user'),
    path('profile_user/update/', update_user_info, name='update_user_info'),

    path('address/delete/<int:address_id>/', delete_address, name='delete_address'),
    path('register/', add_user, name='add_user'),
    path('login/', login_user, name='login_user'),
    path('logout/', logout_user, name='logout_user'),
    path('showuser/', show_user, name='show_user'),
    path('toggle-active/<int:id>/', toggle_active, name='toggle_active'),
    path('delete-user/<int:id>/', delete_user, name='delete_user'),


        # Forgot Password
    path('forgot-password/',forgot_password_view, name='forgot_password'), 
    path('verify/',verify_otp_view, name='verify_otp'), 
    path('verify-check/',verify_otp_check, name='verify_otp_check'), 
    path('resend-otp/',resend_otp_view, name='resend_otp'), 
    path('reset-password/',reset_password_view, name='reset_password'),

    # Admin
    path("admin-login/", admin_login, name="admin_login"),
    path("admin-logout/", admin_logout, name="admin_logout"),
    path("admin-panel/dashboard/", admin_dashboard, name="admin_dashboard"),
    
        # Category
    path('addcat/', add_category, name='add_category'),
    path('showcat/', show_categoryData, name='show_category'),
    path('updatecat/<int:id>/', update_category, name='update_category'),
    path('deletecat/<int:id>/', delete_category, name='delete_category'),

        # Product
    path('addpro/', add_product, name='add_product'),
    path('showpro/', show_productData, name='show_product'),
    path('updatepro/<int:id>/', update_product, name='update_product'),
    path('deletepro/<int:id>/', delete_product, name='delete_product'),

    path("api/sales-trend/", sales_trend),
    path("api/sales-by-category/", sales_by_category_api),

    path('api/top-selling-products/', top_selling_products_api, name='top_selling_products_api'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
