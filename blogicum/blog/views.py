from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.http import Http404
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .forms import CommentForm, EditProfileForm, PostForm, RegistrationForm
from .models import Post, Category, Comment

User = get_user_model()

POSTS_PER_PAGE = 10

def index(request):
    template_name = 'blog/index.html'
    post_list = Post.objects.select_related(
        'author', 'category', 'location'
    ).filter(
        Q(is_published=True)
        & Q(pub_date__lte=timezone.now())
        & Q(category__is_published=True)
    ).order_by('-pub_date')[:5]

    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {"page_obj": page_obj}
    return render(request, template_name, context)


def _post_accessible(post: Post, request):
    if (
        request.user.is_authenticated
        and (request.user == post.author or request.user.is_staff)
    ):
        return True

    is_accessible = Post.objects.filter(
        pk=post.pk,
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    ).exists()
    return is_accessible


def post_detail(request, id):
    template_name = "blog/detail.html"
    post = get_object_or_404(Post, pk=id)

    is_accessible = _post_accessible(post, request)

    if not is_accessible:
        raise Http404

    comments = (
        Comment.objects.filter(post=post)
        .select_related("author")
        .order_by("created_at")
    )
    form = CommentForm()
    context = {"post": post, "comments": comments, "form": form}
    return render(request, template_name, context)


def category_posts(request, category_slug):
    template_name = 'blog/category.html'
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post_list = Post.objects.select_related(
        'author', 'category', 'location'
    ).filter(
        category=category,
        is_published=True,
        pub_date__lte=timezone.now()
    ).order_by('-pub_date')

    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {"category": category, "page_obj": page_obj}
    return render(request, template_name, context)

def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    is_owner = request.user.is_authenticated and request.user == profile_user

    qs = (
        Post.objects.select_related("author", "category", "location")
        .filter(author=profile_user)
        .annotate(comment_count=Count("comments"))
        .order_by("-pub_date")
    )
    if not is_owner:
        qs = qs.filter(
            is_published=True,
            pub_date__lte=timezone.now(),
            category__is_published=True,
        )

    paginator = Paginator(qs, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "blog/profile.html",
        {"profile": profile_user, "page_obj": page_obj},
    )


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            updated_user = form.save()
            return redirect("blog:profile", updated_user.username)
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, "blog/user.html", {"form": form})


@login_required
def create_post(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("blog:profile", request.user.username)
    else:
        form = PostForm()
    return render(request, "blog/create.html", {"form": form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        resp = redirect(f"/posts/{post.id}/")
        return resp

    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect("blog:post_detail", post.id)
    else:
        form = PostForm(instance=post)
    return render(request, "blog/create.html", {"form": form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect("blog:post_detail", post.id)

    if request.method == "POST":
        post.delete()
        return redirect("blog:index")

    form = PostForm(instance=post)
    return render(request, "blog/create.html", {"form": form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not _post_accessible(post, request):
        raise Http404

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect("blog:post_detail", post.id)

    raise Http404


@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    if not _post_accessible(post, request):
        raise Http404

    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect("blog:post_detail", post.id)

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect("blog:post_detail", post.id)
    else:
        form = CommentForm(instance=comment)
    return render(
        request,
        "blog/comment.html",
        {"comment": comment, "form": form},
    )


@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    if not _post_accessible(post, request):
        raise Http404

    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.author != request.user:
        return redirect("blog:post_detail", post.id)

    if request.method == "POST":
        comment.delete()
        return redirect("blog:post_detail", post.id)

    return render(request, "blog/comment.html", {"comment": comment})


def registration(request):

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect("login")
    else:
        form = RegistrationForm()
    return render(request, "registration/registration_form.html", {"form": form})