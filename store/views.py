# views.py

from utils.payment_token import generate_payment_token, verify_payment_token
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, InvalidOperation 
from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse

# Create your views here.
from .models import *
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import CustomUser  
from django.contrib.auth import authenticate, get_user_model, login, logout 
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import time
from django.db.models import Avg,Count
from django.core.paginator import Paginator
from django.db.models.functions import Coalesce

@login_required(login_url='/login/')
def index(request):

    # 🆕 New Products (latest 8)
    products = Product.objects.annotate(
        average_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ).order_by('-pro_id')[:8]

    # 🏆 Top Sellers (most purchased 8)
    top_products = Product.objects.annotate(
        total_sold=Coalesce(Sum('orderitem__quantity'), 0),
        average_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ).order_by('-total_sold')[:8]

    context = {
        'products': products,          # 👈 New Products (same naam rakha)
        'top_products': top_products   # 👈 Top Sellers
    }

    return render(request, 'shop/index.html', context)

@login_required(login_url='/login/')
def product_detail(request, id):
    productData = Product.objects.get(pro_id=id)

    # Discount calculation
    if productData.pro_mrp and productData.pro_price:
        discount = ((productData.pro_mrp - productData.pro_price) / productData.pro_mrp) * 100
        productData.por_discount = round(discount)
    else:
        productData.por_discount = 0

    # Reviews (Initial queryset, used for total count and breakdown)
    all_reviews_for_stats = productData.reviews.all()
    total_reviews = all_reviews_for_stats.count()

    # Average Rating & Star Breakdown
    if total_reviews > 0:
        productData.average_rating = round(sum(r.rating for r in all_reviews_for_stats) / total_reviews, 1)
        rating_counts = all_reviews_for_stats.values('rating').annotate(count=Count('rating'))
        star_counts_dict = {i: 0 for i in range(1, 6)}
        for item in rating_counts:
            star_counts_dict[item['rating']] = item['count']
        star_breakdown_list = []
        for rating in range(5, 0, -1):
            count = star_counts_dict[rating]
            percentage = round((count / total_reviews) * 100) if total_reviews else 0
            star_breakdown_list.append({'rating': rating, 'count': count, 'percentage': percentage})
    else:
        productData.average_rating = 0.0
        star_breakdown_list = [{'rating': r, 'count': 0, 'percentage': 0} for r in range(5, 0, -1)]

    # Filters and Sorting Setup
    filter_val = request.GET.get("filter", "All stars")
    sort_val = request.GET.get("sort", "Most Relevant")
    page_number = request.GET.get('page') # Get the current page number
    
    # Start with the unfiltered queryset for filtering/sorting
    reviews_queryset = all_reviews_for_stats 

    # Stars filter
    stars_filter = None
    if 'stars' in filter_val.lower():
        try:
            stars_filter = int(filter_val.split()[0])
        except:
            stars_filter = None

    if stars_filter:
        reviews_queryset = reviews_queryset.filter(rating__gte=stars_filter)

    # Sorting
    if sort_val == 'Most Relevant':
        reviews_queryset = reviews_queryset.order_by('-rating', '-created_at')
    elif sort_val == 'Newest':
        reviews_queryset = reviews_queryset.order_by('-created_at')
    elif sort_val == 'Oldest':
        reviews_queryset = reviews_queryset.order_by('created_at')
    elif sort_val == 'Highest rated':
        reviews_queryset = reviews_queryset.order_by('-rating')
    elif sort_val == 'Lowest rated':
        reviews_queryset = reviews_queryset.order_by('rating')
    elif sort_val == 'Most helpful':
        # Fallback since helpful_count doesn't exist yet
        reviews_queryset = reviews_queryset.order_by('-rating', '-created_at')
    else:
        reviews_queryset = reviews_queryset.order_by('-rating', '-created_at')

    # 🔄 Pagination Implementation (The required update)
    
    # 1. Create a Paginator instance with 5 reviews per page
    paginator = Paginator(reviews_queryset, 5) 
    
    # 2. Get the Page object for the requested page number
    reviews_page = paginator.get_page(page_number)
    
    # Static lists for the template
    stars = ["All stars", "5 stars", "4 stars", "3 stars", "2 stars", "1 star"]
    sort_options = ['Most Relevant', 'Newest', 'Oldest', 'Most helpful', 'Highest rated', 'Lowest rated']

    # Related products (same category, excluding current product)
    related_products = Product.objects.filter(
        cat_id_id=productData.cat_id_id
    ).exclude(pro_id=productData.pro_id
    ).annotate(
        average_rating=Avg('reviews__rating'),   # yahan 'reviews' use karna hai
        review_count=Count('reviews')            # aur yahan bhi
    )[:4]

    return render(request, 'shop/product_detail.html', {
        'product': productData,
        'star_breakdown': star_breakdown_list,
        'total_reviews': total_reviews,
        'reviews': reviews_page, # Pass the Paginated object
        'selected_filter': filter_val,
        'selected_sort': sort_val,
        'stars': stars,
        'sort_options': sort_options,
        'related_products': related_products,
    })

# Start Search

from django.db.models import Q # जटिल queries के लिए

def search_results(request):
    query = request.GET.get('q')
    
    # यदि कोई query है, तो फ़िल्टर करें
    if query:
        # यहाँ फ़ील्ड के नाम बदलें: name, description, brand की जगह 
        # pro_name, pro_description, pro_brand का उपयोग करें।
        products = Product.objects.filter(
            Q(pro_name__icontains=query) | 
            Q(pro_description__icontains=query) |
            Q(pro_brand__icontains=query) |
            Q(processor__icontains=query) # प्रोसेसर फ़ील्ड भी जोड़ा जा सकता है 
        ).distinct()
    else:
        # यदि कोई query नहीं है, तो सभी उत्पाद दिखाएँ
        products = Product.objects.all() 
    
    products = products.annotate(
        average_rating=Avg('reviews__rating'),  # reviews = related_name of ProductReview
        review_count=Count('reviews')
    )

    product_count = products.count() 

    context = {
        'query': query,
        'products': products,
        'product_count': product_count,
    }
    
    return render(request, 'shop/search_results.html', context)
# End Search

# Start All Product
def all_products(request):
    products = Product.objects.annotate(
        average_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    )

    product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
    return render(request, 'shop/all_products.html', context)

# End All Product

# Start Buy Now

@login_required
def buy_now(request, product_id): 
    user = request.user
    # यह सुनिश्चित करें कि Product मॉडल को इंपोर्ट किया गया है
    product = get_object_or_404(Product, pro_id=product_id) 

    # 🎯 FIX 1: सभी पुराने चेकआउट सेशन वेरिएबल्स को हटाएँ, 
    # ताकि यह हमेशा एक नई चेकआउट प्रक्रिया के रूप में शुरू हो
    for key in ['step_cart', 'step_placeorder', 'step_ordersummary', 'checkout_completed', 'selected_address_id', 'payment_token']:
        request.session.pop(key, None)

    # 1. Cart Clear
    Cart.objects.filter(user_id=user).delete()

    # 2. Add New Product
    Cart.objects.create(user_id=user, pro_id=product, quantity=1)

    # 3. Session Set (यह अब नए सिरे से सेट हो रहा है)
    request.session["step_cart"] = True 
    request.session["is_buy_now_flow"] = True # यह आपके मिडिलवेयर के लिए फ्लैग है

    # 4. Redirect to place order page
    return redirect('/placeOrder/')

# End Buy Now 
 
#Midalware 
def begin_checkout(request):
    if request.method != "POST":
        return redirect("/cart/")

    cart_items = Cart.objects.filter(user_id=request.user)
    
    if not cart_items.exists():
        return redirect("/cart/")

    for key in ['step_cart', 'step_placeorder', 'step_ordersummary', 'checkout_completed', 'selected_address_id', 'payment_token']:
        request.session.pop(key, None)

    request.session['step_cart'] = True
    request.session['checkout_completed'] = False
    request.session.modified = True

    return redirect("/placeOrder/")

#Cart

