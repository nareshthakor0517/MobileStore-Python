from django.shortcuts import redirect

class StepAccessMiddleware:
    """
    Controls access to PlaceOrder → OrderSummary → Payment steps.
    Blocks direct URLs, back button, refresh, and prevents re-entering checkout after success.
    """

    ALLOWED_URLS = [
        "/index/",
        "/cart/",
        "/product_detail/",
        "/begin-checkout/",
        "/login/",
        "/register/",
        "/logout/",
        "/showuser/",
        "/add-to-cart/",
        "/remove/",
        "/increase/",
        "/decrease/",
        "/cart/update/",
        # 🎯 ध्यान दें: "/buynow/" को भी ALLOWED_URLS में होना चाहिए
        # ताकि POST request बिना इंटरसेप्ट हुए view तक पहुँच सके।
        "/buynow/", 
    ]

    CHECKOUT_URLS = [
        "/placeOrder/",
        "/save-and-deliver/",
        "/orderSummary/",
        "/payment/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        # Always allow admin
        if path.startswith("/admin-login/") or path.startswith("/admin-logout/"):
            return self.get_response(request)

        # Always allow media
        if path.startswith("/media/"):
            return self.get_response(request)

        # Allow normal public URLs
        for url in self.ALLOWED_URLS:
            if path.startswith(url):
                return self.get_response(request)

        # If checkout already completed → block all checkout pages
        if request.session.get("checkout_completed"):
            for url in self.CHECKOUT_URLS:
                if path.startswith(url):
                    return redirect("/index/")

        # --- UPDATED LOGIC FOR /placeOrder/ ---
        # Block placeOrder direct access
        if path.startswith("/placeOrder/"):
            
            is_buy_now_flow = request.session.get("is_buy_now_flow", False)
            
            # 🎯 FIX: 'step_cart' या 'is_buy_now_flow' में से कोई भी सेट होना चाहिए
            if not request.session.get("step_cart") and not is_buy_now_flow:
                # अगर न तो सामान्य फ़्लो से आया है और न ही buy_now फ़्लो से, तो ब्लॉक करें
                return redirect("/cart/")

            # 💡 CLEANUP: अगर buy_now फ़्लो से आया है, तो इस सेशन वेरिएबल को तुरंत हटा दें
            if is_buy_now_flow:
                del request.session["is_buy_now_flow"]
                
            # चेक पास होने पर रिक्वेस्ट को placeOrder व्यू तक पहुँचाएँ
            return self.get_response(request)
        # --- END OF UPDATED LOGIC ---

        # Block orderSummary direct access
        if path.startswith("/orderSummary/"):
            if not request.session.get("step_placeorder"):
                return redirect("/index/")

        # Block payment direct access
        if path.startswith("/payment/"):
            if not (
                request.session.get("step_cart")
                and request.session.get("step_placeorder")
                and request.session.get("step_ordersummary")
            ):
                return redirect("/index/")

        # Allow all other URLs (non-checkout)
        return self.get_response(request)
    
    

    