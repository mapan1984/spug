# Copyright: (c) OpenSpug Organization. https://github.com/openspug/spug
# Copyright: (c) <spug.dev@gmail.com>
# Released under the AGPL-3.0 License.
from django.views.generic import View
from django.db.models import F
from django.http.response import HttpResponseBadRequest
from libs import json_response, JsonParser, Argument
from apps.setting.utils import AppSetting
from apps.host.models import Host, Tag, Category
from apps.app.models import Deploy
from apps.schedule.models import Task
from apps.monitor.models import Detection
from apps.account.models import Role
from libs.ssh import SSH, AuthenticationException
from paramiko.ssh_exception import BadAuthenticationType
from libs import human_datetime, AttrDict
from openpyxl import load_workbook
import socket


class HostView(View):
    def get(self, request):
        host_id = request.GET.get('id')
        if host_id:
            if not request.user.has_host_perm(host_id):
                return json_response(error='无权访问该主机，请联系管理员')
            return json_response(Host.objects.get(pk=host_id))
        if request.user.is_supper:
            hosts = Host.objects.filter(deleted_by_id__isnull=True)
            categories = Category.forest()
            zones = Category.zones()
        else:
            hosts = Category.hosts(request.user.category_perms)
            categories = Category.sub_forest(request.user.category_perms)
            zones = Category.sub_zones(categories)
        tags = [tag.name for tag in Tag.objects.all() if tag.host_set.filter(deleted_by_id__isnull=True).count() > 0]
        perms = [x.id for x in hosts] if request.user.is_supper else request.user.host_perms
        return json_response(
            {
                'zones': zones,
                'hosts': [x.to_dict() for x in hosts],
                'perms': perms,
                'categories': categories,
                'tags': tags,
            }
        )

    def post(self, request):
        form, error = JsonParser(
            Argument('id', type=int, required=False),
            Argument('category', help='请输入主机类型'),
            Argument('tags', type=list, required=False),
            Argument('name', help='请输主机名称'),
            Argument('username', handler=str.strip, help='请输入登录用户名'),
            Argument('hostname', handler=str.strip, help='请输入主机名或IP'),
            Argument('port', type=int, help='请输入SSH端口'),
            Argument('pkey', required=False),
            Argument('desc', required=False),
            Argument('password', required=False),
        ).parse(request.body)
        if error is not None:
            return json_response(error=error)

        if valid_ssh(form.hostname, form.port, form.username, password=form.pop('password'),
                     pkey=form.pkey) is False:
            return json_response('auth fail')

        tags = form.pop('tags', None)
        category = form.pop('category', None)

        if form.id:
            pk = form.pop('id')
            Host.objects.filter(pk=pk).update(**form)
            if tags is not None:
                host = Host.objects.get(pk=pk)
                host.update_tags(tags)
            if category is not None:
                host = Host.objects.get(pk=pk)
                generated = host.update_category(category)
                if generated:
                    request.user.role.add_category_perms(host.category.id)
        # elif Host.objects.filter(name=form.name, deleted_by_id__isnull=True).exists():
        #     return json_response(error=f'已存在的主机名称【{form.name}】')
        else:
            host = Host.objects.create(created_by=request.user, **form)
            if tags is not None:
                host.update_tags(tags)
            if category is not None:
                generated = host.update_category(category)
            if request.user.role:
                request.user.role.add_host_perm(host.id)
                if category is not None and generated:
                    request.user.role.add_category_perms(host.category.id)

        return json_response(error=error)

    def patch(self, request):
        form, error = JsonParser(
            Argument('id', type=int, required=False),
            Argument('category', help='请输入主机类别')
        ).parse(request.body)
        if error is None:
            host = Host.objects.filter(pk=form.id).first()
            if not host:
                return json_response(error='未找到指定主机')
            count = 0
            for host in Host.objects.filter(category=host.category, deleted_by_id__isnull=True).all():
                host.update_category(form.category)
                count += 1
            request.user.role.add_category_perms(host.category.id)
            return json_response(count)
        return json_response(error=error)

    def delete(self, request):
        form, error = JsonParser(
            Argument('id', type=int, help='请指定操作对象')
        ).parse(request.GET)
        if error is None:
            deploy = Deploy.objects.filter(host_ids__regex=fr'\D{form.id}\D').annotate(
                app_name=F('app__name'),
                env_name=F('env__name')
            ).first()
            if deploy:
                return json_response(error=f'应用【{deploy.app_name}】在【{deploy.env_name}】的发布配置关联了该主机，请解除关联后再尝试删除该主机')
            task = Task.objects.filter(targets__regex=fr'\D{form.id}\D').first()
            if task:
                return json_response(error=f'任务计划中的任务【{task.name}】关联了该主机，请解除关联后再尝试删除该主机')
            detection = Detection.objects.filter(type__in=('3', '4'), addr=form.id).first()
            if detection:
                return json_response(error=f'监控中心的任务【{detection.name}】关联了该主机，请解除关联后再尝试删除该主机')
            role = Role.objects.filter(host_perms__regex=fr'\D{form.id}\D').first()
            if role:
                return json_response(error=f'角色【{role.name}】的主机权限关联了该主机，请解除关联后再尝试删除该主机')
            Host.objects.filter(pk=form.id).update(
                deleted_at=human_datetime(),
                deleted_by=request.user,
            )
        return json_response(error=error)