@login_required(login_url='/login/')
def cart_view(request):
    cart_items = Cart.objects.filter(user_id=request.user)

 # ❌ Remove out-of-stock items automatically
    for item in cart_items:
        if item.pro_id.pro_stock <= 0:
            item.delete()
            messages.warning(request, f"{item.pro_id.pro_name} is out of stock and removed from your cart.")
            
    # Add subtotal for each cart item
    for item in cart_items:
        item.subtotal = item.pro_id.pro_price * item.quantity
    
    # Precompute min/max flags + discount calculate
    for item in cart_items:
        item.is_min = item.quantity <= 1
        item.is_max = item.quantity >= item.pro_id.pro_stock
        
        if item.pro_id.pro_mrp > 0:
            discount = ((item.pro_id.pro_mrp - item.pro_id.pro_price) / item.pro_id.pro_mrp) * 100
            item.pro_discount = int(discount)
        else:
            item.pro_discount = 0

    # Total price of cart
    cart_total_price = sum(item.subtotal for item in cart_items)

    # Total quantity
    cart_total_quantity = sum(item.quantity for item in cart_items)

    # Unique products
    cart_total_items = cart_items.count()

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'cart_total_price': cart_total_price,
        'cart_total_quantity': cart_total_quantity,
        'cart_total_items': cart_total_items,
    })



@login_required(login_url='/login/')
def update_cart(request, id):
    item = Cart.objects.get(user_id=request.user, cart_id=id)
    action = request.POST.get('action')

    if action == "increase":
        # Increase only if stock allows
        if item.quantity < item.pro_id.pro_stock:
            item.quantity += 1

    elif action == "decrease":
        if item.quantity > 1:
            item.quantity -= 1

    item.save()
    return redirect('/cart/')


@login_required(login_url='/login/')
def remove_from_cart(request, id):
    item = Cart.objects.get(user_id=request.user, cart_id=id)
    item.delete()
    return redirect('/cart/')

@login_required(login_url='/login/')
def add_to_cart(request, id):
    product = Product.objects.get(pro_id=id)

    # ❌ Stock check: agar stock 0 hai, add na kare
    if product.pro_stock <= 0:
        messages.error(request, "This product is out of stock!")
        return redirect('/index/')

    # Check if item already exists
    cart_item, created = Cart.objects.get_or_create(
        user_id=request.user,
        pro_id=product
    )

    if created:
        # first time adding to cart → quantity = product ka original stock nahi!
        cart_item.quantity = 1
        cart_item.save()
    else:
        # ❌ NO INCREASE QUANTITY HERE!
        messages.info(request, "This item is already in your cart.")

    return redirect('/cart/')


# Increase Quantity (+) with stock check
@login_required(login_url='/login/')
def increase_quantity(request, id):
    cart_item = Cart.objects.get(user_id=request.user, pro_id_id=id)
    
    if cart_item.quantity < cart_item.pro_id.pro_stock:
        cart_item.quantity += 1
        cart_item.save()
    # else: do nothing, cannot exceed stock

    return redirect('/cart/')


# Decrease Quantity (-) with minimum quantity check
@login_required(login_url='/login/')
def decrease_quantity(request, id):
    cart_item = Cart.objects.get(user_id=request.user, pro_id_id=id)
    
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        # Quantity is 1 → remove item
        cart_item.delete()

    return redirect('/cart/')

#End Cart

#Start PlaceOrder
@login_required(login_url='/login/')
def placeOrder(request):

    if request.session.get("checkout_completed"):
        # अगर चेकआउट पूरा हो गया है, तो इंडेक्स पर वापस जाएँ
        return redirect("/index/")

    # 🎯 UPDATED LOGIC: 'step_cart' या 'is_buy_now_flow' में से कोई भी सेट होना चाहिए
    is_buy_now = request.session.get("is_buy_now_flow", False)
    
    if not request.session.get("step_cart") and not is_buy_now:
        # अगर न तो सामान्य कार्ट चेकआउट शुरू हुआ है (step_cart) 
        # और न ही 'buy now' बटन दबाया गया है, तो कार्ट पर रीडायरेक्ट करें।
        return redirect("/cart/")

    # अगर यूज़र 'buy_now' फ़्लो से आया है, तो सेशन से 'is_buy_now_flow' को हटा दें 
    # ताकि वह इस पेज को रिफ्रेश करने पर या बाद में सीधे एक्सेस न कर सके।
    if is_buy_now:
        del request.session["is_buy_now_flow"]
    
    # --- कार्ट आइटम जाँच और कैलकुलेशन (पुराना लॉजिक) ---
    cart_items = Cart.objects.filter(user_id=request.user)

    if not cart_items.exists():
        # कार्ट खाली होने पर कार्ट पेज पर रीडायरेक्ट करें (यह चेक buy_now के लिए भी आवश्यक है)
        return redirect("/cart/")

    cart_total_items = cart_items.count()
    cart_total_quantity = sum(item.quantity for item in cart_items)
    # सुनिश्चित करें कि pro_id.pro_price और pro_id.pro_mrp सही हैं
    total_price = sum(item.pro_id.pro_price * item.quantity for item in cart_items)
    total_mrp = sum(item.pro_id.pro_mrp * item.quantity for item in cart_items)
    total_discount = total_mrp - total_price
    total_payable = total_price
    savings = total_discount

    addresses = Address.objects.filter(user_id=request.user)

    context = {
        'cart_items': cart_items,
        'cart_total_items': cart_total_items,
        'cart_total_quantity': cart_total_quantity,
        'total_price': total_price,
        'total_mrp': total_mrp,
        'total_discount': total_discount,
        'final_price': total_payable,
        'user_id': request.user,
        'savings': savings,
        'addresses': addresses,
    }

    return render(request, 'shop/placeOrder.html', context)

# Address
import requests

# LocationIQ API setup
LOCATIONIQ_KEY = "pk.fa492be49370b5fd989e46274dd97d71"  # Replace with your free API key
LOCATIONIQ_URL = "https://us1.locationiq.com/v1/search.php"

def get_lat_long_locationiq(address_text):
    """Use LocationIQ to get precise latitude and longitude"""
    try:
        params = {
            "key": LOCATIONIQ_KEY,
            "q": address_text,
            "format": "json",
            "limit": 1
        }
        response = requests.get(LOCATIONIQ_URL, params=params, timeout=10)
        data = response.json()
        if data and isinstance(data, list):
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print("Geocoding error:", e)
    return None, None


@login_required(login_url='/login/')
def save_and_deliver(request):
    if request.method != "POST":
        return redirect("/placeOrder/")

    if not request.session.get("step_cart"):
        return redirect("/placeOrder/")

    # Get form data
    address_id = request.POST.get("address_id")
    full_name = request.POST.get("full_name")
    mobile_number = request.POST.get("mobile_number")
    pincode = request.POST.get("pincode")
    locality = request.POST.get("locality")
    address_line = request.POST.get("address_line")
    city = request.POST.get("city")
    state = request.POST.get("state")
    landmark = request.POST.get("landmark")
    alternate_phone = request.POST.get("alternate_phone")
    address_type = request.POST.get("address_type")

    # Full address for geocoding
    full_address = f"{address_line}, {locality}, {city}, {state}, {pincode}"

    # LocationIQ geocoding
    latitude, longitude = get_lat_long_locationiq(full_address)

    if address_id:
        address = get_object_or_404(Address, address_id=address_id, user_id=request.user)
        address.full_name = full_name
        address.mobile_number = mobile_number
        address.pincode = pincode
        address.locality = locality
        address.address_line = address_line
        address.city = city
        address.state = state
        address.landmark = landmark
        address.alternate_phone = alternate_phone
        address.address_type = address_type
        address.latitude = latitude
        address.longitude = longitude
        address.save()
        request.session["selected_address_id"] = address.address_id
    else:
        new_addr = Address.objects.create(
            user_id=request.user,
            full_name=full_name,
            mobile_number=mobile_number,
            pincode=pincode,
            locality=locality,
            address_line=address_line,
            city=city,
            state=state,
            landmark=landmark,
            alternate_phone=alternate_phone,
            address_type=address_type,
            latitude=latitude,
            longitude=longitude
        )
        request.session["selected_address_id"] = new_addr.address_id

    request.session["step_placeorder"] = True
    request.session.modified = True

    return redirect("/orderSummary/")

