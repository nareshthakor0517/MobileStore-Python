from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
import random

# adminpanel/models.py

from django.contrib.auth.hashers import make_password, check_password

class AdminUser(models.Model):
    admin_id = models.AutoField(primary_key=True)

    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_table"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, user_email, user_name, user_number, password=None):
        if not user_email:
            raise ValueError("Email is required")
        if not user_number:
            raise ValueError("Phone number is required")

        user = self.model(
            user_email=self.normalize_email(user_email),
            user_name=user_name,
            user_number=user_number
        )
        user.set_password(password)  # automatically hash the password
        user.save(using=self._db)
        return user

    def create_superuser(self, user_email, user_name, user_number, password):
        user = self.create_user(
            user_email=user_email,
            user_name=user_name,
            user_number=user_number,
            password=password
        )
        user.is_admin = True
        user.is_staff = True
        user.save(using=self._db)
        return user

# Custom User Model
class CustomUser(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=100)
    user_email = models.EmailField(unique=True)
    user_number = models.CharField(max_length=15, unique=True)
    user_created_at = models.DateTimeField(default=timezone.now)
    user_updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'user_email'      # login with email
    REQUIRED_FIELDS = ['user_name', 'user_number']  # required when creating superuser

    class Meta:
        db_table = 'user_table'

class OTP(models.Model):
    OTP_TYPE_CHOICES = [
        ('forgot', 'Forgot Password'),
        ('reset', 'Reset Password'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=10, choices=OTP_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = str(random.randint(100000, 999999))  # 6-digit OTP
        super().save(*args, **kwargs)

    def is_valid(self):
        """
        Check if OTP is still valid (30s for forgot, 2min for reset)
        """
        now = timezone.now()
        if self.otp_type == 'forgot':
            return (now - self.created_at).total_seconds() <= 30 and not self.is_used
        elif self.otp_type == 'reset':
            return (now - self.created_at).total_seconds() <= 120 and not self.is_used
        return False

    class Meta:
        db_table = 'otp_table'


# Category Model
class Category(models.Model):
    cat_id = models.AutoField(primary_key=True)
    cat_name = models.CharField(max_length=100)
    cat_created_at = models.DateTimeField(auto_now_add=True)
    cat_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'category_table'


# Product Model
class Product(models.Model):
    cat_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    pro_id = models.AutoField(primary_key=True)
    pro_name = models.CharField(max_length=200)
    pro_brand = models.CharField(max_length=100)
    pro_description = models.TextField()
    pro_price = models.DecimalField(max_digits=10, decimal_places=2)
    pro_mrp = models.DecimalField(max_digits=10, decimal_places=2)

    pro_stock = models.PositiveIntegerField()
    pro_status = models.CharField(max_length=20, default='In Stock')
    pro_image = models.ImageField(upload_to='Products_IMG/')
    pro_created_at = models.DateTimeField(auto_now_add=True)
    pro_updated_at = models.DateTimeField(auto_now=True)

    ram = models.CharField(max_length=50)
    storage = models.CharField(max_length=50)
    display = models.CharField(max_length=100)
    rear_camera = models.CharField(max_length=100)
    front_camera = models.CharField(max_length=50)
    battery = models.CharField(max_length=50)
    processor = models.CharField(max_length=100)

    class Meta:
        db_table = 'product_table'

# Cart Model
class Cart(models.Model):
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    pro_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart_id = models.AutoField(primary_key=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'cart_table'
        unique_together = ('user_id', 'pro_id')  # same product ek hi baar per user

    @property
    def total_price(self):
        return self.quantity * self.pro_id.pro_price

# Address

class Address(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('Home', 'Home (All day delivery)'),
        ('Work', 'Work (Delivery between 10 AM - 5 PM)'),
    ]

    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    mobile_number = models.CharField(max_length=10)
    alternate_phone = models.CharField(max_length=10, blank=True, null=True)
    pincode = models.CharField(max_length=10)
    locality = models.CharField(max_length=100)
    address_line = models.TextField()  # Area and Street
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    landmark = models.CharField(max_length=100, blank=True, null=True)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='Home')
    latitude = models.FloatField(null=True, blank=True)   # new
    longitude = models.FloatField(null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'address_table'

# Order Model
class Order(models.Model):
    STATUS_CHOICES = [
        ('confirmed','Confirmed'),
        ('shipped','Shipped'),
        ('out_for_delivery','Out for Delivery'),
        ('delivered','Delivered'),
        ('cancelled','Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('COD','COD'),
    ]

    PAYMENT_STATUS = [
        ('Paid','Paid'),
        ('Unpaid','Unpaid'),
    ]

    order_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="COD")
    order_status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='confirmed')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Unpaid')

    # Courier / tracking
    tracking_number = models.CharField(max_length=128, blank=True, null=True)
    courier_name = models.CharField(max_length=128, blank=True, null=True)

    # Delivery agent details (optional)
    delivery_boy_name = models.CharField(max_length=128, blank=True, null=True)
    delivery_boy_phone = models.CharField(max_length=32, blank=True, null=True)

    # Delivery coordinates (optional)
    delivery_lat = models.FloatField(blank=True, null=True)
    delivery_lng = models.FloatField(blank=True, null=True)

    # Timing & persistence for auto-progress
    created_at = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    expected_days = models.PositiveSmallIntegerField(default=3)

    class Meta:
        db_table = 'order_table'

# OrderItem Model
class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True)

    order_id = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    pro_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    already_reviewed = models.BooleanField(default=False)

    class Meta:
        db_table = 'orderitem_table'
       

class Gst(models.Model):
    gst_id = models.AutoField(primary_key=True)
    order_id = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="business_details")
    gst_number = models.CharField(max_length=20)
    business_name = models.CharField(max_length=255)
    business_address = models.TextField()

    class Meta:
        db_table = "gst_table"


# PhoneComparison Model
class PhoneComparison(models.Model):
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    pro_id = models.JSONField()  # 2-3 product IDs
    details = models.JSONField()      # Specs comparison
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = 'phonecomp_table'


# Review Model
class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    pro_id = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField()
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = 'review_table'
        unique_together = ('user_id', 'pro_id') 
