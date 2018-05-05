import re

import django_tables2 as tables
from django_tables2.utils import A, Accessor

from django.urls import reverse

from crudbuilder.abstract import BaseBuilder
from crudbuilder.helpers import (
    model_class_form,
    plural,
    custom_postfix_url,
    lowercase,
    fetch_id
)


class TransformLinkColumn(tables.LinkColumn):
    def __init__(self, functor,viewname=None, urlconf=None, args=None, kwargs=None,
                 current_app=None, attrs=None, **extra):
        super(TransformLinkColumn, self).__init__(viewname, urlconf, args,kwargs,current_app,attrs,**extra)
        #assert callable(functor)
        self.functor = functor

    def compose_url(self, record, *args, **kwargs):
        '''Compose the url if the column is constructed with a viewname.'''

        if self.viewname is None:
            if not hasattr(record, 'get_absolute_url'):
                raise TypeError('if viewname=None, record must define a get_absolute_url')
            return record.get_absolute_url()

        def resolve_if_accessor(val):
            return val.resolve(record) if isinstance(val, Accessor) else val

        viewname = resolve_if_accessor(self.viewname)
        print(viewname)
        print(self.urlconf)
        print('args')
        for a in self.args:
            print(a)
        if self.kwargs:
            print('kwargs')
            for k, a in self.kwargs.items():
                print(str(k) + ' -> ' + str(a))
        print(self.current_app)

        # Collect the optional arguments for django's reverse()
        params = {}
        if self.urlconf:
            params['urlconf'] = resolve_if_accessor(self.urlconf)
        if self.args:
            params['args'] = [self.functor(resolve_if_accessor(a)) for a in self.args]
        if self.kwargs:
            params['kwargs'] = {key: self.functor(resolve_if_accessor(val)) for key, val in self.kwargs.items()}
        if self.current_app:
            params['current_app'] = resolve_if_accessor(self.current_app)
        for a in params['args']:
            print(a)
        return reverse(viewname, **params)

    def render(self, value, record, bound_column):
        return self.render_link(
            self.compose_url(record, bound_column),
            record=record,
            value=value
)

class TableBuilder(BaseBuilder):
    """
    Table builder which returns django_tables2 instance
    app : app name
    model : model name for which table will be generated
    table_fields : display fields for tables2 class
    css_table : css class for generated tables2 class
    """
    def generate_table(self):
        model_class = self.get_model_class()

        detail_url_name = '{}-{}-detail'.format(
            self.app, custom_postfix_url(self.crud(), self.model)
        )
        main_attrs = dict(
            pk=tables.LinkColumn(detail_url_name, args=[A('pk')])
        )

        meta_attrs = dict(
            model=model_class,
            fields=('pk',) + self.tables2_fields if self.tables2_fields else ('pk',),
            attrs={
                "class": self.tables2_css_class,
                "empty_text": "No {} exist".format(plural(self.model))
            })
        url_fks = {}
        fields = set(list(meta_attrs['fields'])) - {'pk'}
        for field in fields:
            fd = model_class._meta.get_field(field)
            if 'related_model' in fd.__dict__:
                print(field)
                klass = fd.__dict__['related_model']
                pattern = re.compile(r'\.(\w+)\'>')
                klass_name = re.findall(pattern,str(klass))[0]
                url = '{}-{}-detail'.format(self.app,plural(klass_name))
                print(url)
                url_fks[field] = '{}-{}-detail'.format(self.app, lowercase(plural(klass_name)))

        for field, url in url_fks.items():
            main_attrs[field] = TransformLinkColumn(fetch_id,viewname=url, args=[A(field)])
        

        main_attrs['Meta'] = type('Meta', (), meta_attrs)
        klass = type(
            model_class_form(self.model + 'Table'),
            (tables.Table,),
            main_attrs
        )
        return klass
