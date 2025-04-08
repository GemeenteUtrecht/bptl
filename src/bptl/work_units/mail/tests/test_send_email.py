import copy

from django.core import mail
from django.test import TestCase

from django_camunda.utils import serialize_variable

from bptl.camunda.models import ExternalTask
from bptl.tasks.base import MissingVariable

from ..tasks import SendEmailTask


class SendEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task_dict = {
            "topic_name": "send-email",
            "worker_id": "test-worker-id",
            "task_id": "test-task-id",
            "variables": {
                "sender": serialize_variable(
                    {"email": "kees.koos@test.test", "name": "Kees Koos"}
                ),
                "receiver": serialize_variable(
                    {
                        "email": "jan.janssen@test.test",
                        "name": "Jan Janssen",
                        "assignee": "user:janjansen",
                    }
                ),
                "email": serialize_variable(
                    {"subject": "Vakantiepret", "content": "Dit is pas leuk."}
                ),
                "template": serialize_variable("generiek"),
                "context": serialize_variable(
                    {
                        "deadline": "2020-04-20",
                        "doReviewUrl": "test.com?uuid=123456",
                        "reviewType": "advies",
                    }
                ),
            },
        }

    def test_send_email_happy(self):
        task = ExternalTask.objects.create(**self.task_dict)
        send_mail = SendEmailTask(task)
        send_mail.perform()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertEqual(
            email.body,
            """Beste Jan Janssen,\n\nDit is pas leuk.\n\nMet vriendelijke groeten,\n\nKees Koos\n\nDit is een automatisch gegenereerd bericht vanuit de zaakafhandelcomponent; het is niet mogelijk via dit bericht te reageren.""",
        )
        self.assertEqual(email.subject, "Vakantiepret")
        self.assertEqual(email.to, ["jan.janssen@test.test"])
        self.assertEqual(email.reply_to, ["kees.koos@test.test"])

    def test_send_email_missing_variable(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"].pop("receiver")
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)

        with self.assertRaises(Exception) as e:
            send_mail.perform()
        self.assertEqual(type(e.exception), MissingVariable)
        self.assertTrue("receiver" in e.exception.args[0])
        self.assertTrue("Dit veld is vereist." in e.exception.args[0]["receiver"][0])

        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["sender"] = serialize_variable(
            {"email": "", "name": "Kees Koos"}
        )
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)
        with self.assertRaises(Exception) as e:
            send_mail.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertTrue("sender" in e.exception.args[0])
        self.assertTrue("email" in e.exception.args[0]["sender"])
        self.assertTrue(
            "Dit veld mag niet leeg zijn." in e.exception.args[0]["sender"]["email"][0]
        )

    def test_send_email_review_template(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["template"] = serialize_variable("advies")
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)
        send_mail.perform()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            """Beste Jan Janssen,

We willen je op de hoogte brengen van een belangrijke ontwikkeling met betrekking tot zaak:  met omschrijving: "", waarbij jouw advies essentieel is. De deadline hiervoor is 20-04-2020.

Om het proces vlot te laten verlopen en een tijdige afhandeling te waarborgen, hebben we jouw medewerking nodig. We vragen je vriendelijk om jouw benodigde advies te behandelen voor 20-04-2020.

Volg eenvoudig deze stappen om jouw advies te geven:

    Klik op test.com?uuid=123456&amp;assignee=user%3Ajanjansen om direct naar de  te gaan.

Of volg de volgende stappen:

    Log in op .
    Navigeer naar het tabblad "Acties".
    Selecteer de advies-"actie".
    Volg de instructies op het scherm om de  te voltooien.

Jouw medewerking is essentieel voor een snelle afhandeling. Dank je wel voor je prompte aandacht. Dit is pas leuk.

Met vriendelijke groeten,

Kees Koos

Dit is een automatisch gegenereerd bericht vanuit de zaakafhandelcomponent; het is niet mogelijk via dit bericht te reageren.""",
        )
        self.assertEqual(email.subject, "Vakantiepret")
        self.assertEqual(email.to, ["jan.janssen@test.test"])

    def test_send_email_review_template_empty_content(self):
        task_dict = {**self.task_dict}
        task_dict["variables"]["email"] = serialize_variable(
            {"subject": "mooi onderwerp", "content": ""}
        )
        task_dict["variables"]["template"] = serialize_variable("advies")
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)
        send_mail.perform()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            """Beste Jan Janssen,

We willen je op de hoogte brengen van een belangrijke ontwikkeling met betrekking tot zaak:  met omschrijving: "", waarbij jouw advies essentieel is. De deadline hiervoor is 20-04-2020.

Om het proces vlot te laten verlopen en een tijdige afhandeling te waarborgen, hebben we jouw medewerking nodig. We vragen je vriendelijk om jouw benodigde advies te behandelen voor 20-04-2020.

Volg eenvoudig deze stappen om jouw advies te geven:

    Klik op test.com?uuid=123456&amp;assignee=user%3Ajanjansen om direct naar de  te gaan.

Of volg de volgende stappen:

    Log in op .
    Navigeer naar het tabblad "Acties".
    Selecteer de advies-"actie".
    Volg de instructies op het scherm om de  te voltooien.

Jouw medewerking is essentieel voor een snelle afhandeling. Dank je wel voor je prompte aandacht. 

Met vriendelijke groeten,

Kees Koos

Dit is een automatisch gegenereerd bericht vanuit de zaakafhandelcomponent; het is niet mogelijk via dit bericht te reageren.""",
        )
        self.assertEqual(email.subject, "mooi onderwerp")
        self.assertEqual(email.to, ["jan.janssen@test.test"])

    def test_send_email_invalid_review_template(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["template"] = serialize_variable("lelijk")
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)

        with self.assertRaises(Exception) as e:
            send_mail.perform()

        self.assertEqual(type(e.exception), MissingVariable)
        self.assertTrue(
            '"lelijk" is een ongeldige keuze.' in e.exception.args[0]["template"][0]
        )

    def test_send_email_nen2580_template(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["email"] = serialize_variable(
            {
                "subject": "Toelichting op niet akkoord",
                "content": "Ik kan hier echt niet mee akkoord gaan.",
            }
        )
        task_dict["variables"]["template"] = serialize_variable("nen2580")
        task_dict["variables"]["context"] = serialize_variable({})
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)
        send_mail.perform()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            """Beste Jan Janssen,

Wij hebben de door jou aangeleverde documenten bekeken en vragen je de onderstaande wijzigingen hier te doen:

Ik kan hier echt niet mee akkoord gaan.

De gewijzigde documenten kun je opnieuw indienen.

Met vriendelijke groeten,

Kees Koos

Dit is een automatisch gegenereerd bericht vanuit de zaakafhandelcomponent; het is niet mogelijk via dit bericht te reageren.""",
        )
        self.assertEqual(email.subject, "Toelichting op niet akkoord")

    def test_send_email_verzoek_afgehandeld_template(self):
        task_dict = copy.deepcopy(self.task_dict)
        task_dict["variables"]["email"] = serialize_variable(
            {
                "subject": "Betreft antwoord op accorderingsvraag voor some-zaak-omschrijving",
                "content": "some content",
            }
        )
        task_dict["variables"]["template"] = serialize_variable("verzoek_afgehandeld")
        task_dict["variables"]["context"] = serialize_variable(
            {"zaakDetailUrl": "http://some-detail-url.com/"}
        )
        task = ExternalTask.objects.create(**task_dict)
        send_mail = SendEmailTask(task)
        send_mail.perform()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(
            email.body,
            """Beste Jan Janssen,

We willen je graag informeren dat er zojuist antwoord is gegeven op je  binnen zaak: .

Volg eenvoudig deze stappen om de reactie te bekijken:

    Klik op http://some-detail-url.com/  om direct naar de zaak te gaan.
    Navigeer naar het tabblad "Acties".
    Kijk onderaan de pagina bij "Advisering en accordering".
    Klik op de accordering om meer informatie te zien.

some content

Met vriendelijke groeten,

Kees Koos

Dit is een automatisch gegenereerd bericht vanuit de zaakafhandelcomponent; het is niet mogelijk via dit bericht te reageren.""",
        )
        self.assertEqual(
            email.subject,
            "Betreft antwoord op accorderingsvraag voor some-zaak-omschrijving",
        )
