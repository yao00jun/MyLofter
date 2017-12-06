# coding=utf8
from django.shortcuts import render
from django.views.generic import View
from .models import LofterModel
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
import json
from captcha.models import CaptchaStore
from captcha.helpers import captcha_image_url
from Users.models import Comments
from utils.ip2pos import get_ip_pos
from utils.new_ip import generate_new_ip


# Create your views here.

class IndexView(View):
    def get(self, request):
        search_keywords = request.GET.get('keywords', '')

        if search_keywords:
            all_items = LofterModel.objects.filter(
                Q(title__icontains=search_keywords) | Q(content__icontains=search_keywords))
        else:
            all_items = LofterModel.objects.all()

        paginator = Paginator(all_items, 3)  # Show 8 contacts per page
        page = request.GET.get('page', '1')
        try:
            contacts = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            contacts = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            contacts = paginator.page(paginator.num_pages)

        return render(request, 'index.html', {
            'contacts': contacts,
        })


class AddFavView(View):
    def post(self, request):
        item_id = request.POST.get('item_id', '')
        if item_id:
            exist_records = LofterModel.objects.get(id=int(item_id))

            has_clicked = request.session.get(item_id + '_clicked', False)
            if exist_records and has_clicked is False:
                exist_records.fav_click += 1
                request.session[item_id + '_clicked'] = True

            if exist_records and has_clicked is True:
                if exist_records.fav_click > 0:
                    exist_records.fav_click -= 1
                request.session[item_id + '_clicked'] = False

            key = ["status", "newfav"]
            val = ["success", exist_records.fav_click]
            exist_records.save()
            return HttpResponse(json.dumps(dict(zip(key, val))), content_type='application/json')


class PerBlogView(View):
    def get(self, request, blog_id):
        blog_id = int(blog_id)
        blog_item = LofterModel.objects.filter(id=blog_id)
        blog_list = LofterModel.objects.all().defer('title', 'timestamp', 'content', 'image',
                                            'fav_click', 'author_id').values_list('id', flat=True)
        blog_list = list(blog_list)

        try:
            cur_pos = blog_list.index(blog_item[0].id)
        except:
            return render(request,'active_fail.html',{'title':'404','msg':'访问页面不存在'})

        pre_pos = cur_pos - 1 if cur_pos != 0 else cur_pos
        next_pos = cur_pos + 1 if cur_pos != len(blog_list) - 1 else 0

        comments = Comments.objects.filter(essay=blog_id).order_by('-add_time')[:10]
        comments_count = Comments.objects.filter(essay=blog_id).count()
        if blog_item:
            return render(request, 'per_blog.html', {
                'blog_item': blog_item[0],
                'blog_pre': str(blog_list[pre_pos]),
                'blog_next': str(blog_list[next_pos]),
                'comments': comments,
                'comments_count': comments_count
            })
        else:
            return HttpResponseRedirect('/')


# 刷新验证码
class RefreshView(View):
    def get(self, request):
        to_json_response = dict()
        to_json_response['status'] = 1
        to_json_response['new_cptch_key'] = CaptchaStore.generate_key()
        to_json_response['new_cptch_image'] = captcha_image_url(to_json_response['new_cptch_key'])
        return HttpResponse(json.dumps(to_json_response), content_type='application/json')


class AddCommentsView(View):
    def post(self, request):
        essay_id = request.POST.get('essay_id', None)
        if essay_id:
            comments = request.POST.get('comments', "")
            if comments:
                essay_comments = Comments()

                # get()只能取得一条数据，多条会报错
                # filter()可以返回一个数组
                essay = LofterModel.objects.get(id=int(essay_id))
                essay_comments.essay = essay
                essay_comments.comments = comments
                if not request.user.is_authenticated():
                    if request.META.has_key('HTTP_X_FORWARDED_FOR'):
                        user_ip = request.META['HTTP_X_FORWARDED_FOR']
                    else:
                        user_ip = request.META['REMOTE_ADDR']
		    user_ip_star = generate_new_ip(user_ip)
		    essay_comments.anonymous_user = get_ip_pos(user_ip)+'['+user_ip_star+']'
                else:
                    essay_comments.comment_user = request.user
                essay_comments.save()
                return HttpResponse('{"status":"success","msg":"添加成功"}', content_type='application/json')
            else:
                return HttpResponse('{"status":"fail","msg":"添加失败"}', content_type='application/json')


class UserIndexView(View):
    def get(self, request, uid):
        uid = int(uid)

        search_keywords = request.GET.get('keywords', '')

        if search_keywords:
            all_items = LofterModel.objects.filter(Q(author_id=uid),
                                                   Q(title__icontains=search_keywords) | Q(
                                                       content__icontains=search_keywords))
        else:
            all_items = LofterModel.objects.filter(author_id=uid)

        paginator = Paginator(all_items, 3)  # Show 8 contacts per page
        page = request.GET.get('page', '1')
        try:
            contacts = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            contacts = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            contacts = paginator.page(paginator.num_pages)

        return render(request, 'user_index.html', {
            'contacts': contacts,
        })


class UserBlogView(View):
    def get(self, request, uid, bid):
        uid = int(uid)
        blog_id = int(bid)
        blog_item = LofterModel.objects.filter(id=blog_id)
        blog_list = LofterModel.objects.filter(author_id=uid).defer('title', 'timestamp', 'content',
                                                        'fav_click','image').values_list('id', flat=True)
        blog_list = list(blog_list)

        try:
            cur_pos = blog_list.index(blog_item[0].id)
        except:
            return render(request,'active_fail.html',{'title':'404','msg':'访问页面不存在'})

        pre_pos = cur_pos - 1 if cur_pos != 0 else cur_pos
        next_pos = cur_pos + 1 if cur_pos != len(blog_list)-1 else 0

        comments = Comments.objects.filter(essay=blog_id).order_by('-add_time')[:10]
        comments_count = Comments.objects.filter(essay=blog_id).count()
        if blog_item:
            return render(request, 'user_blog.html', {
                'uid':uid,
                'blog_item': blog_item[0],
                'blog_pre': str(blog_list[pre_pos]),
                'blog_next': str(blog_list[next_pos]),
                'comments': comments,
                'comments_count': comments_count
            })
        else:
            return HttpResponseRedirect('/')
