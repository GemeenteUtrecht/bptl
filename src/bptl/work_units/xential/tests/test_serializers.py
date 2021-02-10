from django.test import TestCase

from bptl.work_units.xential.serializers import CallbackDataSerializer


class CallbackDataSerializerTests(TestCase):
    def test_correct_base64_data(self):
        b64_data = "SGVsbG8hIFRoaXMgaXMgc29tZSB0ZXN0IGRhdGEgOkQ="
        uuid = "a4664ccb-259e-4107-b800-d8e5a764b9dd"

        serializer = CallbackDataSerializer(
            data={"bptl_ticket_uuid": uuid, "document": b64_data}
        )

        self.assertTrue(serializer.is_valid())

    def test_wrong_char_base64_data(self):
        b64_data = "SGVsbG8hIFRoaXMgaXMgc29tZSB0ZXN0IGRhdGEgOkQ=!#$"
        uuid = "a4664ccb-259e-4107-b800-d8e5a764b9dd"

        serializer = CallbackDataSerializer(
            data={"bptl_ticket_uuid": uuid, "document": b64_data}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("document", serializer.errors)
        self.assertEqual("Non-base64 digit found", serializer.errors["document"][0])

    def test_wrong_padding_base64_data(self):
        b64_data = "SGVsbG8hIFRoaXMgaXMgc29tZSB0ZXN0IGRhdGEgOkQ"
        uuid = "a4664ccb-259e-4107-b800-d8e5a764b9dd"

        serializer = CallbackDataSerializer(
            data={"bptl_ticket_uuid": uuid, "document": b64_data}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("document", serializer.errors)
        self.assertEqual(
            "The provided base64 data has incorrect padding",
            serializer.errors["document"][0],
        )