#Start OrderSummary
@login_required(login_url='/login/')
def orderSummary(request):
    cart_items = Cart.objects.filter(user_id=request.user)

    if not cart_items.exists():
        return redirect("/cart/")

    if request.session.get("checkout_completed"):
        return redirect("/index/")

    if not request.session.get("step_placeorder"):
        return redirect("/index/")

    request.session['step_ordersummary'] = True
    request.session.modified = True

    cart_total_items = cart_items.count()
    cart_total_quantity = sum(item.quantity for item in cart_items)

    total_price = 0
    total_mrp = 0

    for item in cart_items:
        item.item_total_price = item.pro_id.pro_price * item.quantity
        item.item_total_mrp = item.pro_id.pro_mrp * item.quantity
        item.item_total_discount = item.item_total_mrp - item.item_total_price
        item.discount_percentage = round(
            (item.item_total_discount / item.item_total_mrp) * 100
        ) if item.item_total_mrp > 0 else 0

        total_price += item.item_total_price
        total_mrp += item.item_total_mrp

    total_discount = total_mrp - total_price
    total_payable = total_price
    savings = total_discount

    address_id = request.session.get("selected_address_id")
    address = Address.objects.filter(address_id=address_id, user_id=request.user).first()

    # 🔥 CREATE TOKEN
    token = None
    try:
        payload = {
            "user_id": request.user.user_id,
            "amount": float(total_payable),
            "step": "ordersummary"
        }
        token = generate_payment_token(payload)
        request.session["payment_token"] = token
    except Exception as e:
        print("Payment token error:", e)

    # 👉 ENABLE PAYMENT PAGE REDIRECT
    payment_url = f"/payment/?token={token}"

    return render(request, 'shop/orderSummary.html', {
        'cart_items': cart_items,
        'cart_total_items': cart_total_items,
        'cart_total_quantity': cart_total_quantity,
        'total_price': total_price,
        'total_mrp': total_mrp,
        'total_discount': total_discount,
        'total_payable': total_payable,
        'savings': savings,
        "address": address,
        "payment_url": payment_url,
        "token": token,
    })

@login_required(login_url='/login/')
def setAddress(request):
    if request.method == "POST":
        data = json.loads(request.body)
        address_id = data.get("address_id")

        request.session['selected_address_id'] = address_id

        # ⭐ MOST IMPORTANT FIX
        request.session['step_placeorder'] = True
        request.session.modified = True

        return JsonResponse({"status": "ok"})

    return JsonResponse({"status": "invalid"})

@login_required(login_url='/login/')
def update_summary(request, id):
    cart_item = Cart.objects.get(user_id=request.user, cart_id=id)
    action = request.POST.get("action")

    if action == "increase":
        cart_item.quantity += 1

    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            return redirect('/orderSummary/')

    cart_item.save()
    return redirect('/orderSummary/')

    
@login_required(login_url='/login/')
def remove_summary(request, id):
    item = Cart.objects.get(user_id=request.user, cart_id=id)
    item.delete()
    return redirect('/orderSummary/')

# Increase Quantity (+)
@login_required(login_url='/login/')
def increase_qty(request, id):
    cart_item = Cart.objects.get(user_id=request.user, cart_id=id)
    product = cart_item.pro_id

    if cart_item.quantity < product.pro_stock:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('/orderSummary/')


# Decrease Quantity (-)
@login_required(login_url='/login/')
def decrease_qty(request, id):
    cart_item = Cart.objects.get(user_id=request.user, cart_id=id)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()

    # ❌ Delete nahi karna
    return redirect('/orderSummary/')

@csrf_exempt
def save_gst(request):
    if request.method == "POST":
        gst_number = request.POST.get('gst_number', '').strip()
        business_name = request.POST.get('business_name', '').strip()
        business_address = request.POST.get('business_address', '').strip()

        request.session['gst_number'] = gst_number
        request.session['business_name'] = business_name
        request.session['business_address'] = business_address

        # ⭐ RE-USE TOKEN GENERATED IN orderSummary ⭐
        token = request.session.get("payment_token")

        if not token:
            return HttpResponse("❌ Payment token missing. Go back to Order Summary.")

        return redirect(f"/payment/?token={token}")

    return redirect('/orderSummary/')


#End OrderSummary

# Start Payment

@login_required(login_url='/login/')
def payment(request):
    from decimal import Decimal

    # --- Cart Calculations ---
    cart_items = Cart.objects.filter(user_id=request.user)
    cart_total_items = cart_items.count()
    cart_total_quantity = sum(item.quantity for item in cart_items)

    total_price_decimal = Decimal(0)
    total_mrp_decimal = Decimal(0)

    try:
        for item in cart_items:
            price = Decimal(str(item.pro_id.pro_price))
            mrp = Decimal(str(item.pro_id.pro_mrp))

            item.item_total_price = price * item.quantity
            item.item_total_mrp = mrp * item.quantity
            item.item_total_discount = item.item_total_mrp - item.item_total_price
            
            item.discount_percentage = round(
                (item.item_total_discount / item.item_total_mrp) * 100
            ) if item.item_total_mrp > Decimal(0) else 0

            total_price_decimal += item.item_total_price
            total_mrp_decimal += item.item_total_mrp

    except:
        messages.error(request, "❌ Product price data is invalid for calculation.")
        return redirect("/orderSummary/")

    total_discount_decimal = total_mrp_decimal - total_price_decimal

    total_price = float(total_price_decimal)
    total_mrp = float(total_mrp_decimal)
    total_discount = float(total_discount_decimal)
    total_payable = total_price
    savings = total_discount

    # --- Address & Token Validation (unchanged) ---
    address_id = request.session.get("selected_address_id")
    address = Address.objects.filter(
        address_id=address_id, user_id=request.user
    ).first()

    if request.session.get("checkout_completed"):
        return redirect("/index/")

    token = request.GET.get("token")
    if not token:
        messages.error(request, "❌ Payment token missing.")
        return redirect("/orderSummary/")

    session_token = request.session.get("payment_token")
    if not session_token or token != session_token:
        messages.error(request, "❌ Invalid or already used token")
        return redirect("/orderSummary/")

    data = verify_payment_token(token, max_age=300)
    if not data or data.get("user_id") != request.user.user_id:
        messages.error(request, "❌ Invalid or expired token")
        return redirect("/orderSummary/")

    if not (
        request.session.get('step_cart') and
        request.session.get('step_placeorder') and
        request.session.get('step_ordersummary')
    ):
        messages.error(request, "❌ Missing checkout steps")
        return redirect("/orderSummary/")

    request.session.pop("payment_token", None)
    request.session.modified = True
    
    # 🔥 TIMER ADD HERE
    expiry_ts = int(time.time()) + 300  # 5 minutes from now

    return render(request, "shop/payment.html", {
        'cart_items': cart_items,
        'cart_total_items': cart_total_items,
        'cart_total_quantity': cart_total_quantity,
        'total_price': total_price,
        'total_mrp': total_mrp,
        'total_discount': total_discount,
        'total_payable': total_payable,
        'savings': savings,
        "address": address,
        'expiry_ts':expiry_ts
    })

@csrf_exempt
def destroy_gst_session(request):
    if request.method == "POST":
        keys_to_remove = [
            'gst_number', 'business_name', 'business_address',
            'terms_accepted', 'can_access_payment'
        ]
        for key in keys_to_remove:
            request.session.pop(key, None)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'failed'})

def debug_session(request):
    data = {
        'session_keys': list(request.session.keys()),
        'session_data': {k: request.session.get(k) for k in request.session.keys()},
        'cookies': request.COOKIES,
        'user': str(request.user) if request.user.is_authenticated else 'anonymous',
    }
    return JsonResponse(data)

#End Payment

# Start COD

@login_required
def order_success(request):
    user = request.user
    
    Cart.objects.filter(user_id=user).delete() 
    
    for key in [
        'step_cart', 
        'step_placeorder', 
        'step_ordersummary', 
        'selected_address_id', 
        'payment_token', 
        'is_buy_now_flow' # buy_now फ़्लो का सेशन भी हटाएँ
    ]:
        request.session.pop(key, None)
    
    # 🎯 FIX 3: 'checkout_completed' फ्लैग सेट करें
    # यह मिडिलवेयर को बताता है कि चेकआउट पूरा हो गया है और यूज़र को चेकआउट पेजों से ब्लॉक कर देना चाहिए।
    request.session['checkout_completed'] = True 
    
    return render(request, "shop/order_success.html")
from threading import Timer

