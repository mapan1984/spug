# Copyright: (c) OpenSpug Organization. https://github.com/openspug/spug
# Copyright: (c) <spug.dev@gmail.com>
# Released under the AGPL-3.0 License.
import queue

from django.db import models
from libs import ModelMixin, human_datetime
from apps.account.models import User
from apps.setting.utils import AppSetting
from libs.ssh import SSH


class Category(models.Model, ModelMixin):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return '/'.join(full_path[::-1])

    def tree(self, filter_empty=True, visited={}):
        """
        将自身结构表达为可被 https://ant.design/components/cascader-cn/ 组件
        的 options 接受的格式

        Args:
            filter_empty: 是否过滤没有所属 host 的 Category，默认过滤
            visited: 缓存每个子节点的结构，以 id 为 key
        """
        if self.id in visited:
            return visited[self.id]

        res = {
            'value': self.name,
            'label': self.name,
        }

        childrens = self.children.all()

        if len(childrens) == 0:
            if (
                filter_empty
                and self.host_set.filter(deleted_by_id__isnull=True).count() == 0
            ):
                visited[self.id] = None
            else:
                visited[self.id] = res
            return visited[self.id]

        res['children'] = []
        for c in childrens:
            sub_tree = c.tree(filter_empty, visited)
            if (
                not filter_empty
                or sub_tree is not None
            ):
                res['children'].append(sub_tree)

        if len(res['children']) > 0:
            visited[self.id] = res
        else:
            if self.host_set.filter(deleted_by_id__isnull=True).count() > 0:
                del res['children']
                visited[self.id] = res
            else:
                visited[self.id] = None
        return visited[self.id]

    @classmethod
    def forest(cls):
        res = []
        for category in cls.objects.filter(parent=None).all():
            tree = category.tree()
            if tree is not None:
                res.append(tree)
        return res

    @classmethod
    def generate(cls, location):
        """
        生成 Category 实例，location 表示嵌套类的路径，以 `/` 分隔
        例如：
            location = region/zone，则生成 2 个 Category 实例，name 分别为
            `region` 和 `zone`，将 `zone` Category 的 parent 设置为 `region`
        Return:
            current: 最低层次的类别
            generated: 是否有新生成的类别
        """
        parent = None
        current = None
        generated = False
        for name in location.split('/'):
            current, created = cls.objects.get_or_create(name=name, parent=parent)
            parent = current
            generated = generated or created
        return current, generated

    @classmethod
    def zones(cls):
        res = []
        for category in cls.objects.all():
            if category.host_set.filter(deleted_by_id__isnull=True).count() > 0:
                res.append(str(category))
        return res

    @classmethod
    def sub_zones(cls, categories):
        res = []
        for category in categories:
            name = category['value']
            if 'children' in category:
                names = cls.sub_zones(category['children'])
                for n in names:
                    res.append(f'{name}/{n}')
            else:
                res.append(name)
        return res

    def to_dict(self, *args, **kwargs):
        res = super().to_dict(*args, **kwargs)
        res['full_path'] = str(self)
        return res

    @classmethod
    def hosts(cls, category_pks):
        hosts = []
        pks = queue.Queue()
        visited = set()
        for pk in category_pks:
            pks.put(pk)
        while not pks.empty():
            pk = pks.get()
            if pk in visited:
                continue
            category = cls.objects.get(pk=pk)
            for host in category.host_set.filter(deleted_by_id__isnull=True).all():
                hosts.append(host)
            for c in category.children.all():
                pks.put(c.id)
            visited.add(pk)
        return hosts

    @classmethod
    def sub_forest(cls, category_pks):
        visited = {}
        for pk in category_pks:
            if pk in visited:
                continue
            category = cls.objects.get(pk=pk)
            category.tree(visited=visited)

        root = set()
        parent_visited = {}
        for pk, tree in visited.items():
            category = cls.objects.get(pk=pk)
            while category.parent:
                parent = category.parent
                if parent.id in visited:
                    category = parent
                    continue

                if category.id in visited:
                    tree = visited[category.id]
                elif category.id in parent_visited:
                    tree = parent_visited[category.id]
                else:
                    raise KeyError(f'{category.id} not visited')

                if parent.id in parent_visited:
                    parent_visited[parent.id]['children'].append(tree)
                else:
                    parent_visited[parent.id] = {
                        'value': parent.name,
                        'label': parent.name,
                        'children': [tree],
                    }

                category = parent
            else:
                root.add(category.id)

        trees = []
        for pk in root:
            if pk in visited:
                tree = visited[pk]
            elif pk in parent_visited:
                tree = parent_visited[pk]
            else:
                raise KeyError(f'{pk} not visited')
            trees.append(tree)

        return trees


class Tag(models.Model, ModelMixin):
    name = models.CharField(max_length=30)

    def __str__(self):
        return f'<Tag: {self.name}>'

    class Meta:
        db_table = 'tags'
        ordering = ['name']


class Host(models.Model, ModelMixin):
    name = models.CharField(max_length=50)
    tags = models.ManyToManyField(Tag)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True)
    hostname = models.CharField(max_length=50)
    port = models.IntegerField()
    username = models.CharField(max_length=50)
    pkey = models.TextField(null=True)
    desc = models.CharField(max_length=255, null=True)

    created_at = models.CharField(max_length=20, default=human_datetime)
    created_by = models.ForeignKey(User, models.PROTECT, related_name='+')
    deleted_at = models.CharField(max_length=20, null=True)
    deleted_by = models.ForeignKey(User, models.PROTECT, related_name='+', null=True)

    @property
    def private_key(self):
        return self.pkey or AppSetting.get('private_key')

    def get_ssh(self, pkey=None):
        pkey = pkey or self.private_key
        return SSH(self.hostname, self.port, self.username, pkey)

    def to_dict(self, *args, **kwargs):
        res = super().to_dict(*args, **kwargs)
        res['tags'] = []
        for tag in self.tags.all():
            res['tags'].append(tag.name)
        if self.category:
            res['category'] = str(self.category)
            res['zone'] = self.zone
        return res

    @property
    def zone(self):
        return str(self.category)

    def update_tags(self, tags):
        for tag in self.tags.all():
            if tag.name not in tags:
                self.tags.remove(tag)
        for tag in tags:
            t, created = Tag.objects.get_or_create(name=tag)
            self.tags.add(t)
        self.save()

    def update_category(self, category):
        category, generated = Category.generate(category)
        self.category = category
        self.save()
        return generated

    def __repr__(self):
        return '<Host %r>' % self.name

    class Meta:
        db_table = 'hosts'
        ordering = ('-id',)
