from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.cache import cache_page

from .models import Post, Group, User, Comment, Follow
from .forms import PostForm, CommentForm


POSTS_QUANTITY = 10
CACHE_TIME_IN_SECONDS = 20


@cache_page(CACHE_TIME_IN_SECONDS, key_prefix='index_page')
def index(request):
    """Главная страница."""
    template = 'posts/index.html'
    posts = Post.objects.all().order_by('-pub_date')
    context = {
        'title': 'Последние обновления на сайте',
        'posts': posts,
        'page_obj': get_page(posts, request),
    }
    return render(request, template, context)


def group_posts(request, slug):
    """view-функция принимает параметр slug из path()."""
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author').order_by('-pub_date')
    context = {
        'group': group,
        'posts': posts,
        'page_obj': get_page(posts, request),
    }
    return render(request, template, context)


def profile(request, username):
    """Здесь код запроса к модели и создание словаря контекста."""
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    posts_count = author.posts.count()
    following = (
        request.user.is_authenticated
        and author.following.filter(user=request.user).exists()
    )
    context = {
        'author': author,
        'posts': posts,
        'posts_count': posts_count,
        'page_obj': get_page(posts, request),
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    """Здесь код запроса к модели и создание словаря контекста."""
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, id=post_id)
    posts_count = post.author.posts.count()
    form = CommentForm()
    context = {
        'post': post,
        'posts_count': posts_count,
        'form': form,
        'comments': Comment.objects.select_related('post')
    }
    return render(request, template, context)


@login_required
def post_create(request):
    """Форма создания поста."""
    template = 'posts/create_post.html'
    if request.method == 'POST':
        form = PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', request.user)
        return render(request, template, {'form': form})
    form = PostForm()
    return render(request, template, {'form': form})


@login_required
def post_edit(request, post_id):
    """Форма редактирования поста."""
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post.pk)
    if request.method == 'POST':
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post
        )
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:post_detail', post.pk)
    else:
        form = PostForm(instance=post)
    return render(request, template, {
        'form': form,
        'post_id': post_id,
        'is_edit': True,
    })


def get_page(posts, request):
    paginator = Paginator(posts, POSTS_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    posts = Post.objects.filter(author__following__user=request.user)
    context = {
        'title': 'Лента подписок',
        'page_obj': get_page(posts, request),
        'posts': posts
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
        return redirect('posts:follow_index')
    return redirect('posts:profile', request.user)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get(user=request.user, author=author).delete()
        return redirect('posts:follow_index')
    return redirect('posts:profile', request.user)