def post_import(request):
    password = request.POST.get('password')
    file = request.FILES['file']
    ws = load_workbook(file, read_only=True)['Sheet1']
    summary = {'invalid': [], 'skip': [], 'fail': [], 'network': [], 'repeat': [], 'success': [], 'error': []}
    for i, row in enumerate(ws.rows):
        if i == 0:  # 第1行是表头 略过
            continue
        if not all([row[x].value for x in range(5)]):
            summary['invalid'].append(i)
            continue
        data = AttrDict(
            category=row[0].value,
            tags=row[1].value,
            name=row[2].value,
            hostname=row[3].value,
            port=row[4].value,
            username=row[5].value,
            password=row[6].value,
            desc=row[7].value
        )
        if Host.objects.filter(hostname=data.hostname, port=data.port, username=data.username,
                               deleted_by_id__isnull=True).exists():
            summary['skip'].append(i)
            continue
        try:
            if valid_ssh(data.hostname, data.port, data.username, data.pop('password') or password, None,
                         False) is False:
                summary['fail'].append(i)
                continue
        except AuthenticationException:
            summary['fail'].append(i)
            continue
        except socket.error:
            summary['network'].append(i)
            continue
        except Exception:
            summary['error'].append(i)
            continue
        if Host.objects.filter(name=data.name, deleted_by_id__isnull=True).exists():
            summary['repeat'].append(i)
            continue
        tags = data.pop('tags', None)
        category = data.pop('category', None)
        host = Host.objects.create(created_by=request.user, **data)
        if tags is not None:
            host.update_tags(tags.split(','))
        if category is not None:
            generated = host.update_category(category)
        if request.user.role:
            request.user.role.add_host_perm(host.id)
            if category is not None and generated:
                request.user.role.add_category_perms(host.category.id)
        summary['success'].append(i)
    return json_response(summary)


def get_categories(request):
    categories = Category.objects.all()
    return json_response({
        'categories': [c.to_dict() for c in categories]
    })


def valid_ssh(hostname, port, username, password=None, pkey=None, with_expect=True):
    try:
        private_key = AppSetting.get('private_key')
        public_key = AppSetting.get('public_key')
    except KeyError:
        private_key, public_key = SSH.generate_key()
        AppSetting.set('private_key', private_key, 'ssh private key')
        AppSetting.set('public_key', public_key, 'ssh public key')
    if password:
        _cli = SSH(hostname, port, username, password=str(password))
        _cli.add_public_key(public_key)
    if pkey:
        private_key = pkey
    try:
        cli = SSH(hostname, port, username, private_key)
        cli.ping()
    except BadAuthenticationType:
        if with_expect:
            raise TypeError('该主机不支持密钥认证，请参考官方文档，错误代码：E01')
        return False
    except AuthenticationException:
        if password and with_expect:
            raise ValueError('密钥认证失败，请参考官方文档，错误代码：E02')
        return False
    return True


def post_parse(request):
    file = request.FILES['file']
    if file:
        data = file.read()
        return json_response(data.decode())
    else:
        return HttpResponseBadRequest()