def cod_order(request):
    if request.method != "POST":
        return redirect("/orderSummary/")

    cart_items = Cart.objects.filter(user_id=request.user)
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("/cart/")

    total_price = sum(item.pro_id.pro_price * item.quantity for item in cart_items)

    address_id = request.session.get("selected_address_id")
    address = Address.objects.filter(address_id=address_id, user_id=request.user).first()
    if not address:
        messages.error(request, "Please select a delivery address.")
        return redirect("/placeOrder/")

    # Create Order
    order = Order.objects.create(
        user=request.user,
        total_amount=total_price,
        payment_method="COD",
        payment_status="Pending",
        order_status="Confirmed",
        address=address,
    )

    for item in cart_items:
        order.items.create(
            pro_id=item.pro_id,
            quantity=item.quantity,
            price=item.pro_id.pro_price,
        )

    # Save GST if exists
    gst_number = request.session.get("gst_number")
    business_name = request.session.get("business_name")
    business_address = request.session.get("business_address")
    if gst_number or business_name or business_address:
        Gst.objects.create(
            order_id=order,
            gst_number=gst_number,
            business_name=business_name,
            business_address=business_address,
        )

    cart_items.delete()
    # Clear GST session
    for key in ['gst_number', 'business_name', 'business_address']:
        request.session.pop(key, None)

    request.session["checkout_completed"] = True

    # ------------------------------
    # Auto mark as Delivered after 30 minutes
    def mark_delivered():
        order.order_status = "Delivered"
        order.payment_status = "Paid"
        order.delivered_at = timezone.now()  # optional field if you track delivery time
        order.save()

    Timer(30*60, mark_delivered).start()  # 30 minutes = 1800 seconds
    # ------------------------------

    return redirect("/order_success/")

# End COD

# Start Order
def order_user(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'shop/order.html', context)
# End Order

# Start TrackOrder
from django.utils import timezone
import time
from datetime import datetime, timedelta

import random
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Order
from django.contrib.auth.decorators import login_required

steps = ["confirmed", "dispatched", "on_the_way", "delivered"]

