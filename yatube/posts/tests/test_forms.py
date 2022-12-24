import tempfile
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Post, Group, Comment


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='HasNoName')
        cls.user = User.objects.create_user(username='NoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testgroup',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
        )
        cls.guest_client = Client()
        cls.author_client = Client()
        cls.not_author_client = Client()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.not_author_client.force_login(self.user)
        self.author_client.force_login(self.post.author)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        new_text = self.post.text
        form_data = {
            'text': new_text,
            'group': self.group.id
        }

        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username': self.author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=new_text,
                group=self.group.id,
            ).exists()
        )

    def test_edit_post_form(self):
        posts_count = Post.objects.count()
        text_changed = 'Тестовый пост изменен'
        form_data = {
            'text': text_changed,
        }

        response = self.author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )

        self.post.refresh_from_db()

        self.assertTrue(
            Post.objects.filter(
                text=text_changed,
            ).exists()
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(self.post.text, text_changed)

    def test_create_post_for_guest(self):
        posts_count = Post.objects.count()
        new_text = self.post.text
        postfix = '?next=%2Fcreate%2F'
        login_url = f'{reverse("users:login")}{postfix}'
        form_data = {
            'text': new_text,
            'group': self.group.id
        }

        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, login_url)
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFalse(
            Post.objects.filter(
                text=new_text,
                group=self.group.id,
            ).exists()
        )

    def test_edit_post_form_for_not_author(self):
        text_changed = 'Тестовый пост изменен'
        login_url = reverse('users:login')
        target_url = f'{login_url}?next=%2Fposts%2F{self.post.id}%2Fedit%2F'
        form_data = {
            'text': text_changed,
        }

        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )

        self.post.refresh_from_db()

        self.assertFalse(
            Post.objects.filter(
                text=text_changed,
            ).exists()
        )
        self.assertRedirects(response, target_url)
        self.assertNotEqual(self.post.text, text_changed)

        response = self.not_author_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.post.refresh_from_db()

        self.assertFalse(
            Post.objects.filter(
                text=text_changed,
            ).exists()
        )
        self.assertNotEqual(self.post.text, text_changed)

    def test_context_image_exists_on_pages(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded,
        }
        image_on_pages = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )

        self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        for reverse_name in image_on_pages:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertContains(response, '<img')

    def test_create_post_image_exists_on_pages(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B')
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': self.post.text,
            'group': self.group.id,
            'image': uploaded,
        }

        self.author_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_comment_form_for_auth_client(self):
        comments_count = Comment.objects.count()
        post_detail_url = reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        )
        form_data = {
            'text': 'test',
            'post': self.post,
            'author': self.author
        }

        response_for_auth = self.not_author_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response_for_auth, post_detail_url)
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_comment_form_for_guest_client(self):
        login_url = reverse('users:login')
        trgt_url = f'{login_url}?next=%2Fposts%2F{self.post.id}%2Fcomment%2F'
        form_data = {
            'text': 'test',
            'post': self.post,
            'author': self.author
        }

        response_for_guest = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response_for_guest, trgt_url)
