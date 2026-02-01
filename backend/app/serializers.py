from rest_framework import serializers

class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=100, 
        min_length=3,
        help_text="Username must be 3-100 characters"
    )
    email = serializers.EmailField(
        help_text="Valid email address required"
    )
    password = serializers.CharField(
        min_length=6,
        max_length=128,
        help_text="Password must be at least 6 characters"
    )
    full_name = serializers.CharField(
        max_length=200,
        help_text="Full name of the user"
    )
    role = serializers.ChoiceField(
        choices=['admin', 'employee', 'customer'],
        default='customer',
        help_text="User role in the system"
    )
    status = serializers.ChoiceField(
        choices=['active', 'inactive', 'suspended'],
        default='active',
        help_text="Account status"
    )

class UserUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=100, min_length=3, required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(min_length=6, max_length=128, required=False)
    full_name = serializers.CharField(max_length=200, required=False)
    role = serializers.ChoiceField(choices=['admin', 'employee', 'customer'], required=False)
    status = serializers.ChoiceField(choices=['active', 'inactive', 'suspended'], required=False)

class CustomerCreateSerializer(serializers.Serializer):
    full_name = serializers.CharField(
        max_length=200,
        help_text="Customer's full name"
    )
    email = serializers.EmailField(
        help_text="Valid email address required"
    )
    password = serializers.CharField(
        min_length=6,
        max_length=128,
        help_text="Password must be at least 6 characters"
    )
    phone = serializers.CharField(
        max_length=20,
        required=False,
        help_text="Customer's phone number"
    )
    delivery_address = serializers.JSONField(
        required=False,
        help_text="Customer's delivery address as JSON object"
    )
    loyalty_points = serializers.IntegerField(
        default=0,
        min_value=0,
        help_text="Customer's loyalty points"
    )

class CustomerUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200, required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(min_length=6, max_length=128, required=False)
    phone = serializers.CharField(max_length=20, required=False)
    delivery_address = serializers.JSONField(required=False)
    loyalty_points = serializers.IntegerField(min_value=0, required=False)

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        help_text="User's email address"
    )
    password = serializers.CharField(
        help_text="User's password"
    )

class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(
        help_text="Valid refresh token"
    )

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        help_text="Current password"
    )
    new_password = serializers.CharField(
        min_length=6,
        max_length=128,
        help_text="New password must be at least 6 characters"
    )
    confirm_password = serializers.CharField(
        help_text="Confirm new password"
    )
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords don't match")
        return data