def track_order(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    base_time = order.created_at

    step_dates = {
        "confirmed": base_time,
        "dispatched": base_time + timedelta(minutes=5),
        "on_the_way": base_time + timedelta(minutes=18),
        "delivered": base_time + timedelta(minutes=30),
    }

    step_titles = {
        "confirmed": "Order Confirmed",
        "dispatched": "Dispatched From Gandhinagar",
        "on_the_way": "Truck is On The Way",
        "delivered": "Delivered Successfully",
    }

    step_location = {
        "confirmed": "Gandhinagar, Gujarat",
        "dispatched": "Leaving Gandhinagar Facility",
        "on_the_way": "En Route to GANDHINAGAR",
        "delivered": f"{order.address.address_line.capitalize()}, {order.address.city.capitalize()}",
    }

    # Auto decide current step (0–3)
    now = timezone.now()
    diff_min = (now - base_time).total_seconds() / 60
    if diff_min < 5:
        current_step = 0
    elif diff_min < 18:
        current_step = 1
    elif diff_min < 30:
        current_step = 2
    else:
        current_step = 3
        # --- Backend auto-update DB after 30 min ---
        if order.order_status != "Delivered":
            order.order_status = "Delivered"
            order.payment_status = "Paid"
            order.delivered_at = timezone.now()
            order.save()

    full_delivery_address = f"{order.address.address_line}, {order.address.locality}, {order.address.city}, {order.address.state} - {order.address.pincode}"
    order_start_timestamp = int(order.created_at.timestamp() * 1000)

    return render(request, "shop/order_track.html", {
        "order": order,
        "steps": steps,
        "step_dates": step_dates,
        "step_titles": step_titles,
        "step_location": step_location,
        "current_step": current_step,
        "full_delivery_address": full_delivery_address,
        "order_start_timestamp": order_start_timestamp,
    })

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def broadcast_order_update(order_id, current_step, lat=None, lng=None):
    channel_layer = get_channel_layer()
    payload = {'current_step': current_step}
    if lat and lng:
        payload.update({'lat': lat, 'lng': lng})
    async_to_sync(channel_layer.group_send)(
        f'order_{order_id}',
        {
            'type': 'order_update',
            'payload': payload
        }
    )

def track_status_api(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    # compute current step same as your view logic (days diff)
    start = order.created_at
    diff_days = (timezone.now() - start).days
    current_step = min(diff_days, 3)
    # Optionally return last known marker pos (for demo, return waypoint for step)
    lat, lng = None, None
    if current_step == 0:
        lat, lng = 23.0225, 72.5714
    elif current_step == 1:
        lat, lng = 23.2156, 72.6369
    else:
        lat, lng = order.address.latitude or 23.2156, order.address.longitude or 72.6369

    return JsonResponse({'current_step': current_step, 'lat': lat, 'lng': lng})

# End TrackOrder

# Start MyOrder

from django.db import transaction 

@login_required(login_url='/login/')
def my_orders(request):
    user = request.user
    orders = Order.objects.filter(user=user).order_by('-created_at').prefetch_related('items')

    reviewed_product_ids = Review.objects.filter(
        user_id=user
    ).values_list('pro_id', flat=True)

    if reviewed_product_ids.exists():
        with transaction.atomic():
            OrderItem.objects.filter(
                order_id__user=user,
                pro_id__in=reviewed_product_ids,
                already_reviewed=False 
            ).update(already_reviewed=True)

    return render(request, 'shop/order.html', {'orders': orders})

from decimal import Decimal as D
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order
from datetime import datetime

def amount_in_words(amount):
    """Convert number to words placeholder"""
    return f"Rupees {amount} Only"

@login_required(login_url='/login/')
def invoice(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    gst_rate = D('0.18')  # 18%

    items_list = []
    subtotal_excl_tax = D('0.00')
    total_gst = D('0.00')

    # Process Order Items
    for item in order.items.all():
        product = item.pro_id
        qty = D(str(item.quantity))
        unit_price = D(str(product.pro_price))  # Includes GST
        total_item_amount = (unit_price * qty).quantize(D('0.01'))

        # Reverse calculate GST and taxable value
        taxable_value = (unit_price / (1 + gst_rate)).quantize(D('0.01'))
        gst_amount = (unit_price - taxable_value).quantize(D('0.01'))

        subtotal_excl_tax += (taxable_value * qty)
        total_gst += (gst_amount * qty)

        items_list.append({
            'pro_name': product.pro_name,
            'quantity': qty,
            'unit_price': unit_price,
            'taxable_value': taxable_value,
            'gst_rate': 18,
            'gst_amount': gst_amount,
            'total_item_amount': total_item_amount,
            'hsn': getattr(product, 'hsn', 'N/A'),
            'asin': getattr(product, 'asin', 'N/A'),
        })

    # Grand total = sum of product totals
    total_amount = sum(item['total_item_amount'] for item in items_list)

    context = {
        'order': order,
        'items': items_list,

        'invoice_date': datetime.now(),
        'order_date': order.created_at,

        'subtotal_excl_tax': subtotal_excl_tax,
        'total_gst': total_gst,
        'total_amount': total_amount,
        'total_amount_in_words': amount_in_words(total_amount),

        'invoice_number': f'INV-{order.order_id}',
        'invoice_date': order.created_at,
        'order_date': order.created_at,

        # Billing & Shipping Addresses
        'billing_address': order.address,
        'shipping_address': getattr(order, 'shipping_address', order.address),
    }

    return render(request, 'shop/invoice.html', context)


@login_required(login_url='/login/')
def submit_review(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        try:
            rating = int(rating)
            if not 1 <= rating <= 5:
                messages.error(request, "Invalid rating value.")
                return redirect('my_orders')
                
            product = get_object_or_404(Product, pk=product_id)

            if not Review.objects.filter(user_id=request.user, pro_id=product).exists():
                Review.objects.create(
                    user_id=request.user,    
                    pro_id=product,          
                    rating=rating,
                    review_text=review_text.strip() 
                )
            
            OrderItem.objects.filter(
                pro_id=product,
                order_id__user=request.user 
            ).update(already_reviewed=True)
            
            messages.success(request, "Review submitted and all related orders updated! 🎉")

        except Exception as e:
            messages.error(request, f"An internal error occurred: {e}")
            print(f"DATABASE SAVE/UPDATE ERROR: {e}") 
            return redirect('my_orders')

        return redirect('my_orders')

    return redirect('my_orders')

# End MyOrder

# Update Stock/Quentity
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

@receiver(post_save, sender=OrderItem)  # Assuming OrderItem model exists
def update_product_stock(sender, instance, created, **kwargs):
    if created:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=instance.pro_id.pk)

            if product.pro_stock >= instance.quantity:
                product.pro_stock -= instance.quantity
            else:
                instance.quantity = product.pro_stock
                product.pro_stock = 0

            product.pro_status = 'Out of Stock' if product.pro_stock == 0 else 'In Stock'
            product.save()
            instance.save()

# END Stock/Quentity

#Start User 
def profile_user(request):
    if not request.user.is_authenticated:
        return redirect('login_user')

    # 1. Active Tab (Dashboard or Addresses)
    active_tab = request.GET.get('tab', 'dashboard') # Default is 'dashboard'

    # 3. Addresses Data (fetch, as it's needed regardless of the active tab)
    user_addresses = None 
    
    try:
        # Address model से वर्तमान logged-in user के लिए डेटा fetch करें
        user_addresses = Address.objects.filter(user_id=request.user).order_by('-created_at') 
        # Note: 'user_id' field का नाम आपके ForeignKey field से मेल खाना चाहिए।
        # यदि आपने Model में user_id को 'user' नाम दिया है, तो 'user=request.user' का उपयोग करें।
        # मैंने Model में 'user_id' field का उपयोग किया है, इसलिए यहाँ 'user_id=request.user' का उपयोग किया है।
        
    except Exception as e:
        print(f"Error fetching addresses: {e}")
        
    # ... (बाकी कोड)
    
    context = {
        'active_tab': active_tab, 
        'user_addresses': user_addresses or [], 
    }
    
    return render(request, 'user/profile_user.html', context)

def delete_address(request, address_id):
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect('/profile_user/?tab=addresses')

    # Get the address for this user
    address = get_object_or_404(Address, pk=address_id, user_id=request.user)

    # Check if this address is linked to any orders
    if Order.objects.filter(address=address).exists():
        messages.error(request, "This address cannot be deleted because it is linked with existing orders.")
    else:
        address.delete()
        messages.success(request, "Address deleted successfully!")

    # Redirect back to profile addresses tab
    return redirect('/profile_user/?tab=addresses')

from django.shortcuts import render, redirect
from django.contrib import messages
from store.models import CustomUser

def update_user_info(request):
    if request.method == "POST":
        # Get current logged-in user
        user = request.user

        # Get data from form
        name = request.POST.get("user_name")
        email = request.POST.get("user_email")
        number = request.POST.get("user_number")

        # Validate inputs
        if not name or not email or not number:
            messages.error(request, "All fields are required!")
            return redirect("profile_user")

        # Validate mobile number
        if not number.isdigit() or len(number) < 10:
            messages.error(request, "Enter a valid mobile number!")
            return redirect("profile_user")

        # Check if email is already used by another user
        if CustomUser.objects.filter(user_email=email).exclude(user_id=user.user_id).exists():
            messages.error(request, "This email is already in use by another account!")
            return redirect("profile_user")

        # Check if mobile number is already used by another user
        if CustomUser.objects.filter(user_number=number).exclude(user_id=user.user_id).exists():
            messages.error(request, "This mobile number is already in use by another account!")
            return redirect("profile_user")

        # Update user data
        user.user_name = name
        user.user_email = email
        user.user_number = number
        user.save()

        messages.success(request, "Your profile has been updated successfully!")
        return redirect("profile_user")

    # For GET request, just redirect to profile page
    return redirect("profile_user")

def add_user(request):
    if request.method == "POST":
        user_name = request.POST.get('user_name')
        user_email = request.POST.get('user_email')
        user_number = request.POST.get('user_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # ✅ Password check
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'user/add_user.html')

        # ✅ Email & number uniqueness check
        if CustomUser.objects.filter(user_email=user_email).exists():
            messages.error(request, "Email is already registered.")
            return render(request, 'user/add_user.html')

        if CustomUser.objects.filter(user_number=user_number).exists():
            messages.error(request, "Phone number is already registered.")
            return render(request, 'user/add_user.html')

        # ✅ Create user
        user = CustomUser.objects.create(
            user_name=user_name,
            user_email=user_email,
            user_number=user_number,
            password=make_password(password)
        )

        messages.success(request, "Registration successful! Please log in.")
        return redirect("/login/")

    return render(request, 'user/add_user.html')

def show_user(request):
    userData = CustomUser.objects.all() 
    context = {'userData': userData}
    return render(request, 'user/show_userData.html',context)

def toggle_active(request, id):
    user = CustomUser.objects.get(user_id=id)
    user.is_active = not user.is_active  # True <-> False toggle
    user.save()
    messages.success(request, f"{user.user_name} is now {'active' if user.is_active else 'inactive'}.")
    return redirect('/showuser/')

def delete_user(request,id):
    delete_id = CustomUser.objects.get(user_id = id)
    delete_id.delete()
    return redirect('/showuser/')

User = get_user_model()

def login_user(request):
    if request.method == "POST":
        user_email = request.POST.get('user_email')
        user_password = request.POST.get('user_password')  # must match form

        try:
            # check if user exists in DB
            user = User.objects.get(user_email=user_email)
        except User.DoesNotExist:
            messages.error(request, "Email not registered.")
            return redirect('/login/')

        # authenticate using custom backend
        user = authenticate(request, user_email=user_email, password=user_password)

        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f"Welcome {user.user_name}!")
                return redirect("/index/")
            else:
                messages.error(request, "Account inactive. Contact admin.")
        else:
            messages.error(request, "Invalid password. Try again.")

        return redirect('/login/')

    return render(request, 'user/login_user.html')

def logout_user(request):
    logout(request)  # clears the session
    return redirect('/login/')

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import time
from datetime import datetime, timedelta

from django.contrib import messages 
import json
import random
import time 

from .models import OTP 

CustomUser = get_user_model() 
OTP_VALIDITY_SECONDS = 30 
RESEND_COOLDOWN_SECONDS = 20 

# --- 1. Forgot Password View ---
@csrf_exempt
def forgot_password_view(request):
    if request.method == "POST":
        email_or_mobile = request.POST.get('email_or_mobile')
        
        try:
            user = CustomUser.objects.get(user_email=email_or_mobile)
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': 'This account does not exist.'})
        
        # Clean up old unused OTPs and generate a new one
        OTP.objects.filter(user=user, otp_type='forgot', is_used=False).delete()
        otp_obj = OTP.objects.create(user=user, otp_type='forgot')
        
        # Send OTP
        send_mail(
            subject='Your OTP for Password Reset',
            message=f'Your OTP is {otp_obj.otp_code}. It is valid for {OTP_VALIDITY_SECONDS} seconds.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.user_email],
            fail_silently=False
        )
        
        # Set Session Data
        request.session['user_id'] = user.pk
        request.session['user_contact'] = email_or_mobile
        # 🚀 NEW: Store timestamp when OTP was sent 
        request.session['otp_sent_timestamp'] = int(time.time())
        # 🚨 NEW FLAG: Set a temporary flag for the initial view load
        request.session['is_first_otp_view'] = True

        return JsonResponse({'status': 'ok', 'message': 'OTP sent successfully'})
    
    return render(request, 'user/forgot_password.html')


# --- 2. OTP Verification Display View (Forced Redirect on Reload) ---
def verify_otp_view(request):
    user_id = request.session.get('user_id')
    user_contact = request.session.get('user_contact')
    otp_timestamp = request.session.get('otp_sent_timestamp')
    is_first_load = request.session.get('is_first_otp_view', False)
    
    # 🚨 FORCED RELOAD CHECK: If not the first load, or crucial data is missing, redirect.
    # This ensures that any subsequent access (including reload) redirects.
    if not user_id or not user_contact or not otp_timestamp or not is_first_load:
        messages.error(request, 'Verification session expired or incomplete. Please start the password reset process again.')
        return redirect('forgot_password')
    
    # 🌟 TEMPORARY FLAG REMOVAL: Allow only one successful render.
    # On the first successful load, remove the flag. Any subsequent access/reload will fail the check above.
    del request.session['is_first_otp_view'] 

    # Calculate remaining time for the front-end timer
    current_time = int(time.time())
    time_elapsed = current_time - otp_timestamp
    time_remaining = OTP_VALIDITY_SECONDS - time_elapsed
    
    if time_remaining < 0:
        time_remaining = 0

    context = {
        'user_id': user_id, 
        'user_contact': user_contact,
        'time_remaining': time_remaining,
    }
    return render(request, 'user/verify_otp.html', context)

# --- 3. AJAX: OTP Verification Check ---
@csrf_exempt
def verify_otp_check(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            otp_input = data.get('otp')
            user_id = request.session.get('user_id')
            
            if not user_id:
                # Signal frontend to redirect if session is lost
                return JsonResponse({'status': 'redirect', 'url': 'forgot_password'})
            
            user = CustomUser.objects.get(pk=user_id)
            
            # OTP validation check 
            valid_otp = OTP.objects.filter(
                user=user, 
                otp_type='forgot', 
                is_used=False,
                created_at__gte=timezone.now() - timedelta(seconds=OTP_VALIDITY_SECONDS) 
            ).order_by('-created_at').first()

            if valid_otp and valid_otp.otp_code == otp_input:
                valid_otp.is_used = True
                valid_otp.save()
                request.session['otp_verified'] = True 
                return JsonResponse({'status': 'ok'})
            else:
                return JsonResponse({'status': 'error', 'error': 'Invalid or expired OTP.'})

        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'redirect', 'url': 'forgot_password'})
        except Exception:
            return JsonResponse({'status': 'error', 'error': 'An unexpected error occurred.'})

    return JsonResponse({'status': 'error', 'error': 'Invalid request method.'})


# --- 4. AJAX: Resend OTP (Smooth & Fast) ---
@csrf_exempt
def resend_otp_view(request):
    """Handles the AJAX request to resend the OTP."""
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        
        if not user_id:
             return JsonResponse({'status': 'error', 'error': 'Session expired.'})
        
        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': 'Account not found.'})

        # --- Resend Cooldown Check (Backend enforcement) ---
        recent_otp = OTP.objects.filter(
            user=user, 
            otp_type='forgot', 
            created_at__gte=timezone.now() - timedelta(seconds=RESEND_COOLDOWN_SECONDS) 
        ).first()

        if recent_otp:
            time_since_last_send = (timezone.now() - recent_otp.created_at).total_seconds()
            wait_time = max(0, RESEND_COOLDOWN_SECONDS - int(time_since_last_send))
            return JsonResponse({'status': 'error', 'error': f'Please wait {wait_time} seconds before resending.'}, status=429)

        # Clean old OTPs and generate new one
        OTP.objects.filter(user=user, otp_type='forgot', is_used=False).delete()
        otp_obj = OTP.objects.create(user=user, otp_type='forgot')
        
        # Update timestamp when new OTP is sent
        request.session['otp_sent_timestamp'] = int(time.time()) 
        # Since this is a new session flow, we should allow the view to load once more
        request.session['is_first_otp_view'] = True
        
        send_mail(
            subject='Your New OTP',
            message=f'Your new OTP is {otp_obj.otp_code}. It is valid for {OTP_VALIDITY_SECONDS} seconds.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.user_email],
            fail_silently=False
        )
        return JsonResponse({'status':'ok'})
        
    return JsonResponse({'status':'error', 'error':'Invalid method.'})


# --- 5. Reset Password Final Step ---
def reset_password_view(request):
    """Handles the final password reset submission."""
    # RELOAD/SESSION CHECK: Redirect if verification status is lost
    if not request.session.get('otp_verified'):
        messages.error(request, 'Security check failed. Please verify the OTP again.')
        return redirect('verify_otp') 

    if request.method == "POST":
        user_id = request.session.get('user_id')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # 1. Password Match Check
        if new_password != confirm_password:
            messages.error(request, '⚠️ Passwords do not match. Please check again.')
            return redirect('verify_otp') 

        # 2. Password Length Check (4 to 10 characters)
        if len(new_password) < 4 or len(new_password) > 10:
            messages.error(request, '⚠️ Password length must be between 4 and 10 characters.')
            return redirect('verify_otp')

        try:
            user = CustomUser.objects.get(pk=user_id)
            
            # 3. Update password in the database
            user.set_password(new_password)
            user.save()

            # 4. Clear session and redirect to Login
            request.session.pop('user_id', None)
            request.session.pop('user_contact', None)
            request.session.pop('otp_verified', None)
            request.session.pop('otp_sent_timestamp', None)
            request.session.pop('is_first_otp_view', None) # Clear the flag
            
            messages.success(request, 'Your password has been successfully reset. Please log in.')
            
            return redirect('login_user') 
            
        except CustomUser.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('forgot_password')

    return redirect('forgot_password')

# End User -->

# Start Admin -->
# adminpanel/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import AdminUser

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .models import AdminUser

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .models import AdminUser


def admin_login(request):
    if request.method == "POST":
        # 🔹 HTML ke name attributes ke hisaab se
        login_input = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        if not login_input or not password:
            messages.error(request, "All fields are required")
            return redirect("admin_login")

        try:
            # 🔹 email ya username dono se login
            admin = AdminUser.objects.get(
                Q(email__iexact=login_input) |
                Q(username__iexact=login_input)
            )
        except AdminUser.DoesNotExist:
            messages.error(request, "Invalid username or email")
            return redirect("admin_login")

        # 🔐 Password check (hashed)
        if not admin.check_password(password):
            messages.error(request, "Invalid password")
            return redirect("admin_login")

        if not admin.is_active:
            messages.error(request, "Your account is disabled")
            return redirect("admin_login")

        # ✅ Login success → session set
        request.session["admin_id"] = admin.admin_id
        request.session["admin_username"] = admin.username
        request.session.set_expiry(60 * 60 * 2)  # 2 hours session

        return redirect("admin_dashboard")

    return render(request, "admin/dashboard/admin_login.html")


def admin_dashboard(request):
    if not request.session.get("admin_id"):
        return redirect("admin_login")

    return render(request, "admin/dashboard/admin_dashboard.html")


def admin_logout(request):
    print("🔥 ADMIN LOGOUT VIEW HIT 🔥")
    request.session.pop("admin_id", None)
    request.session.pop("admin_username", None)
    return redirect("admin_login")


from django.db.models import Sum, Count
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from django.shortcuts import render
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from dateutil.relativedelta import relativedelta

def indian_format(amount):
    """
    Converts a number (int or float) to Indian Rupee format (e.g., 1,23,456.78).
    
    Yeh function:
    1. Integer aur Decimal parts ko alag karta hai.
    2. Integer part ko Indian style (Lakh/Crore) mein format karta hai.
    3. Final result mein '₹' symbol aur decimal part (agar hai) shamil karta hai.
    """
    if amount is None or amount == 0:
        return "₹0"
    
    try:
        # Number ko round off karke string mein convert karein, 2 decimal places tak
        # Jaise ki '123456.78' ya '123456'
        s = f"{float(amount):.2f}"
    except (TypeError, ValueError):
        return f"₹{amount}" # Agar invalid input ho
        
    # Decimal aur Integer parts ko alag karein
    if '.' in s:
        main, decimal = s.split('.')
        # Agar decimal part sirf '00' hai, to use chhod dein
        if decimal == '00':
            decimal = None
    else:
        main, decimal = s, None
        
    # Integer part ko ensure karein ki woh integer hi ho
    main = main.lstrip('0') or '0' # Leading zeros hatayein
    
    # Negative sign check karein
    is_negative = main.startswith('-')
    if is_negative:
        main = main[1:] # Negative sign ko alag rakhein

    # --- Indian Format Logic ---
    if len(main) <= 3:
        formatted_main = main
    else:
        last_three = main[-3:]
        other_digits = main[:-3]
        formatted_other = ''
        
        while other_digits:
            # Har do digits (Lakh, Crore) ke baad comma lagaayein
            chunk = other_digits[-2:]
            
            # Agar formatted_other pehle se set hai to comma lagayein
            if formatted_other:
                formatted_other = chunk + ',' + formatted_other
            else:
                formatted_other = chunk
            
            other_digits = other_digits[:-2]

        formatted_main = f"{formatted_other},{last_three}"
        
    # Final String construct karein
    final_amount = formatted_main
    if decimal:
        final_amount = f"{final_amount}.{decimal}"
        
    if is_negative:
        return f"-₹{final_amount}"
    
    return f"₹{final_amount}"

# Helper function 2: Growth Percentage Calculation
def calculate_growth_percentage(current, previous):
    """Calculates growth percentage between current and previous values."""
    if previous == 0 and current == 0:
        return 0.0
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return ((current - previous) / previous) * 100

# --- The Main View Function ---
from django.db.models import Count, Sum, Q, F # Ensure F and Q are imported
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import json # Ensure json is imported


def admin_dashboard(request):
    # --- 1. तारीखों की गणना (Calculate Dates) ---
    today = timezone.now().date()
    # ... (Lines 4-13 unchanged) ...
    start_of_current_month = today.replace(day=1)
    end_of_current_month = today # आज तक की अवधि
    
    start_of_last_month = start_of_current_month - relativedelta(months=1)
    end_of_last_month = start_of_current_month - relativedelta(days=1)
    
    # --- 2. टोटल रेवेन्यू (Total Revenue) ---
    current_revenue_data = Order.objects.filter(
        created_at__gte=start_of_current_month, created_at__lte=end_of_current_month
    ).aggregate(total=Sum('total_amount'))
    current_revenue = current_revenue_data['total'] or 0.0

    total_revenue_data = Order.objects.aggregate(total=Sum('total_amount'))
    total_revenue = total_revenue_data['total'] or 0.0

    last_month_revenue_data = Order.objects.filter(
        created_at__gte=start_of_last_month, created_at__lte=end_of_last_month
    ).aggregate(total=Sum('total_amount'))
    last_month_revenue = last_month_revenue_data['total'] or 0.0

    revenue_growth_percentage = calculate_growth_percentage(current_revenue, last_month_revenue)
    
    # --- 3. टोटल ऑर्डर्स (Total Orders) ---
    total_orders = Order.objects.count() 
    last_month_orders_count = Order.objects.filter(
        created_at__gte=start_of_last_month, created_at__lte=end_of_last_month
    ).count()
    current_orders_count = Order.objects.filter(
        created_at__gte=start_of_current_month, created_at__lte=end_of_current_month
    ).count()
    orders_growth_percentage = calculate_growth_percentage(current_orders_count, last_month_orders_count)

    # --- 4. टोटल प्रोडक्ट्स (Total Products) ---
    total_products = Product.objects.count()
    
    # --- 5. टोटल कस्टमर्स (Total Customers) ---
    all_active_customers = User.objects.filter(is_admin=False, is_staff=False, is_active=True)
    # ... (Lines 52-67 unchanged) ...
    total_customers = all_active_customers.count()
    
    last_month_customers_count = all_active_customers.filter(
        user_created_at__gte=start_of_last_month, user_created_at__lte=end_of_last_month
    ).count()
    current_customers_count = all_active_customers.filter(
        user_created_at__gte=start_of_current_month, user_created_at__lte=end_of_current_month
    ).count()
    customers_growth_percentage = calculate_growth_percentage(current_customers_count, last_month_customers_count)

    # --- 6. एवरेज ऑर्डर वैल्यू (Average Order Value - AOV) ---
    current_aov = current_revenue / current_orders_count if current_orders_count > 0 else 0.0
    last_month_aov = last_month_revenue / last_month_orders_count if last_month_orders_count > 0 else 0.0
    aov_growth_percentage = calculate_growth_percentage(current_aov, last_month_aov)

    # --- 7. कन्वर्जन रेट (Conversion Rate - CR) ---
    TOTAL_VISITORS_CURRENT_MONTH = 1000 
    TOTAL_VISITORS_LAST_MONTH = 950
    current_conversion_rate = round(
        (current_orders_count / TOTAL_VISITORS_CURRENT_MONTH) * 100, 2
    ) if TOTAL_VISITORS_CURRENT_MONTH > 0 else 0.0
    last_month_conversion_rate = round(
        (last_month_orders_count / TOTAL_VISITORS_LAST_MONTH) * 100, 2
    ) if TOTAL_VISITORS_LAST_MONTH > 0 else 0.0
    cr_growth_percentage = calculate_growth_percentage(current_conversion_rate, last_month_conversion_rate)

    # --- 8. अलर्ट्स और हालिया ऑर्डर्स (Alerts and Recent Orders) ---
    # ... (Lines 84-117 unchanged) ...
    LOW_STOCK_THRESHOLD = 10 
    out_of_stock_count = Product.objects.filter(pro_stock=0).count() 
    low_in_stock_count = Product.objects.filter(
        pro_stock__gt=0, pro_stock__lt=LOW_STOCK_THRESHOLD
    ).count()
    low_stock_products_combined = Product.objects.filter(
        pro_stock__lte=LOW_STOCK_THRESHOLD 
    ).order_by('-pro_stock') 
    pending_orders_count = Order.objects.filter(payment_status='Pending').count() 
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:5]

    # ✅ सुधार: प्रोडक्ट्स को Fetch करें और कीमतें फॉर्मेट करें
    all_products_qs = Product.objects.select_related('cat_id').order_by('-pro_created_at')
    
    formatted_products = []
    for product in all_products_qs:
        # pro_price को फॉर्मेट करें (no decimal, Indian format)
        product.formatted_price = indian_format(product.pro_price)
        
        # pro_old_price (या pro_mrp) को फॉर्मेट करें
        if hasattr(product, 'pro_old_price') and product.pro_old_price and product.pro_old_price > product.pro_price:
            product.formatted_old_price = indian_format(product.pro_old_price)
        else:
            product.formatted_old_price = None

        formatted_products.append(product)

    # --- ✅ NEW: Fetch & Annotate Customer Data for Table ---
    
    # Assumption: User model has a Reverse Foreign Key relationship to Order model (named 'order')
    all_customers_with_stats = all_active_customers.annotate(
        # Calculate Total Orders Count for each user
        order_count=Count('order', distinct=True), 
        # Calculate Total Spent (Sum of 'total_amount' in related Orders)
        total_spent_raw=Sum('order__total_amount', filter=Q(order__payment_status='Paid')) 
    ).order_by('-user_created_at') 

    formatted_customers = []
    for customer in all_customers_with_stats:
        # User ki profile image ke liye initials nikalna
        initials = "".join(name[0].upper() for name in customer.user_name.split())[:2] if customer.user_name else 'CU'
        
        # Total Spent ko Indian format mein convert karna
        spent_amount = customer.total_spent_raw if customer.total_spent_raw is not None else 0.0
        
        # --- ✅ LOGIC ADDED: Most Used Address Calculation ---
        most_used_address_qs = Order.objects.filter(
            user=customer,
            address__isnull=False
        ).values(
            'address__address_line', 
            'address__locality', 
            'address__city', 
            'address__pincode'
        ).annotate(
            usage_count=Count('address')
        ).order_by('-usage_count')
        
        most_used_address = 'N/A'
        if most_used_address_qs.exists():
            top_address = most_used_address_qs.first()
            address_parts = [
                top_address.get('address__address_line'),
                top_address.get('address__locality'),
                top_address.get('address__city'),
                top_address.get('address__pincode')
            ]
            most_used_address = ", ".join(filter(None, address_parts))
            
        # --- ✅ LOGIC FIXED: Recent Orders Data for Modal ---
        # 💡 FIX: Yeh query har order ko fetch karti hai, chahe status Delivered ho ya nahi.
        recent_orders_qs = Order.objects.filter(user=customer).order_by('-created_at')[:4] # Top 4 orders
        
        recent_orders_list = []
        for order in recent_orders_qs:
            # ⭐️ सुधार 1: delivery_status field fetch karen (agar Order model mein hai)
            order_status = getattr(order, 'delivery_status', 'N/A')
            
            recent_orders_list.append({
                'id': f"ORD-{order.order_id}", 
                # '%#m/%#d/%Y' will format as M/D/YYYY (e.g., 1/5/2025)
                'date': order.created_at.strftime('%#m/%#d/%Y') if order.created_at else 'N/A', 
                'amount': indian_format(order.total_amount),
                'status': order_status, # ⭐️ सुधार 2: Status field JSON mein include kiya
            })
        
        # ⭐️ FIX APPLIED: recent_orders_json ko poore array ke saath dump kiya gaya hai.
        recent_orders_json = json.dumps(recent_orders_list) 
        
        customer_data = {
            'id': customer.user_id, # Must include ID for linking
            'initials': initials,
            'user_name': customer.user_name,
            'user_email': customer.user_email,
            'user_number': customer.user_number,
            
            # ✅ UPDATED: Most Used Address
            'location': most_used_address, 
            
            'order_count': customer.order_count,
            'total_spent_raw': spent_amount,
            'total_spent_formatted': indian_format(spent_amount),
            
            # ✅ NEW: JSON data for Recent Orders Modal (Full JSON array string)
            'recent_orders_json': recent_orders_json,
        }
        formatted_customers.append(customer_data)


    # --- 9. कॉन्टेक्स्ट (Context) ---
    # ... (Lines 226-267 unchanged) ...
    categories_with_counts = Category.objects.annotate(
        product_count=Count('product')
    ).order_by('-product_count', 'cat_name')

    all_orders = Order.objects.select_related('user').order_by('-created_at')

    pending_count = Order.objects.filter(order_status__iexact='Pending').count()
    processing_count = Order.objects.filter(order_status__iexact='Processing').count()
    shipped_count = Order.objects.filter(order_status__iexact='Shipped').count()
    delivered_count = Order.objects.filter(order_status__iexact='Delivered').count()

    context = {
        'all_orders': all_orders,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'shipped_count': shipped_count,
        'delivered_count': delivered_count,

        # रेवेन्यू डेटा
        'total_revenue': indian_format(total_revenue),
        'revenue_growth_percentage': round(revenue_growth_percentage, 1),
        
        # ऑर्डर्स डेटा
        'total_orders': total_orders, 
        'orders_growth_percentage': round(orders_growth_percentage, 1),
        
        # AOV डेटा
    'total_aov': indian_format(current_aov),  # ✅ Indian format with commas
    'aov_growth_percentage': round(aov_growth_percentage, 1),

    # CR डेटा
    'conversion_rate': f"{current_conversion_rate:.2f}",  # ✅ Always 2 decimals
    'cr_growth_percentage': round(cr_growth_percentage, 1),
        
        # प्रोडक्ट्स डेटा
        'total_products': total_products,
        
        # कस्टमर्स डेटा
        'total_customers': total_customers,
        'customers_growth_percentage': round(customers_growth_percentage, 1),
        
        # अलर्ट्स
        'out_of_stock_count': out_of_stock_count, 
        'low_in_stock_count': low_in_stock_count, 
        'low_stock_count': low_stock_products_combined.count(), 
        'pending_orders_count': pending_orders_count, 

        # Low Stock Products की सूची
        'low_stock_products': low_stock_products_combined,
        'low_stock_threshold': LOW_STOCK_THRESHOLD, 

        # हालिया ऑर्डर्स
        'recent_orders': recent_orders,
        
        # फ़ॉर्मेटेड प्रोडक्ट्स की सूची
        'all_products': formatted_products,

        'categories': categories_with_counts,
        
        # ✅ NEW: Customer Data for Table
        'customer_list': formatted_customers, 
    }
    return render(request, 'admin/dashboard/admin_dashboard.html', context)
