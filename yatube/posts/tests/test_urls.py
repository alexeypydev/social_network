from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from posts.models import Group, Post


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовое описание группы',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group
        )
        cls.guest_client = Client()
        cls.another_authorized_client = Client()
        cls.authorized_client = Client()

    def setUp(self):
        self.user = User.objects.create_user(username='NoName')
        self.another_authorized_client.force_login(self.user)
        self.authorized_client.force_login(self.post.author)

    def test_urls_exists_at_desired_location(self):
        desired_locations = (
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ),
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )

        for reverse_name in desired_locations:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_url_redirect_anonymous(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        create_url = reverse('posts:post_create')
        target_url = f'/auth/login/?next={create_url}'

        response = self.guest_client.get(create_url, follow=True)

        self.assertRedirects(response, target_url)

    def test_edit_for_author(self):
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/edit/'
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_for_another_author_redirect(self):
        response = self.another_authorized_client.get(
            f'/posts/{self.post.id}/edit/', follow=True
        )

        self.assertRedirects(response, f'/posts/{self.post.id}/')

    def test_task_unexisting_page_url_not_exists_at_desired_location(self):
        response = self.guest_client.get('unexisting_page/')

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_follow_url_exists_at_desired_location(self):
        """Страницы /follow/ доступна авторизованному пользователю."""
        response = self.another_authorized_client.get(
            f'/profile/{self.author.username}/follow/'
        )

        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unfollow_url_exists_at_desired_location(self):
        """Страница /unfollow/ доступна авторизованному пользователю."""
        self.another_authorized_client.get(
            f'/profile/{self.author.username}/follow/'
        )
        response = self.another_authorized_client.get(
            f'/profile/{self.author.username}/unfollow/'
        )

        self.assertEqual(response.status_code, HTTPStatus.FOUND)
