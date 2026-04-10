from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Post, Category


def index(request):
    template_name = 'blog/index.html'
    post_list = Post.objects.select_related(
        'author', 'category', 'location'
    ).filter(
        Q(is_published=True)
        & Q(pub_date__lte=timezone.now())
        & Q(category__is_published=True)
    ).order_by('-pub_date')[:5]
    context = {'post_list': post_list}
    return render(request, template_name, context)


def post_detail(request, id):
    template_name = 'blog/detail.html'
    post = get_object_or_404(
        Post.objects.select_related('author', 'category', 'location'),
        id=id,
        is_published=True,
        category__is_published=True,
        pub_date__lte=timezone.now()
    )
    context = {'post': post}
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
    context = {
        'category': category,
        'post_list': post_list
    }
    return render(request, template_name, context)