# End Admin
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from .models import Order, OrderItem


def sales_trend(request):
    qs = (
        Order.objects
        .filter(payment_status="Paid", order_status="delivered")
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Count("order_id"))
        .order_by("date")
    )

    return JsonResponse({
        "labels": [str(x["date"]) for x in qs],
        "values": [x["total"] for x in qs]
    })

from django.http import JsonResponse
from django.utils import timezone
import time
from datetime import datetime, timedelta

from .models import Category, OrderItem

def sales_by_category_api(request):
    days = int(request.GET.get("days", 7))
    start_date = timezone.now() - timedelta(days=days)

    labels = []
    values = []
    colors = []

    for cat in Category.objects.all():
        qs = OrderItem.objects.filter(
            pro_id__cat_id=cat,
            order_id__order_status="delivered",
            order_id__payment_status="Paid",
            order_id__created_at__gte=start_date
        )

        # 🔥 ONLY ORDER COUNT (distinct orders)
        total_orders = qs.values("order_id").distinct().count()

        labels.append(cat.cat_name)
        values.append(total_orders)

        hue = abs(hash(cat.cat_name)) % 360
        colors.append(f"hsl({hue}, 65%, 55%)")

    return JsonResponse({
        "labels": labels,
        "values": values,
        "colors": colors
    })

