from django.test import TestCase
from django.urls import reverse, reverse_lazy

from furl import furl

from bptl.accounts.tests.factories import SuperUserFactory, UserFactory


class SuperUserViewTests(TestCase):
    def test_no_superuser(self):
        urls = [
            reverse("index"),  # index
            reverse("admin:index"),  # admin pages
            reverse("camunda:process-instance-list"),  # camunda
            reverse("tasks:taskmapping-list"),  # task mappings
            reverse("tasks:taskmapping-create"),
            reverse("dashboard:task-list"),  # tasks
            reverse("dashboard:task-detail", args=[1]),  # index
        ]
        user = UserFactory.create()
        self.client.force_login(user)
        for url in urls:
            login_url = furl(reverse("admin:login"))
            login_url.args["next"] = url
            with self.subTest(variant=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    login_url.url,
                    status_code=302,
                    target_status_code=200,
                    msg_prefix="",
                    fetch_redirect_response=True,
                )

    def test_admin(self):
        urls = [
            reverse("index"),  # index
            reverse("admin:index"),  # admin pages
            reverse("camunda:process-instance-list"),  # camunda
            reverse("tasks:taskmapping-list"),  # task mappings
            reverse("tasks:taskmapping-create"),
            reverse("dashboard:task-list"),  # tasks
            reverse("dashboard:task-detail", args=[1]),  # index
        ]
        user = UserFactory.create(is_staff=True)
        self.client.force_login(user)
        for url in urls:
            login_url = furl(reverse("admin:login"))
            login_url.args["next"] = url
            with self.subTest(variant=url):
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    login_url.url,
                    status_code=302,
                    target_status_code=200,
                    msg_prefix="",
                    fetch_redirect_response=True,
                )

    def test_yes_superuser(self):
        urls_200 = [
            reverse("index"),  # index
            reverse("admin:index"),  # admin pages
            reverse("tasks:taskmapping-list"),  # task mappings
            reverse("tasks:taskmapping-create"),
            reverse("dashboard:task-list"),  # tasks
        ]
        user = SuperUserFactory.create(is_staff=True)
        self.client.force_login(user)
        for url in urls_200:
            login_url = furl(reverse("admin:login"))
            login_url.args["next"] = url
            with self.subTest(variant=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

        # expect 404 here because task doesnt exist
        response_404 = self.client.get(reverse("dashboard:task-detail", args=[1]))
        self.assertEqual(response_404.status_code, 404)

        # expect exception here because no camunda mocks
        with self.assertRaises(Exception):
            response_exception = self.client.get(
                reverse("camunda:process-instance-list"),
            )
