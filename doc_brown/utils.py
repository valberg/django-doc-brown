# coding: utf-8
from django.core import serializers


def revision_on_delete(collector, field, sub_objs, using):
    serialized = serializers.serialize('json',
                                       [getattr(sub_objs[0], field.name)])
    for obj in sub_objs:
        setattr(obj, field.name, None)
        setattr(obj, field.name + '_serialized', serialized)
        obj.save()