from django.http import JsonResponse
from django.db.models import Count, F
from django.utils import timezone
import time
from datetime import datetime, timedelta

from .models import OrderItem

def top_selling_products_api(request):
    days = int(request.GET.get("days", 30))
    
    # 1. Start Date की गणना
    if days == 1:
        # आज के दिन को 00:00:00 पर सेट करें
        start_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # पिछले N दिनों के लिए
        start_datetime = timezone.now() - timedelta(days=days)

    # 2. Query Logic
    qs = (
        OrderItem.objects.filter(
            order_id__order_status="Delivered",
            order_id__payment_status="Paid",
            order_id__created_at__gte=start_datetime
        )
        # 3. केवल वही प्रोडक्ट दिखाएं जिनकी बिक्री 1 या उससे ज़्यादा हो (वैकल्पिक, लेकिन अच्छा)
        # अगर आप OrderItem से फ़िल्टर कर रहे हैं, तो यह ज़रूरी नहीं है क्योंकि qs में केवल बेचे गए आइटम होंगे।
        
        .values(name=F("pro_id__pro_name"))
        .annotate(total_orders=Count("order_id")) 
        .order_by("-total_orders")[:7] 
    )

    labels = [x["name"] for x in qs]
    values = [x["total_orders"] for x in qs]

    # ✅ REMOVED: Placeholders (Product 6, Product 7) डालने वाला यह सेक्शन हटा दिया गया है।
    # अब सिर्फ वही प्रोडक्ट दिखेंगे जो बिके हैं (यानी जिनका 'total_orders' > 0 है)।

    return JsonResponse({"labels": labels, "values": values})

