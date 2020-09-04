# Copyright: (c) OpenSpug Organization. https://github.com/openspug/spug
# Copyright: (c) <spug.dev@gmail.com>
# Released under the AGPL-3.0 License.
from django.db import models
from libs import ModelMixin, human_datetime
from apps.account.models import User
from apps.setting.utils import AppSetting
from libs.ssh import SSH


class Category(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='children')

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return '/'.join(full_path[::-1])

    def tree(self, filter_empty=True):
        """
        将自身结构表达为可被 https://ant.design/components/cascader-cn/ 组件
        的 options 接受的格式

        Args:
            filter_empty: 是否过滤没有所属 host 的 Category，默认过滤
        """
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
                return None
            else:
                return res

        res['children'] = []
        for c in childrens:
            sub_tree = c.tree(filter_empty)
            if (
                not filter_empty
                or sub_tree is not None
            ):
                res['children'].append(sub_tree)

        if len(res['children']) > 0:
            return res
        else:
            return None

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
        """
        parent = None
        current = None
        for name in location.split('/'):
            current, _ = cls.objects.get_or_create(name=name, parent=parent)
            parent = current
        return current

    @classmethod
    def zones(cls):
        res = []
        for category in cls.objects.all():
            if category.host_set.filter(deleted_by_id__isnull=True).count() > 0:
                res.append(str(category))
        return res


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
        category = Category.generate(category)
        self.category = category
        self.save()

    def __repr__(self):
        return '<Host %r>' % self.name

    class Meta:
        db_table = 'hosts'
        ordering = ('-id',)
