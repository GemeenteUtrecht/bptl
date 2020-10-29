from rest_framework import exceptions, serializers

from bptl.tasks.base import MissingVariable


class ZacUserDetailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)
    firstName = serializers.CharField(required=True, allow_blank=True)
    lastName = serializers.CharField(required=True, allow_blank=True)
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        name = f"{obj['firstName']} {obj['lastName']}"
        name = name.strip(" ")
        if not name:
            return "Medewerker"
        else:
            return name


class ZacUsersDetailsSerializer(serializers.Serializer):
    results = ZacUserDetailSerializer(many=True)

    def is_valid(self, raise_exception=False):
        codes_to_catch = (
            "code='required'",
            "code='blank'",
        )

        try:
            valid = super().is_valid(raise_exception=raise_exception)
            return valid
        except Exception as e:
            if isinstance(e, exceptions.ValidationError):
                error_codes = str(e.detail)
                if any(code in error_codes for code in codes_to_catch):
                    raise MissingVariable(e.detail)
            else:
                raise e