# Start Category -->
def add_category(request):

    if request.method == "POST":
        cat_name = request.POST.get('cat_name') 

        Category.objects.create(
            cat_name = cat_name,
        )
        return redirect('/admin-dashboard/')

    return render(request, 'admin/category/add_category.html')

def show_categoryData(request):
    categoryData = Category.objects.all()
    context = {'categoryData': categoryData}
    return render(request, 'admin/category/show_categoryData.html', context)

def update_category(request,id):
    upd_id = Category.objects.get(cat_id = id)
    
    if request.method == "POST":
        cat_name = request.POST.get('cat_name')

        if cat_name:
            upd_id.cat_name = cat_name

        upd_id.save()
        return redirect('/admin-dashboard/')
        
    context = {"updData":upd_id}

    return render(request, 'admin/category/update_category.html', context)

def delete_category(request,id):
    deleted_id = Category.objects.get(cat_id = id)
    deleted_id.delete()
    return redirect('/admin-dashboard/')
# End Category -->
     
# Start Product -->
def add_product(request): 
    if request.method == "POST":
        cat_id = request.POST.get('cat_id')
        pro_name = request.POST.get('pro_name')
        pro_brand = request.POST.get('pro_brand')
        pro_description = request.POST.get('pro_description')
        pro_price = request.POST.get('pro_price')
        pro_mrp = request.POST.get('pro_mrp')
        pro_stock = request.POST.get('pro_stock')
        pro_image = request.FILES.get('pro_image')

        #New fields
        ram = request.POST.get('ram')
        storage = request.POST.get('storage')
        display = request.POST.get('display')
        rear_camera = request.POST.get('rear_camera')
        front_camera = request.POST.get('front_camera')
        battery = request.POST.get('battery')
        processor = request.POST.get('processor')

        # Category object fetch kar raha hai
        category = Category.objects.get(cat_id=cat_id)

        Product.objects.create(
            cat_id = category,  # idddd
            pro_name = pro_name,
            pro_brand = pro_brand,
            pro_description = pro_description,
            pro_price = pro_price,
            pro_mrp = pro_mrp,
            pro_stock = pro_stock,
            pro_image = pro_image,
            ram=ram,
            storage=storage,
            display=display,
            rear_camera=rear_camera,
            front_camera=front_camera,
            battery=battery,
            processor=processor
        )
        return redirect('/admin-dashboard/')
    
    catData = Category.objects.all()
    context = {'catData': catData}

    return render(request, 'admin/product/add_product.html', context)

def show_productData(request):
    productData = Product.objects.all()
    context = {'productData': productData}
    return render(request, 'admin/product/show_productData.html', context)

def update_product(request,id):
    upd_id = Product.objects.get(pro_id = id)

    if request.method == "POST":
        cat_id = request.POST.get('cat_id')
        pro_name = request.POST.get('pro_name')
        pro_brand = request.POST.get('pro_brand')
        pro_description = request.POST.get('pro_description')
        pro_price = request.POST.get('pro_price')
        pro_mrp = request.POST.get('pro_mrp')
        pro_stock = request.POST.get('pro_stock')
        pro_image = request.FILES.get('pro_image')
        # 🔹 New fields
        ram = request.POST.get('ram')
        storage = request.POST.get('storage')
        display = request.POST.get('display')
        rear_camera = request.POST.get('rear_camera')
        front_camera = request.POST.get('front_camera')
        battery = request.POST.get('battery')
        processor = request.POST.get('processor')


        upd_id.cat_id_id = cat_id
        upd_id.pro_name = pro_name
        upd_id.pro_brand = pro_brand
        upd_id.pro_description = pro_description
        upd_id.pro_price = pro_price
        upd_id.pro_mrp = pro_mrp
        upd_id.pro_stock = pro_stock
        upd_id.ram = ram
        upd_id.storage = storage
        upd_id.display = display
        upd_id.rear_camera = rear_camera
        upd_id.front_camera = front_camera
        upd_id.battery = battery
        upd_id.processor = processor
        
        if pro_image:
            upd_id.pro_image = pro_image

        upd_id.save()   
        return redirect('/admin-dashboard/')
    
    catData = Category.objects.all()
    context = {'updData': upd_id, 'catData': catData}
    
    return render(request, 'admin/product/update_product.html', context)

def delete_product(request,id):
    deleted_id = Product.objects.get(pro_id = id)
    deleted_id.delete()
    return redirect('/admin-dashboard/')


# End Product -->


