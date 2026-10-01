# store/context_processors.py

from store.models import Cart
from django.db.models import Sum
from store.models import Order
from store.models import OrderItem


def cart_count_processor(request):
    """
    टेम्पलेट कॉन्टेक्स्ट में कार्ट में मौजूद आइटम की कुल मात्रा जोड़ता है।
    यह लॉग इन (User-based) और गेस्ट (Session-based) दोनों कार्ट को संभालता है।
    """
    cart_items_count = 0
    
    # 1. लॉग इन यूज़र के लिए (User-based Cart)
    if request.user.is_authenticated:
        try:
            # Cart मॉडल में user_id के आधार पर कुल मात्रा का योग करें
            total_quantity_agg = Cart.objects.filter(
                user_id=request.user
            ).aggregate(total=Sum('quantity'))
            
            cart_items_count = total_quantity_agg['total'] or 0
            
        except Exception:
            cart_items_count = 0
    
    # 2. गेस्ट यूज़र के लिए (Session-based Cart)
    else:
        # Django session में कार्ट डेटा खोजने का प्रयास करें। 
        # (मान लीजिए कि आप session में कार्ट आइटम्स की लिस्ट/डिक्ट स्टोर करते हैं)
        # अगर आप session में एक लिस्ट ऑफ प्रोडक्ट IDs स्टोर करते हैं:
        session_cart = request.session.get('cart', {}) 
        
        # 'cart' सेशन डिक्शनरी में मौजूद सभी उत्पादों की मात्रा (quantity) का योग करें।
        # यहाँ 'quantity' को डिक्शनरी वैल्यू के रूप में माना जाता है।
        for item_key, item_data in session_cart.items():
            # यदि आप session में quantity को ऐसे स्टोर करते हैं: {'pro_id_1': {'quantity': 2}, 'pro_id_2': {'quantity': 1}}
            try:
                # यदि item_data एक डिक्शनरी है जिसमें 'quantity' फ़ील्ड है
                cart_items_count += int(item_data.get('quantity', 1))
            except (TypeError, AttributeError):
                # यदि आप session में सिर्फ pro_id स्टोर करते हैं, तो हर item को 1 गिनें।
                 cart_items_count += 1 

    # Note: आपके 'session_cart' के स्टोरेज स्ट्रक्चर के अनुसार quantity सम करने का लॉजिक बदल जाएगा।
    
    return {'cart_item_count': cart_items_count}

def pending_orders_count_processor(request):
    """
    यूज़र के उन ऑर्डर्स की संख्या दिखाता है जो अभी तक 'Delivered' नहीं हुए हैं।
    """
    pending_orders_count = 0
    
    # यह केवल लॉग इन किए गए यूज़र्स के लिए काम करता है
    if request.user.is_authenticated:
        try:
            # Order मॉडल से उन ऑर्डर्स को गिनें जो इस यूजर से जुड़े हैं 
            # और जिनका order_status 'delivered' नहीं है।
            pending_orders_count = Order.objects.filter(
                user=request.user,  # CustomUser का ऑब्जेक्ट
                order_status__in=['confirmed', 'shipped', 'out_for_delivery']
                # वैकल्पिक रूप से, यह भी इस्तेमाल किया जा सकता है:
                # order_status__exclude='delivered' 
            ).count()
            
        except Exception:
            # यदि कोई एरर आए (जैसे मॉडल या DB कनेक्शन में), तो 0 दिखाएँ
            pending_orders_count = 0
            
    # यहाँ 'pending_order_count' वैरिएबल का नाम टेम्पलेट में उपयोग होगा
    return {'pending_order_count': pending_orders_count}


def dashboard_stats_processor(request):
    """
    यूज़र के डिलीवर किए गए ऑर्डर्स और खरीदे गए कुल उत्पादों की संख्या दिखाता है।
    """
    stats = {
        'delivered_order_count': 0,
        'total_products_bought': 0,
    }

    if request.user.is_authenticated:
        try:
            # 1. Delivered Orders Count
            # Order मॉडल में user फ़ील्ड 'user' है, और स्टेटस 'delivered' है
            delivered_orders_count = Order.objects.filter(
                user=request.user, 
                order_status='delivered'
            ).count()
            
            stats['delivered_order_count'] = delivered_orders_count

            # 2. Total Products Bought
            # सिर्फ डिलीवर किए गए ऑर्डर्स की ID प्राप्त करें
            # Order मॉडल में user फ़ील्ड 'user' है
            delivered_order_ids = Order.objects.filter(
                user=request.user, 
                order_status='delivered'
            ).values_list('order_id', flat=True) # order_id आपके Order मॉडल की Primary Key है
            
            # OrderItem टेबल में 'order_id' फ़ील्ड का उपयोग करके फ़िल्टर करें और 'quantity' का योग करें
            total_products = OrderItem.objects.filter(
                order_id__in=delivered_order_ids # OrderItem का ForeignKey 'order_id' है
            ).aggregate(
                total_qty=Sum('quantity') # OrderItem में 'quantity' फ़ील्ड का नाम सही है
            )['total_qty']

            # None (अगर कोई प्रोडक्ट नहीं है) को 0 में बदलें
            stats['total_products_bought'] = total_products if total_products is not None else 0

        except Exception as e:
            # डीबगिंग के लिए इस लाइन को अस्थायी रूप से इस्तेमाल करें:
            # print(f"Context Processor Error: {e}") 
            pass

    return stats