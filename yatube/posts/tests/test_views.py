from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.cache import cache
from django import forms

from posts.models import Post, Group, Follow
from posts.views import POSTS_QUANTITY


User = get_user_model()
TEST_POSTS_FOR_SECOND_PAGE = 3


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testgroup',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group
        )

    def setUp(self):
        self.user = User.objects.create_user(username='Alex')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.post.author)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        response = self.authorized_client.get(reverse('posts:post_create'))

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

        text_field = response.context.get('form').instance.text
        group_field = response.context.get('form').instance.group

        self.assertEqual(text_field, '')
        self.assertEqual(group_field, None)

    def test_edit_post_page_show_correct_context(self):
        """Проверяет, что шаблон create_post cодержит форму
        редактирования поста.
        """
        response = self.authorized_author.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}
                    )
        )

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        text_field = response.context.get('form').instance.text
        group_field = response.context.get('form').instance.group.title

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
                self.assertEqual(text_field, 'Тестовый пост')
                self.assertEqual(group_field, 'Тестовая группа')

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        expected = list(Post.objects.all()[:POSTS_QUANTITY])

        response = self.authorized_client.get(reverse('posts:index'))

        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.
                    get(reverse('posts:group_list',
                                kwargs={'slug': self.group.slug}))
                    )

        expected = list(Post.objects.filter(group=self.group)[:10])

        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.
                    get(reverse('posts:post_detail',
                                kwargs={'post_id': self.post.id}))
                    )

        self.assertEqual(response.context.get('post'), self.post)

    def test_cache_on_index_page(self):
        """Проверка кэширования главной страницы."""
        first_response = self.authorized_client.get(reverse('posts:index'))
        form_data = {
            'text': self.post.text,
            'group': self.group.id
        }

        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        response_aftr_test = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(first_response.content, response_aftr_test.content)

        cache.clear()
        response_clr_cache = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(first_response.content, response_clr_cache.content)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testgroup',
            description='Тестовое описание'
        )
        many_posts = []
        for _ in range(POSTS_QUANTITY + TEST_POSTS_FOR_SECOND_PAGE):
            many_posts.append(Post(
                text='Тестовый пост',
                author=cls.user,
                group=cls.group,
            ))
        Post.objects.bulk_create(many_posts)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        cache.clear()

    def test_first_page_contains_ten_records(self):
        first_pages = (
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ),
        )

        for reverse_name in first_pages:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(len(response.context['page_obj']),
                                 POSTS_QUANTITY
                                 )

    def test_second_page_contains_three_records(self):
        postfix = '?page=2'
        second_pages = (
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}
            ),
        )

        for reverse_name in second_pages:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(f'{reverse_name}{postfix}')
                self.assertEqual(len(response.context['page_obj']),
                                 TEST_POSTS_FOR_SECOND_PAGE
                                 )


class PostOnPagesViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testgroup',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group
        )
        cls.another_post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост без группы'
        )

    def setUp(self):
        self.authorized_author = Client()
        self.authorized_author.force_login(self.post.author)
        cache.clear()

    def test_post_on_all_pages(self):
        post_on_pages = (
            reverse('posts:index'),
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}
                    ),
            reverse('posts:profile',
                    kwargs={'username': self.author.username}
                    )
        )

        for reverse_name in post_on_pages:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertIn(self.post, response.context['posts'])

    def test_post_not_on_all_pages(self):
        post_on_pages = {
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}
                    ): self.another_post,
        }

        for reverse_name, another_post in post_on_pages.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertNotIn(another_post, response.context['posts'])


class TestFollow(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='vasya')
        self.user_2 = User.objects.create_user(username='petya')
        self.user_client = Client()
        self.user_client.force_login(self.user)

    def test_new_author_post_for_user_follow(self):
        Follow.objects.create(user=self.user, author=self.user_2)
        post = Post.objects.create(author=self.user, text='podpiska')
        response = self.user_client.get(reverse('posts:follow_index'))
        for context in response.context['posts']:
            self.assertIn(post, context)

        response_unfollow = self.user_client.get(
            reverse('posts:follow_index'))
        for context in response_unfollow.context['posts']:
            self.assertNotIn(post, context)

    def test_follow(self):
        follower_count = Follow.objects.count()
        self.user_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2})
        )

        self.assertEqual(Follow.objects.count(), follower_count + 1)
        self.assertTrue(Follow.objects.filter(
            user=self.user, author=self.user_2).exists())

    def test_unfollow(self):
        Follow.objects.create(user=self.user, author=self.user_2)
        follower_count = Follow.objects.count()
        self.user_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_2})
        )

        self.assertEqual(Follow.objects.count(), follower_count - 1)
        self.assertFalse(Follow.objects.filter(
            user=self.user, author=self.user_2).exists())
